# app.py

from flask import Flask, request, abort
import logging
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

app = Flask(__name__)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler()
                    ])

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
if not VERIFY_TOKEN:
    app.logger.error("VERIFY_TOKEN not found in environment variables. Please set it in your .env file.")
    exit(1)

@app.route('/')
def hello_world():
    app.logger.info("Hello World route accessed.")
    return 'Hello, World! This is your WhatsApp Bot MVP.'

# Webhook endpoint for WhatsApp Cloud API
@app.route('/webhook', methods=['GET', 'POST']) # <--- Add 'POST' to methods
def webhook(): # <--- Renamed function to handle both GET and POST
    if request.method == 'GET':
        """
        Handles the GET request for webhook verification.
        Meta sends a GET request to verify the webhook URL.
        """
        app.logger.info("Received Webhook GET request for verification.")

        # Parse params from the webhook verification request
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        # Check if a token and mode were sent
        if mode and token:
            if mode == "subscribe" and token == VERIFY_TOKEN:
                app.logger.info("WEBHOOK_VERIFIED: Successfully verified webhook.")
                return challenge, 200
            else:
                app.logger.warning(f"Webhook verification failed: Invalid token '{token}' or mode '{mode}'.")
                abort(403)
        else:
            app.logger.warning("Webhook verification failed: Missing 'hub.mode' or 'hub.verify_token' in request.")
            abort(400)

    elif request.method == 'POST':
        """
        Handles the POST request for incoming messages from WhatsApp.
        """
        app.logger.info("Received Webhook POST request (incoming message).")
        data = request.get_json() # Parse the incoming JSON data

        app.logger.info(f"Incoming Webhook Data: {data}") # Log the full incoming payload for inspection

        try:
            # Standard WhatsApp Cloud API webhook payload structure
            # Check if the 'object' is 'whatsapp_business_account'
            if data['object'] == 'whatsapp_business_account':
                # Iterate over each entry (there's usually only one)
                for entry in data['entry']:
                    # Iterate over each change within the entry
                    for change in entry['changes']:
                        # Check if the change is related to messages
                        if change['field'] == 'messages':
                            value = change['value']
                            # Check if there are messages and if they are from the messaging_product 'whatsapp'
                            if 'messages' in value and value['messaging_product'] == 'whatsapp':
                                for message in value['messages']:
                                    # Get the sender's WhatsApp ID
                                    from_number = message['from']
                                    # Check message type
                                    if message['type'] == 'text':
                                        # Extract the text message body
                                        msg_body = message['text']['body']
                                        app.logger.info(f"Received message from {from_number}: {msg_body}")
                                        # TODO: In future steps, this is where you'd process the message and send a reply
                                    else:
                                        # Log other message types for now
                                        app.logger.info(f"Received non-text message type '{message['type']}' from {from_number}. Ignoring for now.")
                            # Handle message status updates (e.g., delivered, read)
                            elif 'statuses' in value and value['messaging_product'] == 'whatsapp':
                                for status in value['statuses']:
                                    app.logger.info(f"Message Status Update: ID {status['id']}, Status: {status['status']}")
                            else:
                                app.logger.info("Received unhandled WhatsApp event (not messages or statuses).")
                        else:
                            app.logger.info(f"Received webhook field '{change['field']}'. Ignoring for now.")
            else:
                app.logger.info(f"Received webhook for object '{data['object']}'. Ignoring for now.")

        except Exception as e:
            app.logger.error(f"Error processing webhook POST request: {e}")
            app.logger.error(f"Full payload causing error: {data}") # Log the full payload if an error occurs

        # Always return a 200 OK status to Meta regardless of content or errors
        # This prevents Meta from retrying the webhook
        return '', 200

# This block ensures the Flask app runs only when the script is executed directly
if __name__ == '__main__':
    app.logger.info("Flask application starting...")
    app.run(debug=True, port=5000)