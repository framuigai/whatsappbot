# db/users_crud.py
import sqlite3
import logging
from db.db_connection import get_db_connection

logger = logging.getLogger(__name__)

def add_user(email, password_hash, role, tenant_id=None, uid=None):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (uid, email, password_hash, role, tenant_id) VALUES (?, ?, ?, ?, ?)",
            (uid, email, password_hash, role, tenant_id)
        )
        conn.commit()
        logger.info(f"User '{email}' added successfully.")
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"User email already exists: {email}")
        return False
    except sqlite3.Error as e:
        logger.error(f"Error adding user: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def get_user_by_email(email):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        return dict(user) if user else None
    except sqlite3.Error as e:
        logger.error(f"Error fetching user by email: {e}", exc_info=True)
        return None
    finally:
        conn.close()

def get_user_by_id(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        return dict(user) if user else None
    except sqlite3.Error as e:
        logger.error(f"Error fetching user by ID: {e}", exc_info=True)
        return None
    finally:
        conn.close()

# ✅ New function for Flask-Login
def get_user_by_uid(uid):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE uid = ?", (uid,))
        user = cursor.fetchone()
        return dict(user) if user else None
    except sqlite3.Error as e:
        logger.error(f"Error fetching user by UID: {e}", exc_info=True)
        return None
    finally:
        conn.close()
