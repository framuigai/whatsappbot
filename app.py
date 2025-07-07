import os
import json
import logging
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

# Import functions from our new utility modules
from whatsapp_api_utils import send_whatsapp_message
import db_utils
from ai_utils import generate_ai_reply, generate_embedding # Only generate_embedding is needed here if adding FAQs

# Load environment variables from .env file
load_dotenv()

# Configure logging for the main app
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Get a logger for the main app

app = Flask(__name__)

# Environment variables
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
# Configure Gemini API globally when the app starts
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Rate Limiting Configuration
RATE_LIMIT_SECONDS = 5 # Users can only send a new message after this many seconds

# Initialize the database when the app starts and add initial FAQs
with app.app_context():
    db_utils.init_db()
    # Temporary: Add FAQs for testing. Uncomment, run once, then re-comment.
    # This block now correctly generates embeddings before adding FAQs.

    """
    # Helper function for adding FAQs with validation (Day 5 requirement)
    def add_faq_with_validation(question, answer):
        if not question or not question.strip():
            logger.error(f"Validation failed: FAQ question cannot be empty. Q: '{question}'")
            return False, "FAQ question cannot be empty."
        if not answer or not answer.strip():
            logger.error(f"Validation failed: FAQ answer cannot be empty. Q: '{question}', A: '{answer}'")
            return False, "FAQ answer cannot be empty."

        embedding = generate_embedding(question)
        if embedding:
            db_utils.add_faq(question, answer, embedding)
            logger.info(f"Successfully added FAQ: Q='{question[:50]}...'")
            return True, "FAQ added successfully."
        else:
            logger.error(f"Failed to generate embedding for FAQ: Q='{question[:50]}...'")
            return False, "Failed to generate embedding."

    # FAQ 1
    add_faq_with_validation("What is the company's return policy?", "Our return policy allows returns within 30 days of purchase with a valid receipt.")
    add_faq_with_validation("How do I contact customer support?", "You can reach customer support by calling 1-800-555-0199 or emailing support@example.com.")
    add_faq_with_validation("Where are you located?", "Our main office is located in Nairobi, Kenya.")
    add_faq_with_validation("Do you offer international shipping?", "Yes, we ship to most countries worldwide. Shipping fees apply.")
    add_faq_with_validation("What is your refund procedure?", "To get a refund, please bring the item and receipt to any store location or mail it back to us.")

    # Example of a failed validation attempt (uncomment to test)
    # add_faq_with_validation("", "This answer should not be added.")
    # add_faq_with_validation("Question with no answer?", "")
    """


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """
    Verifies the webhook subscription with Facebook.
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            logger.info("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            logger.warning("Webhook verification failed: Token mismatch or wrong mode.")
            return "Verification failed", 403
    return "OK", 200 # Default return for GET requests not for verification

@app.route("/webhook", methods=["POST"])
def webhook_post():
    """
    Handles incoming messages from WhatsApp.
    """
    data = request.json
    logger.info(f"Received webhook data: {json.dumps(data, indent=2)}")

    # Basic payload validation
    if not data or 'entry' not in data or not data['entry']:
        logger.warning("Invalid webhook payload: Missing 'entry'.")
        return jsonify({"status": "error", "message": "Invalid payload"}), 400

    for entry in data['entry']:
        for change in entry.get('changes', []):
            if change.get('field') == 'messages':
                for message in change.get('value', {}).get('messages', []):
                    # Extract message details
                    from_number = message.get('from')
                    message_type = message.get('type')
                    wa_id = message.get('from') # WhatsApp ID (phone number) of the sender

                    if message_type == 'text':
                        user_message = message['text']['body']
                        logger.info(f"Received text message from {from_number}: {user_message}")

                        # Handle empty or whitespace-only messages
                        if not user_message.strip():
                            logger.info(f"Received empty or whitespace message from {from_number}. Ignoring.")
                            db_utils.add_message(wa_id, user_message, 'user', 'Ignored (empty/whitespace)')
                            return jsonify({"status": "success"}), 200

                        # Basic Rate Limiting
                        last_message_time = db_utils.get_last_message_time(wa_id)
                        current_time = int(time.time())
                        time_since_last_message = current_time - last_message_time

                        if time_since_last_message < RATE_LIMIT_SECONDS:
                            wait_time_remaining = RATE_LIMIT_SECONDS - time_since_last_message
                            response_message = f"Please wait {int(wait_time_remaining)}s before sending another message."
                            logger.warning(f"Rate limit hit for {from_number}. Remaining: {wait_time_remaining}s")
                            send_whatsapp_message(from_number, response_message)
                            db_utils.add_message(wa_id, user_message, 'user', response_message)
                            return jsonify({"status": "rate_limited"}), 200

                        # Update last message time for the user
                        db_utils.update_last_message_time(wa_id)

                        # Get AI response (RAG logic is now fully encapsulated within generate_ai_reply)
                        ai_response_text = generate_ai_reply(user_message, wa_id)

                        # Send AI response via WhatsApp
                        if ai_response_text:
                            success = send_whatsapp_message(from_number, ai_response_text)
                            if success:
                                db_utils.add_message(wa_id, user_message, 'user', ai_response_text)
                            else:
                                logger.error(f"Failed to send response to {from_number}.")
                                db_utils.add_message(wa_id, user_message, 'user', 'Failed to send response')
                        else:
                            logger.warning(f"AI response was empty for message from {from_number}.")
                            db_utils.add_message(wa_id, user_message, 'user', 'No AI response generated')

                    elif message_type == 'button':
                        button_payload = message['button']['payload']
                        logger.info(f"Received button click from {from_number} with payload: {button_payload}")
                        response_message = f"You clicked: {button_payload}"
                        send_whatsapp_message(from_number, response_message)
                        db_utils.add_message(wa_id, f"Button Click: {button_payload}", 'user', response_message)

                    else:
                        logger.info(f"Received message of type '{message_type}' from {from_number}. Not handling this type yet.")
                        db_utils.add_message(wa_id, f"Unhandled type: {message_type}", 'user', 'Unsupported message type')

    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(debug=True, port=5000)