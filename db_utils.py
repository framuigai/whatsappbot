import sqlite3
import logging
import time
import json
import os
from dotenv import load_dotenv

# Load environment variables (important if this file is run standalone for testing)
load_dotenv()

# --- Logging Configuration ---
logger = logging.getLogger(__name__)

DATABASE_NAME = os.getenv('DATABASE_NAME', 'conversations.db')


def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row  # Allows accessing columns by name
        return conn
    except sqlite3.Error as e:
        logger.critical(f"Error connecting to database {DATABASE_NAME}: {e}")
        raise  # Re-raise to halt execution if DB connection fails


def create_conversations_table():
    """
    Creates the conversations table if it doesn't exist.
    Adds 'tenant_id' column if it's missing.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wa_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                sender TEXT NOT NULL, -- 'user' or 'model'
                response_text TEXT -- The bot's reply to this specific user message
            )
        ''')

        # --- NEW ADDITION FOR TENANT_ID ---
        # Check if tenant_id column exists, if not, add it
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'tenant_id' not in columns:
            cursor.execute('ALTER TABLE conversations ADD COLUMN tenant_id TEXT')
            logger.info("Added 'tenant_id' column to 'conversations' table.")
            # Optional: If you have existing data and want to assign a default tenant_id
            # cursor.execute("UPDATE conversations SET tenant_id = 'default_unassigned_tenant'")
        # ----------------------------------

        conn.commit()
        logger.info("Conversations table checked/created/migrated successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error creating/migrating conversations table: {e}")
    finally:
        conn.close()


def create_last_message_time_table():
    """Creates a table to store the last message timestamp for rate limiting."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS last_message_times (
                wa_id TEXT PRIMARY KEY,
                last_timestamp INTEGER NOT NULL
            )
        ''')
        conn.commit()
        logger.info("Last message times table checked/created successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error creating last_message_times table: {e}")
    finally:
        conn.close()


def create_faqs_table():
    """Creates the faqs table if it doesn't exist, including the embedding column."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS faqs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                embedding TEXT  -- Stores JSON string of the embedding
            )
        ''')
        conn.commit()
        logger.info("FAQs table checked/created successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error creating FAQs table: {e}")
    finally:
        conn.close()


def init_db():
    """Initializes all necessary database tables."""
    logger.info(f"Initializing database: {DATABASE_NAME}")
    create_conversations_table()
    create_last_message_time_table()
    create_faqs_table()
    logger.info("Database initialization complete.")


def add_message(wa_id, message_text, sender, tenant_id, response_text=None):  # ADDED tenant_id
    """Adds a message to the conversation history, associating it with a tenant_id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = int(time.time())
    try:
        cursor.execute(
            "INSERT INTO conversations (wa_id, timestamp, message_text, sender, response_text, tenant_id) VALUES (?, ?, ?, ?, ?, ?)",
            # ADDED tenant_id
            (wa_id, timestamp, message_text, sender, response_text, tenant_id)  # ADDED tenant_id
        )
        conn.commit()
        logger.debug(
            f"Message added for {wa_id} (Tenant: {tenant_id}): '{message_text}' (Sender: {sender}, Response: {response_text or 'N/A'})")
        return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Error adding message to DB for {wa_id} (Tenant: {tenant_id}): {e}", exc_info=True)
        return None
    finally:
        conn.close()


def get_message_history(wa_id, tenant_id, limit=10):  # ADDED tenant_id
    """Retrieves conversation history for a given WhatsApp ID and tenant_id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT message_text, response_text, sender FROM conversations "
            "WHERE wa_id = ? AND tenant_id = ? "  # ADDED tenant_id filter
            "ORDER BY timestamp DESC LIMIT ?",
            (wa_id, tenant_id, limit)  # ADDED tenant_id
        )
        history = cursor.fetchall()
        formatted_history = []
        for row in reversed(history):
            user_message, bot_response, sender = row
            if sender == 'user':
                formatted_history.append({'role': 'user', 'parts': [user_message]})
                if bot_response:
                    formatted_history.append({'role': 'model', 'parts': [bot_response]})
        return formatted_history
    except sqlite3.Error as e:
        logger.error(f"Error retrieving message history for {wa_id} (Tenant: {tenant_id}): {e}", exc_info=True)
        return []
    finally:
        conn.close()


