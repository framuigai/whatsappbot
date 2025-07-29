# db/users_crud.py
import sqlite3
import logging
import uuid  # <-- NEW: for generating unique uids
from werkzeug.security import generate_password_hash
from db.db_connection import get_db_connection

logger = logging.getLogger(__name__)

def add_user(email, password=None, role="client", tenant_id=None, uid=None):
    """
    Add a new user to the database.
    Password is always hashed before saving.
    UID is always required; for local users, a UUID will be generated if not given.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        password_hash = generate_password_hash(password) if password else None

        # PATCH: Always assign a unique uid if not provided
        if not uid:
            # Use email as uid if you prefer, but uuid4() is safer/unique
            uid = str(uuid.uuid4())

        cursor.execute("""
            INSERT INTO users (uid, email, password_hash, role, tenant_id)
            VALUES (?, ?, ?, ?, ?)
        """, (uid, email, password_hash, role, tenant_id))
        conn.commit()
        logger.info(f"User '{email}' added successfully with uid='{uid}'.")
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"User email already exists: {email}")
        return False
    except sqlite3.Error as e:
        logger.error(f"Error adding user: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def migrate_users_set_uid_for_nulls():
    """
    Find users with uid IS NULL or empty and assign them a unique uid.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email FROM users WHERE uid IS NULL OR uid = ''")
        users = cursor.fetchall()
        count = 0
        for user in users:
            new_uid = str(uuid.uuid4())
            cursor.execute("UPDATE users SET uid=? WHERE id=?", (new_uid, user["id"]))
            logger.info(f"User with id={user['id']} ({user['email']}) assigned new uid={new_uid}")
            count += 1
        if count > 0:
            conn.commit()
            logger.info(f"Migration complete: {count} user(s) updated with unique uid.")
        else:
            logger.info("No users found needing uid migration.")
    except sqlite3.Error as e:
        logger.error(f"Error migrating user uids: {e}", exc_info=True)
    finally:
        conn.close()

# ... rest of your file unchanged ...
def get_user_by_email(email):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None
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
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Error fetching user by UID: {e}", exc_info=True)
        return None
    finally:
        conn.close()

def get_user_by_id(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Error fetching user by ID: {e}", exc_info=True)
        return None
    finally:
        conn.close()

def get_all_users():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, uid, email, role, tenant_id FROM users ORDER BY id ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Error fetching all users: {e}", exc_info=True)
        return []
    finally:
        conn.close()

def get_users_by_role(role):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, uid, email, role, tenant_id FROM users WHERE role = ?", (role,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Error fetching users by role: {e}", exc_info=True)
        return []
    finally:
        conn.close()

def get_users_by_tenant(tenant_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, uid, email, role, tenant_id FROM users WHERE tenant_id = ?", (tenant_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Error fetching users by tenant: {e}", exc_info=True)
        return []
    finally:
        conn.close()

def update_user(user_id, email=None, password=None, role=None, tenant_id=None, uid=None):
    """
    Update user details. Password will be hashed before saving.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        fields = []
        params = []

        if email:
            fields.append("email = ?")
            params.append(email)
        if password:
            fields.append("password_hash = ?")
            params.append(generate_password_hash(password))
        if role:
            fields.append("role = ?")
            params.append(role)
        if tenant_id is not None:
            fields.append("tenant_id = ?")
            params.append(tenant_id)
        if uid:
            fields.append("uid = ?")
            params.append(uid)

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
