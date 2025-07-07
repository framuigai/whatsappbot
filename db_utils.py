import sqlite3
import logging
import time # For last message time tracking
import json # Required for serializing/deserializing embeddings
import os   # Required to load DATABASE_NAME from .env
from dotenv import load_dotenv # To ensure .env is loaded if this file is run standalone
# Removed: from ai_utils import generate_embedding - this import is not needed here
# db_utils should not directly depend on ai_utils for core DB operations to avoid circular imports.
# The embedding generation should be handled by the caller (add_faq in app.py or a service layer).

# Load environment variables (good practice if this file might be run standalone)
load_dotenv()

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATABASE_NAME = os.getenv('DATABASE_NAME', 'conversations.db') # Load from .env, default if not set

def get_db_connection():
    """Establishes and returns a database connection."""
    return sqlite3.connect(DATABASE_NAME)

def create_conversations_table():
    """Creates the conversations table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wa_id TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            message_text TEXT NOT NULL,
            sender TEXT NOT NULL,
            response_text TEXT
        )
    ''')
    conn.commit()
    conn.close()
    logging.info("Conversations table checked/created successfully.")

def create_last_message_time_table():
    """Creates a table to store the last message timestamp for rate limiting."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS last_message_times (
            wa_id TEXT PRIMARY KEY,
            last_timestamp INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    logging.info("Last message times table checked/created successfully.")

def create_faqs_table():
    """Creates the faqs table if it doesn't exist, including the embedding column."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            embedding TEXT  -- Stores JSON string of the embedding
        )
    ''')
    conn.commit()
    conn.close()
    logging.info("FAQs table checked/created successfully.")

def init_db():
    """Initializes all necessary database tables."""
    create_conversations_table()
    create_last_message_time_table()
    create_faqs_table()
    logging.info("Database initialized successfully.")

def add_message(wa_id, message_text, sender, response_text=None):
    """Adds a message to the conversation history."""
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = int(time.time())
    try:
        cursor.execute(
            "INSERT INTO conversations (wa_id, timestamp, message_text, sender, response_text) VALUES (?, ?, ?, ?, ?)",
            (wa_id, timestamp, message_text, sender, response_text)
        )
        conn.commit()
        logging.debug(f"Message added for {wa_id}: '{message_text}'")
        return cursor.lastrowid
    except sqlite3.Error as e:
        logging.error(f"Error adding message to DB for {wa_id}: {e}")
        return None
    finally:
        conn.close()

def get_message_history(wa_id, limit=10):
    """Retrieves conversation history for a given WhatsApp ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT message_text, response_text, sender FROM conversations WHERE wa_id = ? ORDER BY timestamp DESC LIMIT ?",
        (wa_id, limit)
    )
    # Fetch all and reverse to get chronological order
    history = cursor.fetchall()
    conn.close()

    formatted_history = []
    for row in reversed(history):
        user_message, bot_response, sender = row
        if sender == 'user':
            formatted_history.append({'role': 'user', 'parts': [user_message]})
            if bot_response:
                formatted_history.append({'role': 'model', 'parts': [bot_response]})
        elif sender == 'model':
            pass # We log bot responses as part of the user's message entry for simplicity
    return formatted_history

def update_last_message_time(wa_id):
    """Updates the last message timestamp for a given WhatsApp ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = int(time.time())
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO last_message_times (wa_id, last_timestamp) VALUES (?, ?)",
            (wa_id, current_time)
        )
        conn.commit()
        logging.debug(f"Last message time updated for {wa_id} to {current_time}")
    except sqlite3.Error as e:
        logging.error(f"Error updating last message time for {wa_id}: {e}")
    finally:
        conn.close()

def get_last_message_time(wa_id):
    """Retrieves the last message timestamp for a given WhatsApp ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT last_timestamp FROM last_message_times WHERE wa_id = ?", (wa_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

# --- FAQ Functions ---
# Note: generate_embedding is now called in app.py when adding FAQs to avoid circular import with ai_utils
def add_faq(question, answer, embedding): # embedding is now passed as an argument
    """Adds a new FAQ to the database with its pre-generated embedding."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if embedding is None:
        logging.error(f"Cannot add FAQ '{question}' - embedding is None.")
        conn.close()
        return None

    try:
        # Store the embedding as a JSON string
        cursor.execute("INSERT INTO faqs (question, answer, embedding) VALUES (?, ?, ?)",
                       (question, answer, json.dumps(embedding)))
        conn.commit()
        logging.info(f"FAQ added successfully with embedding: Q='{question[:50]}...'")
        return cursor.lastrowid
    except sqlite3.Error as e:
        logging.error(f"Error adding FAQ to DB: {e}")
        return None
    finally:
        conn.close()

def get_all_faqs():
    """Retrieves all FAQs from the database, including embeddings (as JSON strings)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, question, answer, embedding FROM faqs")
    faqs = []
    for row in cursor.fetchall():
        faq_item = {"id": row[0], "question": row[1], "answer": row[2]}
        if row[3]: # Check if embedding exists
            try:
                # CRITICAL FIX: Parse JSON string back to list for ai_utils.cosine_similarity
                faq_item["embedding"] = json.loads(row[3])
            except json.JSONDecodeError:
                logging.error(f"Error decoding embedding JSON for FAQ ID {row[0]}. Setting embedding to None.")
                faq_item["embedding"] = None # Set to None if decoding fails
        else:
            faq_item["embedding"] = None
        faqs.append(faq_item)
    conn.close()
    return faqs

def delete_faq(faq_id):
    """Deletes an FAQ by its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM faqs WHERE id = ?", (faq_id,))
        conn.commit()
        if cursor.rowcount > 0:
            logging.info(f"FAQ with ID {faq_id} deleted successfully.")
            return True
        else:
            logging.warning(f"No FAQ found with ID {faq_id} for deletion.")
            return False
    except sqlite3.Error as e:
        logging.error(f"Error deleting FAQ with ID {faq_id}: {e}")
        return False
    finally:
        conn.close()