def update_last_message_time(wa_id):
    """Updates the last message timestamp for a given WhatsApp ID.
       Note: Rate limiting is currently not tenant-aware, applies globally per wa_id.
       If you need tenant-specific rate limiting, this table would also need a tenant_id.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = int(time.time())
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO last_message_times (wa_id, last_timestamp) VALUES (?, ?)",
            (wa_id, current_time)
        )
        conn.commit()
        logger.debug(f"Last message time updated for {wa_id} to {current_time}")
    except sqlite3.Error as e:
        logger.error(f"Error updating last message time for {wa_id}: {e}", exc_info=True)
    finally:
        conn.close()


def get_last_message_time(wa_id):
    """Retrieves the last message timestamp for a given WhatsApp ID. Returns 0 if no record.
       Note: Rate limiting is currently not tenant-aware, applies globally per wa_id.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT last_timestamp FROM last_message_times WHERE wa_id = ?", (wa_id,))
        result = cursor.fetchone()
        return result['last_timestamp'] if result else 0
    except sqlite3.Error as e:
        logger.error(f"Error retrieving last message time for {wa_id}: {e}", exc_info=True)
        return 0
    finally:
        conn.close()


# --- FAQ Functions ---
# Note: FAQs are currently shared across all tenants. If you need tenant-specific FAQs,
# the 'faqs' table would also need a 'tenant_id' column, and add_faq/get_all_faqs
# would need to be updated to include/filter by tenant_id.
def add_faq(question, answer, embedding):
    """Adds a new FAQ to the database with its pre-generated embedding."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if embedding is None:
        logger.error(f"Cannot add FAQ '{question}' - embedding is None. Ensure embedding generation was successful.")
        conn.close()
        return None

    try:
        # Store the embedding as a JSON string
        embedding_json = json.dumps(embedding)
        cursor.execute("INSERT INTO faqs (question, answer, embedding) VALUES (?, ?, ?)",
                       (question, answer, embedding_json))
        conn.commit()
        logger.info(f"FAQ added successfully: Q='{question[:50]}...'")
        return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Error adding FAQ to DB: {e}", exc_info=True)
        return None
    finally:
        conn.close()


def get_all_faqs():
    """Retrieves all FAQs from the database, including embeddings (parsed back to lists)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    faqs = []
    try:
        cursor.execute("SELECT id, question, answer, embedding FROM faqs")
        for row in cursor.fetchall():
            faq_item = {"id": row['id'], "question": row['question'], "answer": row['answer']}
            if row['embedding']:  # Check if embedding exists
                try:
                    faq_item["embedding"] = json.loads(row['embedding'])
                except json.JSONDecodeError:
                    logger.error(f"Error decoding embedding JSON for FAQ ID {row['id']}. Setting embedding to None.",
                                 exc_info=True)
                    faq_item["embedding"] = None
            else:
                faq_item["embedding"] = None
            faqs.append(faq_item)
    except sqlite3.Error as e:
        logger.error(f"Error retrieving all FAQs from DB: {e}", exc_info=True)
    finally:
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
            logger.info(f"FAQ with ID {faq_id} deleted successfully.")
            return True
        else:
            logger.warning(f"No FAQ found with ID {faq_id} for deletion.")
            return False
    except sqlite3.Error as e:
        logger.error(f"Error deleting FAQ with ID {faq_id}: {e}", exc_info=True)
        return False
    finally:
        conn.close()


# --- NEW FUNCTION FOR ADMIN DASHBOARD ---
def get_all_wa_ids(tenant_id=None):
    """
    Retrieves all unique WhatsApp IDs (users) for a given tenant_id.
    If tenant_id is None, retrieves all unique IDs across all tenants (for super-admin view).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    wa_ids = []
    try:
        if tenant_id:
            cursor.execute("SELECT DISTINCT wa_id FROM conversations WHERE tenant_id = ?", (tenant_id,))
            logger.debug(f"Fetching distinct wa_ids for tenant: {tenant_id}")
        else:
            cursor.execute("SELECT DISTINCT wa_id FROM conversations")
            logger.debug("Fetching distinct wa_ids for all tenants.")
        wa_ids = [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Error retrieving all wa_ids for tenant {tenant_id or 'all'}: {e}", exc_info=True)
    finally:
        conn.close()
    return wa_ids