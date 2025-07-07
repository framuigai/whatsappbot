import os
import json
import logging
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai # New: Import genai for configuration

# Import functions from our new utility modules
from whatsapp_api_utils import send_whatsapp_message
import db_utils
from ai_utils import generate_ai_reply, generate_embedding # Updated: Import generate_embedding too

# Load environment variables from .env file
load_dotenv()

# Configure logging for the main app
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Environment variables
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
# NEW: Configure Gemini API globally when the app starts
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

# Rate Limiting Configuration
RATE_LIMIT_SECONDS = 5 # Users can only send a new message after this many seconds

# Initialize the database when the app starts
with app.app_context():
    db_utils.init_db()
    # Temporary: Add an FAQ to test embedding generation
    # Uncomment the line below, run the app once, then comment it out again
    # db_utils.add_faq("What is the company's return policy?", "Our return policy allows returns within 30 days of purchase with a valid receipt.")
    # db_utils.add_faq("How do I contact customer support?", "You can reach customer support by calling 1-800-555-0199 or emailing support@example.com.")


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
            logging.info("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            logging.warning("Webhook verification failed: Token mismatch or wrong mode.")
            return "Verification failed", 403
    return "OK", 200 # Default return for GET requests not for verification

@app.route("/webhook", methods=["POST"])
def webhook_post():
    """
    Handles incoming messages from WhatsApp.
    """
    data = request.json
    logging.info(f"Received webhook data: {json.dumps(data, indent=2)}")

    # Basic payload validation (can be enhanced as per critique point 5)
    if not data or 'entry' not in data or not data['entry']:
        logging.warning("Invalid webhook payload: Missing 'entry'.")
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
                        logging.info(f"Received text message from {from_number}: {user_message}")

                        # Day 6: Handle empty or whitespace-only messages
                        if not user_message.strip():
                            logging.info(f"Received empty or whitespace message from {from_number}. Ignoring.")
                            db_utils.add_message(wa_id, user_message, 'user', 'Ignored (empty/whitespace)')
                            return jsonify({"status": "success"}), 200

                        # Day 6: Basic Rate Limiting
                        last_message_time = db_utils.get_last_message_time(wa_id)
                        current_time = int(time.time())
                        time_since_last_message = current_time - last_message_time

                        if time_since_last_message < RATE_LIMIT_SECONDS:
                            wait_time_remaining = RATE_LIMIT_SECONDS - time_since_last_message
                            # Critque Point 3: Clearer Rate Limiting Feedback
                            response_message = f"Please wait {int(wait_time_remaining)}s before sending another message."
                            logging.warning(f"Rate limit hit for {from_number}. Remaining: {wait_time_remaining}s")
                            send_whatsapp_message(from_number, response_message)
                            # Log the user message and the bot's rate-limit response
                            db_utils.add_message(wa_id, user_message, 'user', response_message)
                            return jsonify({"status": "rate_limited"}), 200

                        # Update last message time for the user
                        db_utils.update_last_message_time(wa_id)

                        # Get AI response (now using ai_utils.generate_ai_reply)
                        ai_response_text = generate_ai_reply(user_message, wa_id) # Call the function from ai_utils

                        # Send AI response via WhatsApp
                        if ai_response_text:
                            success = send_whatsapp_message(from_number, ai_response_text)
                            if success:
                                # Log both user message and bot response to DB
                                db_utils.add_message(wa_id, user_message, 'user', ai_response_text)
                            else:
                                logging.error(f"Failed to send response to {from_number}.")
                                db_utils.add_message(wa_id, user_message, 'user', 'Failed to send response')
                        else:
                            logging.warning(f"AI response was empty for message from {from_number}.")
                            db_utils.add_message(wa_id, user_message, 'user', 'No AI response generated')

                    elif message_type == 'button':
                        # Handle button clicks
                        button_payload = message['button']['payload']
                        logging.info(f"Received button click from {from_number} with payload: {button_payload}")
                        response_message = f"You clicked: {button_payload}"
                        send_whatsapp_message(from_number, response_message)
                        db_utils.add_message(wa_id, f"Button Click: {button_payload}", 'user', response_message)

                    else:
                        logging.info(f"Received message of type '{message_type}' from {from_number}. Not handling this type yet.")
                        # Optionally send a message indicating unsupported type
                        # send_whatsapp_message(from_number, "I can only process text messages for now. Please type your query.")
                        db_utils.add_message(wa_id, f"Unhandled type: {message_type}", 'user', 'Unsupported message type')

    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(debug=True, port=5000)