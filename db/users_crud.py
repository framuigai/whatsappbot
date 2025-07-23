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

def get_all_users():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, role, tenant_id FROM users ORDER BY id ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Error fetching all users: {e}", exc_info=True)
        return []
    finally:
        conn.close()

# ✅ New: Update user
def update_user(user_id, email=None, password_hash=None, role=None, tenant_id=None):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        fields = []
        params = []

        if email:
            fields.append("email = ?")
            params.append(email)
        if password_hash:
            fields.append("password_hash = ?")
            params.append(password_hash)
        if role:
            fields.append("role = ?")
            params.append(role)
        if tenant_id is not None:
            fields.append("tenant_id = ?")
            params.append(tenant_id)

        if not fields:
            logger.warning("No fields provided for update.")
            return False

        params.append(user_id)
        query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(query, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error updating user: {e}", exc_info=True)
        return False
    finally:
        conn.close()

# ✅ New: Delete user
def delete_user(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error deleting user: {e}", exc_info=True)
        return False
    finally:
        conn.close()
