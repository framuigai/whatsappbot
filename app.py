import os
import json
import logging
import time
import sys
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

# Import functions from our utility modules
from whatsapp_api_utils import send_whatsapp_message
import db_utils
from ai_utils import generate_ai_reply, generate_embedding # generate_embedding is needed for FAQ setup

# Load environment variables from .env file
load_dotenv()

# --- Logging Configuration ---
# Configure logging for the main app and other modules
# Set this to INFO, DEBUG, WARNING, ERROR, CRITICAL as needed for verbosity
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO").upper()
log_level_map = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

logging.basicConfig(
    level=log_level_map.get(LOGGING_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("whatsapp_bot.log"), # Logs to a file
        logging.StreamHandler(sys.stdout)       # Logs to the console
    ]
)
logger = logging.getLogger(__name__) # Get a logger for the main app

app = Flask(__name__)

# --- Environment Variables ---
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
if not VERIFY_TOKEN:
    logger.error("VERIFY_TOKEN not set in environment variables. Webhook verification will fail.")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
if not WHATSAPP_PHONE_NUMBER_ID:
    logger.error("WHATSAPP_PHONE_NUMBER_ID not set in environment variables.")

# Configure Gemini API globally when the app starts
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.critical("GEMINI_API_KEY not set. AI functionalities will not work.")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("Gemini API configured successfully.")
    except Exception as e:
        logger.critical(f"Failed to configure Gemini API: {e}")

# Rate Limiting Configuration
try:
    RATE_LIMIT_SECONDS = int(os.getenv("RATE_LIMIT_SECONDS", 5))
except ValueError:
    logger.warning("Invalid RATE_LIMIT_SECONDS in .env. Defaulting to 5 seconds.")
    RATE_LIMIT_SECONDS = 5

