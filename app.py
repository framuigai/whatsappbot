# app.py

from flask import Flask, request, abort
import logging
import os
from dotenv import load_dotenv
import requests
import google.generativeai as genai
from google.generativeai.types import BlockedPromptException
import sqlite3
import time

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

# --- Load Gemini API Key from .env (from Week 2 - Day 1) ---
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
if not GEMINI_API_KEY:
    app.logger.error("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")
    exit(1)

# --- Configure Gemini API and Initialize Model Globally ---
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


# --- NEW: SQLite Database Configuration and Helper Functions (for Week 2 - Day 3) ---
DB_FILE = 'conversations.db' # Define the database file name

def init_db():
    """Initializes the SQLite database and creates the conversations table."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                message TEXT NOT NULL,
                is_bot INTEGER NOT NULL, -- 0 for user, 1 for bot
                timestamp INTEGER NOT NULL
            );
        ''')
        conn.commit()
        app.logger.info(f"Database '{DB_FILE}' initialized and 'conversations' table ensured.")
    except sqlite3.Error as e:
        app.logger.error(f"Error initializing database: {e}")
    finally:
        if conn:
            conn.close()

def save_message(user_id, message, is_bot):
    """Saves a message to the database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # Using UNIX timestamp (seconds since epoch)
        timestamp = int(time.time())
        cursor.execute(
            "INSERT INTO conversations (user_id, message, is_bot, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, message, 1 if is_bot else 0, timestamp)
        )
        conn.commit()
        app.logger.info(f"Message saved for {user_id}: {'Bot' if is_bot else 'User'} - '{message[:50]}...'")
    except sqlite3.Error as e:
        app.logger.error(f"Error saving message for {user_id}: {e}")
    finally:
        if conn:
            conn.close()

def get_conversation_history(user_id, limit=20):
    """
    Fetches the most recent conversation history for a user,
    formatted for Gemini's ChatSession.
    """
    conn = None
    history = []
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # Fetching messages in chronological order, limited by 'limit'
        cursor.execute(
            "SELECT message, is_bot FROM conversations WHERE user_id = ? ORDER BY timestamp ASC LIMIT ?",
            (user_id, limit)
        )
        rows = cursor.fetchall()

        # Format history for Gemini ChatSession (list of {"role": ..., "parts": [...]})
        for message_text, is_bot_val in rows:
            role = "model" if is_bot_val == 1 else "user"
            history.append({"role": role, "parts": [{"text": message_text}]})

        app.logger.info(f"Fetched {len(history)} messages for {user_id}.")
    except sqlite3.Error as e:
        app.logger.error(f"Error fetching conversation history for {user_id}: {e}")
    finally:
        if conn:
            conn.close()
    return history

# Define the system instruction/persona for your AI globally
# This will be used when starting a new chat session or building history.
SYSTEM_INSTRUCTION = (
    "You are a helpful and friendly WhatsApp assistant. Your goal is to provide concise and accurate "
    "information, and engage in polite conversation. Keep your responses brief, typically under 100 words, "
    "unless more detail is specifically requested. Do not make up information. If you cannot answer, "
    "politely state so."
)


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

