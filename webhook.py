# webhook.py
import json
import logging
import time
from flask import Blueprint, request, jsonify
from config import VERIFY_TOKEN, RATE_LIMIT_SECONDS, WHATSAPP_PHONE_NUMBER_ID, LOGGING_LEVEL, log_level_map
from whatsapp_api_utils import send_whatsapp_message
import db_utils
from ai_utils import generate_ai_reply # generate_embedding not needed here, only for FAQ setup

webhook_bp = Blueprint('webhook', __name__)
logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO)) # Set level for this module


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