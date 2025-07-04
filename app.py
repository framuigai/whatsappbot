# app.py

from flask import Flask, request, abort
import logging
import os
from dotenv import load_dotenv
import requests
import google.generativeai as genai # <--- NEW: Import the Google Generative AI SDK
from google.generativeai.types import BlockedPromptException # <--- NEW: Import specific exception for safety blocks

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

# --- Load WhatsApp API credentials from .env (from Week 1) ---
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")

# --- NEW: Load Gemini API Key from .env (from Week 2 - Day 1) ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

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
if not GEMINI_API_KEY: # <--- NEW: Check for Gemini API key
    app.logger.error("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")
    exit(1)

# --- NEW: Configure Gemini API and Initialize Model Globally ---
try:
    genai.configure(
        api_key=GEMINI_API_KEY,
        client_options={"api_endpoint": "generativelanguage.googleapis.com"}
    )
    app.logger.info("Gemini API configured successfully.")
    gemini_model = genai.GenerativeModel('gemini-1.5-flash') # Initialize the model
    app.logger.info("Gemini-1.5-Flash model initialized globally.")
except Exception as e:
    app.logger.error(f"Failed to configure Gemini API or initialize model: {e}")
    gemini_model = None # Set to None if initialization fails, to prevent errors later
# --- END NEW GEMINI CONFIG ---


@app.route('/')
def hello_world():
    """
    A simple test route to ensure the Flask app is running.
    """
    app.logger.info("Hello World route accessed.")
    return 'Hello, World! This is your WhatsApp Bot MVP.'

# --- Helper function to send WhatsApp messages (from Week 1) ---
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
        return True
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Failed to send message to {to_number}. Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            app.logger.error(f"WhatsApp API Error Response: {e.response.text}")
        return False

# --- NEW FUNCTION: generate_ai_reply (for Week 2 - Day 2) ---
def generate_ai_reply(user_input, context=None): # Added context parameter for future use (Day 4)
    """
    Generates an AI response using the Gemini model.
    Includes basic error handling for common Gemini API issues.
    """
    if not gemini_model:
        app.logger.error("Gemini model not initialized. Cannot generate AI reply.")
        return "Sorry, my AI brain is currently offline. Please try again later!"

    # Define the system instruction/persona for your AI
    # This guides Gemini's behavior and tone.
    system_instruction = (
        "You are a helpful and friendly WhatsApp assistant. Your goal is to provide concise and accurate "
        "information, and engage in polite conversation. Keep your responses brief, typically under 100 words, "
        "unless more detail is specifically requested. Do not make up information. If you cannot answer, "
        "politely state so."
    )

    # For Day 2, context is not yet used, but the parameter is there for Day 4.
    # The prompt is a simple concatenation of system instruction and user input.
    # In Day 4, 'context' will be formatted into the 'contents' list for chat.
    current_prompt = f"{system_instruction}\n\nUser: {user_input}\nAssistant:"

    try:
        app.logger.info(f"Sending prompt to Gemini: {current_prompt[:100]}...") # Log a snippet of the prompt

        # Make the API call to Gemini
        # For now, we're sending a single-turn text prompt.
        response = gemini_model.generate_content(current_prompt)

        # Check if Gemini returned any text
        if response.text:
            app.logger.info(f"Received AI response: {response.text[:100]}...")
            return response.text.strip() # Return the cleaned AI text
        else:
            # Handle cases where Gemini might not return text (e.g., safety block, empty response)
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                block_reason = response.prompt_feedback.block_reason.name
                app.logger.warning(f"Gemini response blocked due to: {block_reason}")
                # Log safety ratings for debugging
                for rating in response.prompt_feedback.safety_ratings:
                    app.logger.warning(f"  {rating.category.name}: {rating.probability.name}")
                return "Sorry, I cannot respond to that. Your query might violate safety guidelines."
            else:
                app.logger.warning("Gemini returned an empty response with no block reason.")
                return "Sorry, I couldn't generate a response for that. Can you try rephrasing?"

    except BlockedPromptException as e: # Catch specific safety block exception
        app.logger.error(f"Prompt blocked by Gemini safety filters: {e}")
        return "I'm sorry, but I cannot process that request due to safety concerns. Please try a different query."
    except requests.exceptions.HTTPError as e: # Catch HTTP errors (e.g., 429 for rate limit, 401 for auth)
        if e.response.status_code == 429:
            app.logger.error(f"Gemini API rate limit exceeded: {e}")
            return "My apologies! I'm receiving too many requests right now. Please try again in a moment."
        else:
            app.logger.error(f"Gemini API HTTP error ({e.response.status_code}): {e}")
            app.logger.error(f"Gemini API Error Response: {e.response.text}")
            return "An unexpected error occurred with my AI brain. Please try again later."
    except Exception as e:
        # Catch any other general errors from the Gemini API call (e.g., network issues)
        app.logger.error(f"General error generating AI response from Gemini: {e}")
        return "Oops! My AI brain is currently unavailable due to an unexpected issue. Please try again in a few moments."
# --- END NEW generate_ai_reply FUNCTION ---


# Webhook endpoint for WhatsApp Cloud API
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
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
            if data and data.get('object') == 'whatsapp_business_account':
                # Iterate over each entry (there's usually only one)
                for entry in data.get('entry', []):
                    # Iterate over each change within the entry
                    for change in entry.get('changes', []):
                        # Check if the change is related to messages
                        if change.get('field') == 'messages':
                            value = change.get('value', {})
                            # Check if there are messages and if they are from the messaging_product 'whatsapp'
                            if 'messages' in value and value.get('messaging_product') == 'whatsapp':
                                for message in value.get('messages', []):
                                    # Get the sender's WhatsApp ID
                                    from_number = message.get('from')
                                    # Check message type
                                    if message.get('type') == 'text':
                                        # Extract the text message body
                                        msg_body = message.get('text', {}).get('body')
                                        app.logger.info(f"Received text message from {from_number}: {msg_body}")

                                        # --- OLD: Trigger static reply after receiving a message ---
                                        # static_reply = "Hello, I received your message! This is an automated reply."
                                        # send_whatsapp_message(to_number=from_number, message_text=static_reply)
                                        # --- END OLD REPLY TRIGGER ---
                                        # We will replace this with generate_ai_reply in Day 5

                                    elif message.get('type') == 'button':
                                        button_text = message.get('button', {}).get('text')
                                        app.logger.info(f"Received button click from {from_number}: {button_text}")
                                        static_reply = f"You clicked the button: {button_text}"
                                        send_whatsapp_message(to_number=from_number, message_text=static_reply)

                                    else:
                                        # Log other message types for now
                                        app.logger.info(f"Received non-text/button message type '{message.get('type')}' from {from_number}. Ignoring for now.")
                            # Handle message status updates (e.g., delivered, read)
                            elif 'statuses' in value and value.get('messaging_product') == 'whatsapp':
                                for status in value.get('statuses', []):
                                    app.logger.info(f"Message Status Update: ID {status.get('id')}, From: {status.get('recipient_id')}, Status: {status.get('status')}")
                            else:
                                app.logger.info("Received unhandled WhatsApp event (not messages or statuses).")
                        else:
                            app.logger.info(f"Received webhook field '{change.get('field', 'UNKNOWN')}'. Ignoring for now.")
            else:
                app.logger.info(f"Received webhook for object '{data.get('object', 'UNKNOWN')}'. Ignoring for now.")

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