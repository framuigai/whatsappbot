# webhook.py
import json
import logging
import time
from flask import Blueprint, request, jsonify
from config import VERIFY_TOKEN, RATE_LIMIT_SECONDS, WHATSAPP_PHONE_NUMBER_ID, LOGGING_LEVEL, log_level_map
from whatsapp_api_utils import send_whatsapp_message
import db_utils
from ai_utils import generate_ai_reply  # generate_embedding not needed here, only for FAQ setup

webhook_bp = Blueprint('webhook', __name__)
logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))  # Set level for this module


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
            f"Webhook verification failed. Mode: {mode}, Token received: {token}, Expected Token: {VERIFY_TOKEN}")
        return "Verification failed", 403


@webhook_bp.route("/webhook", methods=["POST"])
def handle_webhook():
    """
    Handles incoming webhook events from WhatsApp.
    """
    try:
        data = request.get_json()
        logger.info(f"Received webhook event: {json.dumps(data, indent=2)}")

        if not data or "object" not in data or "entry" not in data:
            logger.warning("Invalid webhook event structure.")
            return jsonify({"status": "error", "message": "Invalid event structure"}), 400

        for entry in data["entry"]:
            for change in entry["changes"]:
                if "value" in change and "messages" in change["value"]:
                    for message in change["value"]["messages"]:
                        from_number = message["from"]  # WhatsApp ID of the sender
                        message_type = message["type"]
                        timestamp = int(time.time())  # Current time for logging/db

                        # --- Tenant Identification ---
                        # IMPORTANT: This is where the WHATSAPP_PHONE_NUMBER_ID of the *receiving* bot
                        # is used to identify which tenant this message belongs to.
                        # You would map this WHATSAPP_PHONE_NUMBER_ID to your internal tenant_id.
                        # For now, we use the global WHATSAPP_PHONE_NUMBER_ID from config.
                        # In a multi-tenant setup, you'd get this from change['value']['metadata']['phone_number_id']
                        # and then look up the tenant_id in your db_utils.

                        # Corrected line:
                        current_tenant_id = db_utils.get_tenant_id_from_whatsapp_phone_number(WHATSAPP_PHONE_NUMBER_ID)

                        if not current_tenant_id:
                            logger.error(
                                f"No tenant found for WHATSAPP_PHONE_NUMBER_ID: {WHATSAPP_PHONE_NUMBER_ID}. Cannot process message from {from_number}.")
                            send_whatsapp_message(from_number,
                                                  "Sorry, I'm unable to process your request at the moment. Please try again later.")
                            return jsonify({"status": "error", "message": "Tenant not configured"}), 404

                        # Use the 'from' number (wa_id) as the unique identifier for the conversation
                        wa_id = from_number

                        user_message_to_save = ""  # Initialize for potential logging/DB
                        response_message = "I'm sorry, I didn't understand that."  # Default response

                        if message_type == "text":
                            user_message = message["text"]["body"]
                            user_message_to_save = user_message
                            logger.info(
                                f"Received message from {from_number} (Tenant: `{current_tenant_id}`): '{user_message}'")

                            # Generate AI reply
                            response_message = generate_ai_reply(user_message, current_tenant_id)
                            send_whatsapp_message(from_number, response_message)
                            db_utils.add_message(wa_id, user_message_to_save, 'user', current_tenant_id,
                                                 response_message)

                        elif message_type == "button":
                            button_payload = message["button"]["payload"]
                            user_message_to_save = f"Button Click: {button_payload}"
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

    except Exception as e:
        logger.error(f"Error processing webhook event: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

    return jsonify({"status": "success"}), 200