# --- Database Initialization & FAQ Setup ---
# Initialize the database when the app starts
with app.app_context():
    db_utils.init_db()
    logger.info("Database initialization complete.")

    # Helper function for adding FAQs with validation and embedding generation
    def add_faq_with_validation_and_embedding(question, answer):
        """
        Adds an FAQ to the database, generating its embedding.
        Returns True on success, False on failure.
        """
        if not question or not question.strip():
            logger.error(f"Validation failed: FAQ question cannot be empty. Q: '{question}'")
            return False
        if not answer or not answer.strip():
            logger.error(f"Validation failed: FAQ answer cannot be empty. Q: '{question}', A: '{answer}'")
            return False

        embedding = generate_embedding(question)
        if embedding:
            faq_id = db_utils.add_faq(question, answer, embedding)
            if faq_id:
                logger.info(f"Successfully added FAQ (ID: {faq_id}): Q='{question[:50]}...'")
                return True
            else:
                logger.error(f"Failed to add FAQ to DB after embedding: Q='{question[:50]}...'")
                return False
        else:
            logger.error(f"Failed to generate embedding for FAQ: Q='{question[:50]}...'")
            return False

    # --- Initial FAQ Loading (Run once for setup, then keep commented) ---
    # Uncomment the block below, run your app once, then re-comment it.
    # This ensures FAQs are added only when intended and not on every app restart.
    """   
    logger.info("Attempting to add initial FAQs (if not already present)...")
    if not db_utils.get_all_faqs(): # Only add if no FAQs exist
        if add_faq_with_validation_and_embedding("What is the company's return policy?", "Our return policy allows returns within 30 days of purchase with a valid receipt."):
            pass # Success handled by function
        else:
            logger.error("Failed to add initial FAQ 1.")

        if add_faq_with_validation_and_embedding("How do I contact customer support?", "You can reach customer support by calling 1-800-555-0199 or emailing support@example.com."):
            pass
        else:
            logger.error("Failed to add initial FAQ 2.")

        if add_faq_with_validation_and_embedding("Where are you located?", "Our main office is located in Nairobi, Kenya."):
            pass
        else:
            logger.error("Failed to add initial FAQ 3.")

        if add_faq_with_validation_and_embedding("Do you offer international shipping?", "Yes, we ship to most countries worldwide. Shipping fees apply."):
            pass
        else:
            logger.error("Failed to add initial FAQ 4.")

        if add_faq_with_validation_and_embedding("What is your refund procedure?", "To get a refund, please bring the item and receipt to any store location or mail it back to us."):
            pass
        else:
            logger.error("Failed to add initial FAQ 5.")

        # Example of a failed validation attempt (uncomment to test)
        # add_faq_with_validation_and_embedding("", "This answer should not be added.")
        # add_faq_with_validation_and_embedding("Question with no answer?", "")
    else:
        logger.info("FAQs already exist in the database. Skipping initial FAQ loading.")
        """
    # --- End of Initial FAQ Loading Block ---


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """
    Verifies the webhook subscription with Facebook.
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if not all([mode, token, challenge]):
        logger.warning("Missing mode, token, or challenge in webhook verification request.")
        return "Missing parameters", 400

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("WEBHOOK_VERIFIED")
        return challenge, 200
    else:
        logger.warning(f"Webhook verification failed. Mode: {mode}, Token received: {token}, Expected Token: {VERIFY_TOKEN}")
        return "Verification failed", 403

@app.route("/webhook", methods=["POST"])
def webhook_post():
    """
    Handles incoming messages from WhatsApp.
    """
    data = request.json
    logger.debug(f"Received webhook data: {json.dumps(data, indent=2)}") # Use debug for verbose payload logging

    # Basic payload validation
    if not data or 'entry' not in data:
        logger.warning("Invalid webhook payload: Missing 'entry'.")
        return jsonify({"status": "error", "message": "Invalid payload"}), 400

    for entry in data.get('entry', []):
        for change in entry.get('changes', []):
            if change.get('field') == 'messages':
                for message in change.get('value', {}).get('messages', []):
                    from_number = message.get('from') # WhatsApp ID (phone number) of the sender
                    message_type = message.get('type')
                    wa_id = from_number # Alias for clarity

                    if not wa_id:
                        logger.error("Could not extract sender WhatsApp ID from message. Skipping.")
                        continue

                    logger.info(f"Processing message of type '{message_type}' from {from_number}")

                    if message_type == 'text':
                        user_message = message['text']['body']
                        logger.info(f"Received text message from {from_number}: '{user_message}'")

                        # Handle empty or whitespace-only messages early
                        if not user_message.strip():
                            logger.info(f"Received empty or whitespace message from {from_number}. Ignoring.")
                            db_utils.add_message(wa_id, user_message, 'user', 'Ignored (empty/whitespace)')
                            return jsonify({"status": "success"}), 200

                        # Rate Limiting Check
                        last_message_time = db_utils.get_last_message_time(wa_id)
                        current_time = int(time.time())
                        time_since_last_message = current_time - last_message_time

                        if time_since_last_message < RATE_LIMIT_SECONDS:
                            wait_time_remaining = RATE_LIMIT_SECONDS - time_since_last_message
                            response_message = f"Please wait {int(wait_time_remaining)}s before sending another message."
                            logger.warning(f"Rate limit hit for {from_number}. Remaining: {wait_time_remaining}s")
                            send_whatsapp_message(from_number, response_message)
                            db_utils.add_message(wa_id, user_message, 'user', response_message) # Log user message and bot's rate-limit response
                            return jsonify({"status": "rate_limited"}), 200

                        # Update last message time *before* AI processing to prevent race conditions
                        db_utils.update_last_message_time(wa_id)

                        # Get AI response
                        ai_response_text = generate_ai_reply(user_message, wa_id)

                        # Send AI response via WhatsApp
                        if ai_response_text:
                            success = send_whatsapp_message(from_number, ai_response_text)
                            if success:
                                db_utils.add_message(wa_id, user_message, 'user', ai_response_text)
                                logger.info(f"Successfully sent AI response to {from_number}.")
                            else:
                                logger.error(f"Failed to send response to {from_number} via WhatsApp API.")
                                db_utils.add_message(wa_id, user_message, 'user', 'Failed to send response via API')
                        else:
                            fallback_message = "I'm sorry, I couldn't generate a response for that. Please try rephrasing your question or contact support at support@example.com."
                            logger.warning(f"AI response was empty for message from {from_number}. Sending fallback.")
                            send_whatsapp_message(from_number, fallback_message)
                            db_utils.add_message(wa_id, user_message, 'user', fallback_message)

                    elif message_type == 'button':
                        button_payload = message.get('button', {}).get('payload')
                        if button_payload:
                            logger.info(f"Received button click from {from_number} with payload: {button_payload}")
                            response_message = f"You clicked: {button_payload}"
                            send_whatsapp_message(from_number, response_message)
                            db_utils.add_message(wa_id, f"Button Click: {button_payload}", 'user', response_message)
                        else:
                            logger.warning(f"Received button message from {from_number} but no payload found.")
                            db_utils.add_message(wa_id, "Button click (no payload)", 'user', 'No action for button')

                    else:
                        logger.info(f"Received unhandled message type '{message_type}' from {from_number}.")
                        # Optionally send a message back saying "I can only handle text messages"
                        # send_whatsapp_message(from_number, "I can currently only process text messages. How can I help you?")
                        db_utils.add_message(wa_id, f"Unhandled type: {message_type}", 'user', 'Unsupported message type')

    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    # Ensure all modules use the same logging configuration
    logging.getLogger('whatsapp_api_utils').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('db_utils').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('ai_utils').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))

    # For production, set debug=False and configure a proper WSGI server (e.g., Gunicorn)
    app.run(debug=os.getenv("FLASK_DEBUG", "False").lower() == "true", host='0.0.0.0', port=5000)