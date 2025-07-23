# db/db_connection.py
import sqlite3
import logging
import os
from config import DATABASE_NAME, LOGGING_LEVEL, log_level_map

logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))


def get_db_connection():
    """Establishes and returns a database connection."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row  # This allows access to columns by name
        # Enable foreign key support in SQLite
        conn.execute("PRAGMA foreign_keys = ON;")
        logger.debug(f"Successfully connected to database: {DATABASE_NAME}")
    except sqlite3.Error as e:
        logger.critical(f"Error connecting to database {DATABASE_NAME}: {e}")
        raise  # Re-raise the exception for the calling code to handle
    return conn


def create_tenants_table():  # RENAMED from create_tenants_config_table
    """Creates the tenants table and ensures necessary columns exist."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tenants (
                    tenant_id TEXT PRIMARY KEY,
                    tenant_name TEXT NOT NULL,
                    whatsapp_phone_number_id TEXT UNIQUE NOT NULL, -- Ensure this is unique
                    whatsapp_api_token TEXT NOT NULL,
                    ai_system_instruction TEXT,
                    ai_model_name TEXT
                );
            ''')
            conn.commit()
            logger.info("Checked/Created 'tenants' table.")
        except sqlite3.Error as e:
            logger.error(f"Error creating/migrating tenants table: {e}", exc_info=True)
        finally:
            conn.close()
    else:
        logger.error("Could not get database connection to create tenants table.")


def create_users_table():
    """Creates the users table for Flask-Login with role and password support."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Updated schema to include id (PK), password_hash, and role
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uid TEXT UNIQUE, -- Firebase User ID (optional)
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT, -- For local authentication
                    role TEXT NOT NULL, -- admin or client
                    tenant_id TEXT, -- The ID of the tenant this user belongs to
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
                );
            ''')
            conn.commit()
            logger.info("Checked/Created 'users' table with role and password support.")
        except sqlite3.Error as e:
            logger.error(f"Error creating users table: {e}", exc_info=True)
        finally:
            conn.close()
    else:
        logger.error("Could not get database connection to create users table.")


def create_conversations_table():
    """Creates the conversations table."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    whatsapp_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,  -- ADDED: Foreign Key to tenants table
                    message_text TEXT NOT NULL,
                    response_text TEXT,
                    from_user BOOLEAN NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) -- ADDED: Foreign Key
                );
            ''')
            conn.commit()
            logger.info("Checked/Created 'conversations' table.")
        except sqlite3.Error as e:
            logger.error(f"Error creating conversations table: {e}", exc_info=True)
        finally:
            conn.close()
    else:
        logger.error("Could not get database connection to create conversations table.")


def create_faqs_table():
    """Creates the FAQs table and ensures necessary columns exist."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # The 'faqs' table should already be created, but we ensure it here.
            # Also, ensure 'tenant_id' and 'embedding' columns exist.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS faqs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT, -- ADDED: Foreign Key
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    embedding TEXT, -- Store embedding as JSON string
                    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) -- ADDED: Foreign Key
                );
            ''')
            logger.info("Checked/Created 'faqs' table.")

            # --- Schema Migrations for existing 'faqs' table ---
            cursor.execute("PRAGMA table_info(faqs)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'embedding' not in columns:
                cursor.execute('ALTER TABLE faqs ADD COLUMN embedding TEXT')
                logger.info("Added 'embedding' column to 'faqs' table.")
            if 'tenant_id' not in columns:
                cursor.execute('ALTER TABLE faqs ADD COLUMN tenant_id TEXT')
                logger.info("Added 'tenant_id' column to 'faqs' table.")

            conn.commit()
            logger.info("FAQs table ensured and migrated if necessary.")
        except sqlite3.Error as e:
            logger.error(f"Error creating/migrating faqs table: {e}", exc_info=True)
        finally:
            conn.close()
    else:
        logger.error("Could not get database connection to create faqs table.")


def init_db():
    """Initializes all necessary database tables."""
    create_tenants_table()  # MODIFIED: Call renamed function first as users/conversations/faqs depend on it
    create_users_table()  # ADDED: Call new users table creation
    create_conversations_table()
    create_faqs_table()
