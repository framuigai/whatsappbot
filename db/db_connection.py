# db/db_connection.py
import sqlite3
import logging
import os
from config import DATABASE_NAME, LOGGING_LEVEL, log_level_map

logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))

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
                tenant_id TEXT
            )
        ''')
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
                embedding TEXT,
                tenant_id TEXT -- Added tenant_id directly here for initial creation
            )
        ''')
        cursor.execute("PRAGMA table_info(faqs)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'embedding' not in columns:
            cursor.execute('ALTER TABLE faqs ADD COLUMN embedding TEXT')
            logger.info("Added 'embedding' column to 'faqs' table.")
        if 'tenant_id' not in columns: # Still keep this for backward compatibility with old DBs
            cursor.execute('ALTER TABLE faqs ADD COLUMN tenant_id TEXT')
            logger.info("Added 'tenant_id' column to 'faqs' table.")

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