# app.py

from flask import Flask, request, abort
import logging
import os
from dotenv import load_dotenv
import requests # <--- NEW: Import the requests library

# Load environment variables from .env file
load_dotenv()

# Initialize the Flask application
app = Flask(__name__)

# Configure logging for better visibility
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler() # Logs to PyCharm console
                    ])

# --- NEW: Load WhatsApp API credentials from .env ---
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")

# Basic error checking for environment variables
if not VERIFY_TOKEN:
    app.logger.error("VERIFY_TOKEN not found in environment variables. Please set it in your .env file.")
    exit(1)
if not WHATSAPP_ACCESS_TOKEN:
    app.logger.error("WHATSAPP_ACCESS_TOKEN not found in environment variables. Please set it in your .env file.")
    exit(1)
if not WHATSAPP_PHONE_NUMBER_ID:
    app.logger.error("WHATSAPP_PHONE_NUMBER_ID not found in environment variables. Please set it in your .env file.")
    exit(1)
# --- END NEW VAR LOAD ---


@app.route('/')
def hello_world():
    """
    A simple test route to ensure the Flask app is running.
    """
    app.logger.info("Hello World route accessed.")
    return 'Hello, World! This is your WhatsApp Bot MVP.'

# --- NEW FUNCTION: To send messages via WhatsApp Cloud API ---
def send_whatsapp_message(to_number, message_text):
    """
    Sends a text message to a given WhatsApp number using the WhatsApp Cloud API.
    """
    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message_text},
    }

    app.logger.info(f"Attempting to send message to {to_number}: '{message_text}'")
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        app.logger.info(f"Message sent successfully to {to_number}. Response: {response.json()}")
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Failed to send message to {to_number}. Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            app.logger.error(f"Meta API Error Response: {e.response.text}")
# --- END NEW FUNCTION ---


# Webhook endpoint for WhatsApp Cloud API
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # --- Handles GET request for webhook verification (from Day 4) ---
        app.logger.info("Received Webhook GET request for verification.")

        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode and token:
            if mode == "subscribe" and token == VERIFY_TOKEN:
                app.logger.info("WEBHOOK_VERIFIED: Successfully verified webhook.")
                return challenge, 200
            else:
                app.logger.warning(f"Webhook verification failed: Invalid token '{token}' or mode '{mode}'.")
                abort(403) # Forbidden
        else:
            app.logger.warning("Webhook verification failed: Missing 'hub.mode' or 'hub.verify_token'.")
            abort(400) # Bad Request

    elif request.method == 'POST':
        # --- Handles POST request for incoming messages (from Day 5) ---
        app.logger.info("Received Webhook POST request (incoming message).")
        data = request.get_json() # Parse the incoming JSON payload from Meta

        app.logger.info(f"Incoming Webhook Data: {data}") # Log the full incoming payload for debugging

        try:
            if data and data.get('object') == 'whatsapp_business_account':
                for entry in data.get('entry', []):
                    for change in entry.get('changes', []):
                        if change.get('field') == 'messages':
                            value = change.get('value', {})
                            if 'messages' in value and value.get('messaging_product') == 'whatsapp':
                                for message in value.get('messages', []):
                                    from_number = message.get('from') # Sender's WhatsApp ID

                                    if message.get('type') == 'text':
                                        msg_body = message.get('text', {}).get('body')
                                        app.logger.info(f"Received text message from {from_number}: {msg_body}")

                                        # --- NEW: Trigger static reply after receiving a message ---
                                        static_reply = "Hello, I received your message! This is an automated reply."
                                        send_whatsapp_message(to_number=from_number, message_text=static_reply)
                                        # --- END NEW REPLY TRIGGER ---

                                    elif message.get('type') == 'button':
                                        button_text = message.get('button', {}).get('text')
                                        app.logger.info(f"Received button click from {from_number}: {button_text}")
                                        static_reply = f"You clicked the button: {button_text}"
                                        send_whatsapp_message(to_number=from_number, message_text=static_reply)

                                    else:
                                        app.logger.info(f"Received non-text/button message type '{message.get('type')}' from {from_number}. Ignoring for now.")

                            elif 'statuses' in value and value.get('messaging_product') == 'whatsapp':
                                for status in value.get('statuses', []):
                                    app.logger.info(f"Message Status Update: ID {status.get('id')}, From: {status.get('recipient_id')}, Status: {status.get('status')}")
                            else:
                                app.logger.info("Received unhandled WhatsApp event (not messages or statuses).")
                        else:
                            app.logger.info(f"Received webhook field '{change.get('field', 'UNKNOWN')}'. Ignoring for now.")
            else:
                app.logger.info(f"Received webhook for object '{data.get('object', 'UNKNOWN')}'. Ignoring for now.")

            # CRITICAL: Always return a 200 OK status to Meta
            return '', 200

        except Exception as e:
            app.logger.error(f"Error processing webhook POST request: {e}")
            app.logger.error(f"Full payload causing error: {data}")
            return '', 200 # Still return 200 OK even on error to prevent retries

# This block ensures the Flask app runs only when the script is executed directly
if __name__ == '__main__':
    app.logger.info("Flask application starting...")
    app.run(debug=True, port=5000)