# --- Modified generate_ai_reply to use SQLite for history (for Week 2 - Day 3) ---
def generate_ai_reply(user_id, user_input):
    """
    Generates an AI response using the Gemini model, incorporating conversation history
    retrieved from SQLite for the given user_id.
    """
    if not gemini_model:
        app.logger.error("Gemini model not initialized. Cannot generate AI reply.")
        return "Sorry, my AI brain is currently offline. Please try again later!"

    # 1. Retrieve full conversation history for the user from the database
    #    The SYSTEM_INSTRUCTION is prepended to ensure AI always has its persona.
    #    Gemini's 'history' expects a list of {"role": "user/model", "parts": [{"text": ...}]}
    retrieved_history = get_conversation_history(user_id)

    # Initialize a new ChatSession with the entire history from the DB + system instruction
    # The system instruction is provided as the first user turn in the history to set context.
    # This design means the system instruction is resent with every request, ensuring persistent persona.
    chat_session = gemini_model.start_chat(history=[
        {"role": "user", "parts": [{"text": SYSTEM_INSTRUCTION}]}
    ] + retrieved_history) # Prepend system instruction to the retrieved history


    try:
        app.logger.info(f"Sending user input to Gemini for {user_id}: {user_input[:100]}...")

        # 2. Send the user's message to the chat session.
        #    The chat session automatically appends this to history and sends the full context.
        response = chat_session.send_message(user_input)

        ai_reply = ""
        # Check if Gemini returned any text
        if response.text:
            ai_reply = response.text.strip()
            app.logger.info(f"Received AI response for {user_id}: {ai_reply[:100]}...")
            # 3. Save both user input and AI reply to the database
            save_message(user_id, user_input, is_bot=False)
            save_message(user_id, ai_reply, is_bot=True)
            return ai_reply
        else:
            # Handle cases where Gemini might not return text (e.g., safety block)
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                block_reason = response.prompt_feedback.block_reason.name
                app.logger.warning(f"Gemini response blocked for {user_id} due to: {block_reason}")
                for rating in response.prompt_feedback.safety_ratings:
                    app.logger.warning(f"  {rating.category.name}: {rating.probability.name}")
                # Save user message even if bot reply is blocked/empty
                save_message(user_id, user_input, is_bot=False)
                return "Sorry, I cannot respond to that. Your query might violate safety guidelines."
            else:
                app.logger.warning(f"Gemini returned an empty response for {user_id} with no block reason.")
                # Save user message even if bot reply is blocked/empty
                save_message(user_id, user_input, is_bot=False)
                return "Sorry, I couldn't generate a response for that. Can you try rephrasing?"

    except BlockedPromptException as e:
        app.logger.error(f"Prompt blocked by Gemini safety filters for {user_id}: {e}")
        # Save user message even if prompt itself is blocked
        save_message(user_id, user_input, is_bot=False)
        return "I'm sorry, but I cannot process that request due to safety concerns. Please try a different query."
    except requests.exceptions.HTTPError as e:
        app.logger.error(f"Gemini API HTTP error ({e.response.status_code}) for {user_id}: {e}")
        app.logger.error(f"Gemini API Error Response: {e.response.text}")
        # Save user message even if API call fails
        save_message(user_id, user_input, is_bot=False) # Still log user message to DB for audit
        if e.response.status_code == 429:
            return "My apologies! I'm receiving too many requests right now. Please try again in a moment."
        else:
            return "An unexpected error occurred with my AI brain. Please try again later."
    except Exception as e:
        app.logger.error(f"General error generating AI response for {user_id}: {e}")
        # Save user message even if general error occurs
        save_message(user_id, user_input, is_bot=False) # Still log user message to DB for audit
        return "Oops! My AI brain is currently unavailable due to an unexpected issue. Please try again in a few moments."

# --- Your existing Flask routes will go here ---
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
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
                abort(403)
        else:
            app.logger.warning("Webhook verification failed: Missing 'hub.mode' or 'hub.verify_token' in request.")
            abort(400)

    elif request.method == 'POST':
        app.logger.info("Received Webhook POST request (incoming message).")
        data = request.get_json()
        app.logger.info(f"Incoming Webhook Data: {data}")

        try:
            if data and data.get('object') == 'whatsapp_business_account':
                for entry in data.get('entry', []):
                    for change in entry.get('changes', []):
                        if change.get('field') == 'messages':
                            value = change.get('value', {})
                            if 'messages' in value and value.get('messaging_product') == 'whatsapp':
                                for message in value.get('messages', []):
                                    from_number = message.get('from')

                                    if message.get('type') == 'text':
                                        msg_body = message.get('text', {}).get('body')
                                        app.logger.info(f"Received text message from {from_number}: {msg_body}")

                                        # --- NEW: Generate AI reply and send it back ---
                                        ai_response = generate_ai_reply(user_id=from_number, user_input=msg_body)
                                        if ai_response:
                                            send_whatsapp_message(to_number=from_number, message_text=ai_response)
                                        else:
                                            app.logger.error(f"Failed to generate AI response for {from_number}: '{msg_body}'")
                                            send_whatsapp_message(to_number=from_number, message_text="Sorry, I couldn't process your request right now.")
                                        # --- END NEW ---

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

        except Exception as e:
            app.logger.error(f"Error processing webhook POST request: {e}")
            app.logger.error(f"Full payload causing error: {data}")

        return '', 200

# This block ensures the Flask app runs only when the script is executed directly
if __name__ == '__main__':
    # --- NEW: Initialize the database when the Flask app starts ---
    init_db()
    app.logger.info("Flask application starting...")
    app.run(debug=True, port=5000)