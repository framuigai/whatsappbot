import sqlite3
import logging
import time
import json
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_NAME = os.getenv('DATABASE_NAME', 'conversations.db')

def get_db_connection():
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logger.critical(f"Error connecting to database {DATABASE_NAME}: {e}")
        raise

def create_conversations_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wa_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                sender TEXT NOT NULL,
                response_text TEXT,
                tenant_id TEXT -- Ensure this column exists
            )
        ''')
        # Add tenant_id column if it doesn't exist (for existing databases)
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'tenant_id' not in columns:
            cursor.execute('ALTER TABLE conversations ADD COLUMN tenant_id TEXT')
            logger.info("Added 'tenant_id' column to 'conversations' table.")

        conn.commit()
        logger.info("Conversations table checked/created/migrated successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error creating/migrating conversations table: {e}")
    finally:
        conn.close()

def create_last_message_time_table():
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
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS faqs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                embedding TEXT
            )
        ''')
        conn.commit()
        logger.info("FAQs table checked/created successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error creating FAQs table: {e}")
    finally:
        conn.close()

# --- NEW: Tenant Configuration Table ---
def create_tenants_config_table():
    """Creates a table to store WhatsApp Business Phone Number ID to tenant_id mapping."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenants_config (
                whatsapp_phone_number_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL UNIQUE,
                tenant_name TEXT,
                created_at INTEGER NOT NULL
            )
        ''')
        conn.commit()
        logger.info("Tenants config table checked/created successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error creating tenants_config table: {e}")
    finally:
        conn.close()

def add_tenant_config(whatsapp_phone_number_id, tenant_id, tenant_name=None):
    """Adds or updates a tenant configuration."""
    conn = get_db_connection()
    cursor = conn.cursor()
    current_time = int(time.time())
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO tenants_config (whatsapp_phone_number_id, tenant_id, tenant_name, created_at) VALUES (?, ?, ?, ?)",
            (whatsapp_phone_number_id, tenant_id, tenant_name, current_time)
        )
        conn.commit()
        logger.info(f"Tenant config added/updated: WhatsApp Phone ID {whatsapp_phone_number_id} mapped to Tenant ID {tenant_id}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error adding/updating tenant config for WhatsApp Phone ID {whatsapp_phone_number_id}: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def get_tenant_id_from_whatsapp_phone_number(whatsapp_phone_number_id):
    """Retrieves the tenant_id for a given WhatsApp Business Phone Number ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT tenant_id FROM tenants_config WHERE whatsapp_phone_number_id = ?", (whatsapp_phone_number_id,))
        result = cursor.fetchone()
        return result['tenant_id'] if result else None
    except sqlite3.Error as e:
        logger.error(f"Error retrieving tenant_id for WhatsApp Phone ID {whatsapp_phone_number_id}: {e}", exc_info=True)
        return None
    finally:
        conn.close()
# --- END NEW TENANT CONFIGURATION ---


def init_db():
    """Initializes all necessary database tables."""
    logger.info(f"Initializing database: {DATABASE_NAME}")
    create_conversations_table()
    create_last_message_time_table()
    create_faqs_table()
    create_tenants_config_table() # NEW: Initialize the tenant config table
    logger.info("Database initialization complete.")

def add_message(wa_id, message_text, sender, tenant_id, response_text=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = int(time.time())
    try:
        cursor.execute(
            "INSERT INTO conversations (wa_id, timestamp, message_text, sender, response_text, tenant_id) VALUES (?, ?, ?, ?, ?, ?)",
            (wa_id, timestamp, message_text, sender, response_text, tenant_id)
        )
        conn.commit()
        logger.debug(f"Message added for {wa_id} (Tenant: {tenant_id}): '{message_text}' (Sender: {sender}, Response: {response_text or 'N/A'})")
        return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Error adding message to DB for {wa_id} (Tenant: {tenant_id}): {e}", exc_info=True)
        return None
    finally:
        conn.close()

def get_message_history(wa_id, tenant_id, limit=10):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT message_text, response_text, sender FROM conversations "
            "WHERE wa_id = ? AND tenant_id = ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (wa_id, tenant_id, limit)
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

def add_faq(question, answer, embedding):
    conn = get_db_connection()
    cursor = conn.cursor()
    if embedding is None:
        logger.error(f"Cannot add FAQ '{question}' - embedding is None. Ensure embedding generation was successful.")
        conn.close()
        return None
    try:
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
    conn = get_db_connection()
    cursor = conn.cursor()
    faqs = []
    try:
        cursor.execute("SELECT id, question, answer, embedding FROM faqs")
        for row in cursor.fetchall():
            faq_item = {"id": row['id'], "question": row['question'], "answer": row['answer']}
            if row['embedding']:
                try:
                    faq_item["embedding"] = json.loads(row['embedding'])
                except json.JSONDecodeError:
                    logger.error(f"Error decoding embedding JSON for FAQ ID {row['id']}. Setting embedding to None.", exc_info=True)
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

def get_all_wa_ids(tenant_id=None):
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