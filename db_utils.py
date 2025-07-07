import sqlite3
import logging
import time # For last message time tracking

# Configure logging for this module
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATABASE_NAME = 'conversations.db' # Define your database name here

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
    """Creates the faqs table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            embedding TEXT  -- Will store JSON string of the embedding
        )
    ''')
    conn.commit()
    conn.close()
    logging.info("FAQs table checked/created successfully.")

def init_db():
    """Initializes all necessary database tables."""
    create_conversations_table()
    create_last_message_time_table() # Ensure this is called
    create_faqs_table() # New: Ensure FAQs table is created
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

    # Format history for Gemini (user/model roles)
    formatted_history = []
    for row in reversed(history):
        user_message, bot_response, sender = row
        if sender == 'user':
            formatted_history.append({'role': 'user', 'parts': [user_message]})
            if bot_response: # If the bot already responded to this message
                formatted_history.append({'role': 'model', 'parts': [bot_response]})
        elif sender == 'model':
            # This case might happen if a bot message is explicitly logged or if
            # the history retrieval includes partial turns. Adjust logic if needed.
            # For our current flow, 'model' messages are logged as response_text to 'user' messages.
            pass
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

# --- New FAQ Functions for Day 1 ---
def add_faq(question, answer, embedding=""): # Embedding will be populated in Day 2
    """Adds a new FAQ to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO faqs (question, answer, embedding) VALUES (?, ?, ?)",
                       (question, answer, embedding))
        conn.commit()
        logging.info(f"FAQ added: Q='{question[:50]}...'")
        return cursor.lastrowid
    except sqlite3.Error as e:
        logging.error(f"Error adding FAQ: {e}")
        return None
    finally:
        conn.close()

def get_all_faqs():
    """Retrieves all FAQs from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, question, answer, embedding FROM faqs")
    faqs = [{"id": row[0], "question": row[1], "answer": row[2], "embedding": row[3]} for row in cursor.fetchall()]
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