# app.py

from flask import Flask, request, abort # Import request and abort
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the Flask application
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.StreamHandler()
                    ])

# Get VERIFY_TOKEN from environment variables
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
if not VERIFY_TOKEN:
    app.logger.error("VERIFY_TOKEN not found in environment variables. Please set it in your .env file.")
    exit(1) # Exit if this critical variable is missing

@app.route('/')
def hello_world():
    app.logger.info("Hello World route accessed.")
    return 'Hello, World! This is your WhatsApp Bot MVP.'

# Webhook endpoint for WhatsApp Cloud API
@app.route('/webhook', methods=['GET']) # <--- This defines the GET endpoint
def webhook_get():
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
        # Check the mode and verify token to ensure it's a valid setup request
        if mode == "subscribe" and token == VERIFY_TOKEN:
            # Respond with 200 OK and challenge token from the request
            app.logger.info("WEBHOOK_VERIFIED: Successfully verified webhook.")
            return challenge, 200 # Return the challenge back to Meta
        else:
            # Responds with '403 Forbidden' if verify tokens do not match
            app.logger.warning(f"Webhook verification failed: Invalid token '{token}' or mode '{mode}'.")
            abort(403) # Return 403 Forbidden
    else:
        app.logger.warning("Webhook verification failed: Missing 'hub.mode' or 'hub.verify_token' in request.")
        abort(400) # Bad Request if parameters are missing

# This block ensures the Flask app runs only when the script is executed directly
if __name__ == '__main__':
    app.logger.info("Flask application starting...")
    # Ensure debug mode is off in production
    app.run(debug=True, port=5000)