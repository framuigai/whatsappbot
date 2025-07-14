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
from ai_utils import generate_ai_reply, generate_embedding  # generate_embedding is needed for FAQ setup

# Load environment variables from .env file
load_dotenv()

# --- Logging Configuration ---
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
        logging.FileHandler("whatsapp_bot.log"),  # Logs to a file
        logging.StreamHandler(sys.stdout)  # Logs to the console
    ]
)
logger = logging.getLogger(__name__)  # Get a logger for the main app

app = Flask(__name__)

# --- Environment Variables ---
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
if not VERIFY_TOKEN:
    logger.error("VERIFY_TOKEN not set in environment variables. Webhook verification will fail.")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
if not WHATSAPP_PHONE_NUMBER_ID:
    logger.warning(
        "WHATSAPP_PHONE_NUMBER_ID not set in environment variables. This might be needed for sending messages via API if not dynamically determined by webhook metadata.")

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
            logger.error(f"Validation failed: FAQ question: '{question}', answer cannot be empty. A: '{answer}'")
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
    """
    logger.info("Attempting to add initial FAQs (if not already present)...")
    if not db_utils.get_all_faqs(): # Only add if no FAQs exist
        if add_faq_with_validation_and_embedding("What is the company's return policy?", "Our return policy allows returns within 30 days of purchase with a valid receipt."):
            pass
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
        logger.warning(
            f"Webhook verification failed. Mode: {mode}, Token received: {token}, Expected Token: {VERIFY_TOKEN}")
        return "Verification failed", 403


@app.route("/webhook", methods=["POST"])
def webhook_post():
    """
    Handles incoming messages from WhatsApp.
    """
    data = request.json
    logger.debug(f"Received webhook data: {json.dumps(data, indent=2)}")

    if not data or 'entry' not in data:
        logger.warning("Invalid webhook payload: Missing 'entry'.")
        return jsonify({"status": "error", "message": "Invalid payload"}), 400

    for entry in data.get('entry', []):
        for change in entry.get('changes', []):
            if change.get('field') == 'messages':
                for message in change.get('value', {}).get('messages', []):
                    from_number = message.get('from')  # The end-user's WhatsApp number
                    message_type = message.get('type')
                    wa_id = from_number  # Alias for clarity

                    if not wa_id:
                        logger.error("Could not extract sender WhatsApp ID from message. Skipping.")
                        continue

                    # --- Dynamically determine tenant_id from webhook payload ---
                    whatsapp_phone_number_id = change.get('value', {}).get('metadata', {}).get('phone_number_id')

                    if not whatsapp_phone_number_id:
                        logger.error(
                            f"Missing 'phone_number_id' in webhook metadata for message from {from_number}. Cannot determine tenant. Skipping.")
                        send_whatsapp_message(from_number,
                                              "I'm sorry, I couldn't identify which service instance to route your message to. Please contact support.")
                        continue

                    current_tenant_id = db_utils.get_tenant_id_from_whatsapp_phone_number(whatsapp_phone_number_id)

                    if not current_tenant_id:
                        logger.warning(
                            f"No tenant mapping found for WhatsApp Phone ID: {whatsapp_phone_number_id} (message from {from_number}). Please configure this phone number in the tenants_config table.")
                        send_whatsapp_message(from_number,
                                              "I'm sorry, your account isn't configured for this service. Please contact support to set it up.")
                        continue
                    # --- END TENANT_ID DETERMINATION ---

                    logger.info(
                        f"Processing message of type '{message_type}' from {from_number} for Tenant: `{current_tenant_id}` (WhatsApp Phone ID: {whatsapp_phone_number_id})")

                    # Initialize variables for database storage to ensure they are strings
                    user_message_to_save = ""
                    final_ai_response_text_to_save = ""

                    if message_type == 'text':
                        user_message_raw = message['text']['body']
                        # Ensure user_message_to_save is a string, even if webhook sometimes sends objects
                        user_message_to_save = str(user_message_raw)
                        logger.info(
                            f"Received text message from {from_number}: '{user_message_to_save}' (Tenant: `{current_tenant_id}`)")

                        if not user_message_to_save.strip():
                            logger.info(f"Received empty or whitespace message from {from_number}. Ignoring.")
                            db_utils.add_message(wa_id, user_message_to_save, 'user', current_tenant_id,
                                                 'Ignored (empty/whitespace)')
                            return jsonify({"status": "success"}), 200

                        # Rate Limiting Check
                        last_message_time = db_utils.get_last_message_time(wa_id)
                        current_time = int(time.time())
                        time_since_last_message = current_time - last_message_time

                        if time_since_last_message < RATE_LIMIT_SECONDS:
                            wait_time_remaining = RATE_LIMIT_SECONDS - time_since_last_message
                            response_message = f"Please wait {int(wait_time_remaining)}s before sending another message."
                            logger.warning(
                                f"Rate limit hit for {from_number}. Remaining: {wait_time_remaining}s (Tenant: `{current_tenant_id}`).")
                            send_whatsapp_message(from_number, response_message)
                            db_utils.add_message(wa_id, user_message_to_save, 'user', current_tenant_id,
                                                 response_message)
                            return jsonify({"status": "rate_limited"}), 200

                        db_utils.update_last_message_time(wa_id)

                        # Get AI response object (might be string or an object)
                        ai_response_object = generate_ai_reply(user_message_to_save, wa_id)

                        # Robustly extract plain text from AI response for saving to DB
                        if ai_response_object:
                            if isinstance(ai_response_object, str):
                                final_ai_response_text_to_save = ai_response_object
                            elif hasattr(ai_response_object, 'text'):
                                final_ai_response_text_to_save = ai_response_object.text
                            elif hasattr(ai_response_object, 'candidates') and ai_response_object.candidates:
                                try:
                                    # Assuming the first candidate's first text part from content.parts
                                    parts_texts = [p.text for p in ai_response_object.candidates[0].content.parts if
                                                   hasattr(p, 'text')]
                                    final_ai_response_text_to_save = "".join(parts_texts)
                                except Exception as e:
                                    logger.warning(
                                        f"Could not parse Gemini response object for saving text (candidates): {e}")
                                    final_ai_response_text_to_save = str(
                                        ai_response_object)  # Fallback to stringifying object
                            else:
                                final_ai_response_text_to_save = str(
                                    ai_response_object)  # Fallback for other unexpected objects
                        else:
                            final_ai_response_text_to_save = ""  # If AI generated None

                        if final_ai_response_text_to_save:
                            success = send_whatsapp_message(from_number, final_ai_response_text_to_save)
                            if success:
                                db_utils.add_message(wa_id, user_message_to_save, 'user', current_tenant_id,
                                                     final_ai_response_text_to_save)
                                logger.info(
                                    f"Successfully sent AI response to {from_number} (Tenant: `{current_tenant_id}`).")
                            else:
                                logger.error(
                                    f"Failed to send response to {from_number} via WhatsApp API (Tenant: `{current_tenant_id}`).")
                                db_utils.add_message(wa_id, user_message_to_save, 'user', current_tenant_id,
                                                     'Failed to send response via API')
                        else:
                            fallback_message = "I'm sorry, I couldn't generate a response for that. Please try rephrasing your question or contact support at support@example.com."
                            logger.warning(
                                f"AI response was empty for message from {from_number}. Sending fallback (Tenant: `{current_tenant_id}`).")
                            send_whatsapp_message(from_number, fallback_message)
                            db_utils.add_message(wa_id, user_message_to_save, 'user', current_tenant_id,
                                                 fallback_message)

                    elif message_type == 'button':
                        button_payload = message.get('button', {}).get('payload')
                        user_message_to_save = f"Button Click: {button_payload}" if button_payload else "Button click (no payload)"
                        if button_payload:
                            logger.info(
                                f"Received button click from {from_number} with payload: {button_payload} (Tenant: `{current_tenant_id}`).")
                            response_message = f"You clicked: {button_payload}"
                            send_whatsapp_message(from_number, response_message)
                            db_utils.add_message(wa_id, user_message_to_save, 'user', current_tenant_id,
                                                 response_message)
                        else:
                            logger.warning(
                                f"Received button message from {from_number} but no payload found (Tenant: `{current_tenant_id}`).")
                            db_utils.add_message(wa_id, user_message_to_save, 'user', current_tenant_id,
                                                 'No action for button')

                    else:  # Handle other message types that are not text or button
                        user_message_to_save = f"Unhandled type: {message_type}"
                        logger.info(
                            f"Received unhandled message type '{message_type}' from {from_number} (Tenant: `{current_tenant_id}`).")
                        db_utils.add_message(wa_id, user_message_to_save, 'user', current_tenant_id,
                                             'Unsupported message type')

    return jsonify({"status": "success"}), 200


if __name__ == "__main__":
    # Set logging levels for imported modules if needed
    logging.getLogger('whatsapp_api_utils').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('db_utils').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('ai_utils').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))

    # --- IMPORTANT: Initial tenant configuration setup ---
    """
    # This block will add your first tenant mapping to the 'tenants_config' table.
    # Replace the placeholder values with your ACTUAL WhatsApp Business Phone Number ID
    # (found in your Meta Developers App Dashboard, e.g., 736065142913405 from your screenshot)
    # and your chosen unique tenant ID for this client.
    #
    # !!! YOU MUST COMMENT OUT OR REMOVE THIS BLOCK AFTER THE FIRST SUCCESSFUL RUN !!!
    # !!! Otherwise, it will try to add the same entry on every restart, which is harmless
    # !!! due to INSERT OR REPLACE, but unnecessary.
    #
    # You will also need a way to add new tenant configurations (new clients) in the future,
    # perhaps through an admin interface or a separate script.
    with app.app_context():
        # Get the WhatsApp Phone Number ID that your bot instance is associated with.
        # This is the 'metadata.phone_number_id' that comes in the webhook when YOUR bot sends/receives.
        # You've already got it in your .env as WHATSAPP_PHONE_NUMBER_ID for outgoing messages.
        # Use that as the key to map to your first tenant.

        # Ensure WHATSAPP_PHONE_NUMBER_ID is set in your .env for your primary test setup.
        # For example, from your screenshot, it's 736065142913405.
        YOUR_WHATSAPP_TEST_PHONE_ID_FROM_ENV = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

        # Choose a unique, internal ID for your first client/tenant
        YOUR_FIRST_INTERNAL_TENANT_ID = "my_initial_client_id"
        YOUR_FIRST_TENANT_NAME = "My Primary Test Client"

        if YOUR_WHATSAPP_TEST_PHONE_ID_FROM_ENV:
            if db_utils.get_tenant_id_from_whatsapp_phone_number(YOUR_WHATSAPP_TEST_PHONE_ID_FROM_ENV) is None:
                logger.info(
                    f"Adding initial tenant configuration for WhatsApp Phone ID: {YOUR_WHATSAPP_TEST_PHONE_ID_FROM_ENV}")
                db_utils.add_tenant_config(YOUR_WHATSAPP_TEST_PHONE_ID_FROM_ENV, YOUR_FIRST_INTERNAL_TENANT_ID,
                                           YOUR_FIRST_TENANT_NAME)
            else:
                logger.info(
                    f"Tenant configuration for WhatsApp Phone ID {YOUR_WHATSAPP_TEST_PHONE_ID_FROM_ENV} already exists in DB.")
        else:
            logger.error(
                "WHATSAPP_PHONE_NUMBER_ID environment variable not set. Cannot auto-add initial tenant config.")

    """
    # --- END IMPORTANT: Initial tenant configuration setup ---

    app.run(debug=os.getenv("FLASK_DEBUG", "False").lower() == "true", host='0.0.0.0', port=5000)