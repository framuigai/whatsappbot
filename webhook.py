# webhook.py
import json
import logging
import time
from flask import Blueprint, request, jsonify
from config import VERIFY_TOKEN, RATE_LIMIT_SECONDS, WHATSAPP_PHONE_NUMBER_ID, LOGGING_LEVEL, log_level_map

# --- START MODIFICATION FOR DB REFACTORING ---
# Removed: import db_utils
# New: Import specific functions from the new database modules
from db.conversations_crud import add_message, get_conversation_history_by_whatsapp_id # ADDED get_conversation_history_by_whatsapp_id
from db.tenants_crud import get_tenant_config_by_whatsapp_id
# --- END MODIFICATION FOR DB REFACTORING ---

from whatsapp_api_utils import send_whatsapp_message
from ai_utils import generate_ai_reply # generate_embedding not needed here, only for FAQ setup

webhook_bp = Blueprint('webhook', __name__)
logger = logging.getLogger(__name__) # Logger for this module
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO)) # Set level for this module

# Dictionary to store last message timestamp for rate limiting
last_message_time = {}

@webhook_bp.route("/webhook", methods=["GET"])
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
            f"Webhook verification failed. Mode: {mode}, Token received: {token}, Expected Token: {VERIFY_TOKEN}"
        )
        return "Verification failed", 403

@webhook_bp.route("/webhook", methods=["POST"])
def handle_webhook():
    """
    Handles incoming WhatsApp messages from the Meta Webhooks.
    """
    if request.method == 'POST':
        try:
            data = request.get_json()
            logger.debug(f"Received webhook event: {json.dumps(data, indent=2)}")

            # Check if the webhook event is a message from a WhatsApp Business Account
            if "object" in data and "entry" in data:
                for entry in data["entry"]:
                    for change in entry["changes"]:
                        if "value" in change and "messages" in change["value"]:
                            message = change["value"]["messages"][0]
                            from_number = message["from"]
                            message_type = message["type"]
                            wa_id = from_number # Use from_number as wa_id

                            # Get tenant_id from tenant_config based on WHATSAPP_PHONE_NUMBER_ID
                            tenant_config = get_tenant_config_by_whatsapp_id(WHATSAPP_PHONE_NUMBER_ID)
                            current_tenant_id = tenant_config['tenant_id'] if tenant_config else 'default_tenant'
                            logger.info(f"Processing message for tenant: `{current_tenant_id}` (WA ID: {wa_id})")

                            # Implement basic rate limiting
                            now = time.time()
                            if wa_id in last_message_time and (now - last_message_time[wa_id] < RATE_LIMIT_SECONDS):
                                logger.warning(f"Rate limit exceeded for {wa_id}. Ignoring message.")
                                return jsonify({"status": "ignored", "message": "Rate limit exceeded"}), 200
                            last_message_time[wa_id] = now

                            user_message_to_save = ""
                            response_message = "" # Initialize response_message

                            if message_type == "text":
                                user_message_content = message["text"]["body"]
                                user_message_to_save = user_message_content
                                logger.info(
                                    f"Received text message from {from_number} (Tenant: `{current_tenant_id}`): '{user_message_content}'"
                                )

                                # Generate AI reply
                                # MODIFIED: generate_ai_reply now returns a dict
                                ai_response_data = generate_ai_reply(user_message_content, wa_id, current_tenant_id)
                                response_message = ai_response_data.get("response", "I'm sorry, I couldn't generate a response.")

                                send_whatsapp_message(from_number, response_message)

                                # Store both user message and AI response
                                # Updated: Use conversations_crud.add_message
                                add_message(wa_id, user_message_to_save, 'user', current_tenant_id, response_message)


                            elif message_type == "button":
                                button_payload = message["button"]["payload"]
                                user_message_to_save = f"Button click: {button_payload}" # Save button click as user message

                                if button_payload:
                                    logger.info(
                                        f"Received button message from {from_number} with payload '{button_payload}' (Tenant: `{current_tenant_id}`).")

                                    # Here you would typically have logic to handle specific button payloads
                                    # For this example, we'll just echo the payload
                                    response_message = f"You clicked: {button_payload}"
                                    send_whatsapp_message(from_number, response_message)
                                    # Updated: Use conversations_crud.add_message
                                    add_message(wa_id, user_message_to_save, 'user', current_tenant_id,
                                                         response_message)
                                else:
                                    logger.warning(
                                        f"Received button message from {from_number} but no payload found (Tenant: `{current_tenant_id}`).")
                                    # Updated: Use conversations_crud.add_message
                                    add_message(wa_id, user_message_to_save, 'user', current_tenant_id,
                                                         'No action for button')

                            else:  # Handle other message types that are not text or button
                                user_message_to_save = f"Unhandled type: {message_type}"
                                logger.info(
                                    f"Received unhandled message type '{message_type}' from {from_number} (Tenant: `{current_tenant_id}`).")
                                # Updated: Use conversations_crud.add_message
                                add_message(wa_id, user_message_to_save, 'user', current_tenant_id,
                                                     'Unsupported message type')

                            logger.info(f"Processed and responded to {from_number} (Tenant: `{current_tenant_id}`).")

        except Exception as e: # This except block should be for the outermost try block within the POST request
            logger.error(f"Error processing webhook event: {e}", exc_info=True)
            return jsonify({"status": "error", "message": "Internal server error"}), 500

    return jsonify({"status": "success"}), 200 # This return should be at the same level as the initial "if request.method == 'POST':"