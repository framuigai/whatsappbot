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

def create_clients_table():
    """Creates the clients table and ensures necessary columns exist."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clients (
                    client_id TEXT PRIMARY KEY,
                    client_name TEXT NOT NULL,
                    whatsapp_phone_number_id TEXT NOT NULL UNIQUE,
                    whatsapp_api_token TEXT NOT NULL,
                    ai_system_instruction TEXT,
                    ai_model_name TEXT,
                    active INTEGER DEFAULT 1
                );
            ''')
            conn.commit()
            logger.info("Checked/Created 'clients' table.")
        except sqlite3.Error as e:
            logger.error(f"Error creating/migrating clients table: {e}", exc_info=True)
        finally:
            conn.close()
    else:
        logger.error("Could not get database connection to create clients table.")

def create_users_table():
    """Creates the users table for Flask-Login with role and password support."""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uid TEXT UNIQUE,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    role TEXT NOT NULL, -- 'super_admin' or 'client'
                    client_id TEXT,
                    active INTEGER DEFAULT 1,
                    FOREIGN KEY (client_id) REFERENCES clients(client_id)
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
    """
    Creates the conversations table.
    """
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wa_id TEXT NOT NULL,
                    client_id TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    response_text TEXT,
                    sender TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    active INTEGER DEFAULT 1,
                    FOREIGN KEY (client_id) REFERENCES clients(client_id)
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
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS faqs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id TEXT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    embedding TEXT,
                    active INTEGER DEFAULT 1,
                    FOREIGN KEY (client_id) REFERENCES clients(client_id)
                );
            ''')
            conn.commit()
            logger.info("Checked/Created 'faqs' table.")
        except sqlite3.Error as e:
            logger.error(f"Error creating faqs table: {e}", exc_info=True)
        finally:
            conn.close()
    else:
        logger.error("Could not get database connection to create faqs table.")

def init_db():
    """Initializes all necessary database tables."""
    create_clients_table()
    create_users_table()
    create_conversations_table()
    create_faqs_table()
