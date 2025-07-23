# db/users_crud.py
import sqlite3
import logging
from db.db_connection import get_db_connection

logger = logging.getLogger(__name__)

def add_user(email, password_hash, role, tenant_id=None, uid=None):
    """
    Adds a new user to the database.
    Returns True on success, False otherwise (e.g., email already exists).
    """
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (uid, email, password_hash, role, tenant_id) VALUES (?, ?, ?, ?, ?)",
                (uid, email, password_hash, role, tenant_id)
            )
            conn.commit()
            logger.info(f"User '{email}' added successfully with role '{role}' and tenant_id '{tenant_id}'.")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Attempted to add existing user email: {email}")
            return False
        except sqlite3.Error as e:
            logger.error(f"Error adding user '{email}': {e}", exc_info=True)
            return False
        finally:
            conn.close()
    return False


def get_user_by_email(email):
    """
    Retrieves a user from the database by their email.
    Returns a dictionary if found, None otherwise.
    """
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, uid, email, password_hash, role, tenant_id FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            return dict(user) if user else None
        except sqlite3.Error as e:
            logger.error(f"Error fetching user by email '{email}': {e}", exc_info=True)
            return None
        finally:
            conn.close()
    return None


def get_user_by_id(user_id):
    """
    Retrieves a user from the database by their ID.
    """
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, uid, email, password_hash, role, tenant_id FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            return dict(user) if user else None
        except sqlite3.Error as e:
            logger.error(f"Error fetching user by ID '{user_id}': {e}", exc_info=True)
            return None
        finally:
            conn.close()
    return None
