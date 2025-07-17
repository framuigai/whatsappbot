import sqlite3
import logging
import time
import json
import os
# from dotenv import load_dotenv # REMOVED: Loaded globally in config.py

# load_dotenv() # REMOVED: Loaded globally in config.py

logger = logging.getLogger(__name__) # Use specific logger for this module

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
        logger.info("Conversations table ensured.")
    except sqlite3.Error as e:
        logger.error(f"Error creating conversations table: {e}", exc_info=True)
    finally:
        conn.close()

def create_faqs_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS faqs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL UNIQUE,
                answer TEXT NOT NULL,
                embedding TEXT -- Store as JSON string or BLOB, easier as JSON
            )
        ''')
        # Add embedding column if it doesn't exist (for existing databases)
        cursor.execute("PRAGMA table_info(faqs)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'embedding' not in columns:
            cursor.execute('ALTER TABLE faqs ADD COLUMN embedding TEXT')
            logger.info("Added 'embedding' column to 'faqs' table.")
        conn.commit()
        logger.info("FAQs table ensured.")
    except sqlite3.Error as e:
        logger.error(f"Error creating faqs table: {e}", exc_info=True)
    finally:
        conn.close()

def create_tenants_config_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenants_config (
                whatsapp_phone_number_id TEXT PRIMARY KEY,
                tenant_id TEXT UNIQUE NOT NULL,
                tenant_name TEXT NOT NULL
            )
        ''')
        conn.commit()
        logger.info("Tenants config table ensured.")
    except sqlite3.Error as e:
        logger.error(f"Error creating tenants_config table: {e}", exc_info=True)
    finally:
        conn.close()


def init_db():
    """Initializes all necessary database tables."""
    create_conversations_table()
    create_faqs_table()
    create_tenants_config_table()
    logger.info("All database tables initialized.")

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
        logger.info(f"Message added to DB from {sender} (Tenant: {tenant_id}): '{message_text[:50]}...'")
        return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Error adding message to DB: {e}", exc_info=True)
        return None
    finally:
        conn.close()

def get_conversation_history(wa_id, limit=10, tenant_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    messages = []
    try:
        if tenant_id:
            cursor.execute(
                "SELECT message_text, sender, timestamp FROM conversations WHERE wa_id = ? AND tenant_id = ? ORDER BY timestamp DESC LIMIT ?",
                (wa_id, tenant_id, limit)
            )
            logger.debug(f"Fetching conversation history for {wa_id} (Tenant: {tenant_id})")
        else:
            cursor.execute(
                "SELECT message_text, sender, timestamp FROM conversations WHERE wa_id = ? ORDER BY timestamp DESC LIMIT ?",
                (wa_id, limit)
            )
            logger.debug(f"Fetching conversation history for {wa_id}")
        for row in cursor.fetchall():
            messages.append(dict(row))
        return messages[::-1] # Return in chronological order
    except sqlite3.Error as e:
        logger.error(f"Error retrieving conversation history: {e}", exc_info=True)
        return []
    finally:
        conn.close()

def add_faq(question, answer, embedding):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Store embedding as a JSON string
        embedding_json = json.dumps(embedding)
        cursor.execute(
            "INSERT OR REPLACE INTO faqs (question, answer, embedding) VALUES (?, ?, ?)",
            (question, answer, embedding_json)
        )
        conn.commit()
        logger.info(f"FAQ added/updated: Q='{question[:50]}...'")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logger.warning(f"FAQ with question '{question[:50]}...' already exists. Skipping insertion.")
        return None
    except sqlite3.Error as e:
        logger.error(f"Error adding FAQ: {e}", exc_info=True)
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
            faq_item = dict(row)
            if faq_item.get('embedding'):
                try:
                    faq_item['embedding'] = json.loads(faq_item['embedding']) # Convert back from JSON string
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode embedding for FAQ ID {faq_item['id']}. Data might be corrupted.")
                    faq_item['embedding'] = None # Set to None if decoding fails
            faqs.append(faq_item)
        logger.debug(f"Retrieved {len(faqs)} FAQs from DB.")
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
            logger.debug("Fetching distinct wa_ids for all tenants")
        for row in cursor.fetchall():
            wa_ids.append(row['wa_id'])
    except sqlite3.Error as e:
        logger.error(f"Error fetching distinct WA IDs: {e}", exc_info=True)
    finally:
        conn.close()
    return wa_ids

def add_tenant_config(whatsapp_phone_number_id, tenant_id, tenant_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO tenants_config (whatsapp_phone_number_id, tenant_id, tenant_name) VALUES (?, ?, ?)",
            (whatsapp_phone_number_id, tenant_id, tenant_name)
        )
        conn.commit()
        logger.info(f"Tenant configuration added/updated for WhatsApp Phone ID: {whatsapp_phone_number_id}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error adding tenant configuration: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def get_tenant_id_from_whatsapp_phone_number(whatsapp_phone_number_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    tenant_id = None
    try:
        cursor.execute(
            "SELECT tenant_id FROM tenants_config WHERE whatsapp_phone_number_id = ?",
            (whatsapp_phone_number_id,)
        )
        result = cursor.fetchone()
        if result:
            tenant_id = result['tenant_id']
            logger.debug(f"Found tenant_id '{tenant_id}' for WhatsApp Phone ID '{whatsapp_phone_number_id}'.")
        else:
            logger.warning(f"No tenant configuration found for WhatsApp Phone ID '{whatsapp_phone_number_id}'.")
    except sqlite3.Error as e:
        logger.error(f"Error retrieving tenant_id: {e}", exc_info=True)
    finally:
        conn.close()
    return tenant_id

def get_whatsapp_phone_number_from_tenant_id(tenant_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    whatsapp_phone_number_id = None
    try:
        cursor.execute(
            "SELECT whatsapp_phone_number_id FROM tenants_config WHERE tenant_id = ?",
            (tenant_id,)
        )
        result = cursor.fetchone()
        if result:
            whatsapp_phone_number_id = result['whatsapp_phone_number_id']
            logger.debug(f"Found WhatsApp Phone ID '{whatsapp_phone_number_id}' for tenant_id '{tenant_id}'.")
        else:
            logger.warning(f"No WhatsApp Phone ID found for tenant_id '{tenant_id}'.")
    except sqlite3.Error as e:
        logger.error(f"Error retrieving WhatsApp Phone ID from tenant_id: {e}", exc_info=True)
    finally:
        conn.close()
    return whatsapp_phone_number_id


def get_all_tenants_config():
    conn = get_db_connection()
    cursor = conn.cursor()
    tenants = []
    try:
        cursor.execute("SELECT whatsapp_phone_number_id, tenant_id, tenant_name FROM tenants_config")
        for row in cursor.fetchall():
            tenants.append(dict(row))
        logger.debug(f"Retrieved {len(tenants)} tenant configurations from DB.")
    except sqlite3.Error as e:
        logger.error(f"Error retrieving all tenant configurations: {e}", exc_info=True)
    finally:
        conn.close()
    return tenants

def get_conversation_count():
    conn = get_db_connection()
    cursor = conn.cursor()
    count = 0
    try:
        cursor.execute("SELECT COUNT(*) FROM conversations")
        count = cursor.fetchone()[0]
        logger.debug(f"Total conversations in DB: {count}")
    except sqlite3.Error as e:
        logger.error(f"Error getting conversation count: {e}", exc_info=True)
    finally:
        conn.close()
    return count