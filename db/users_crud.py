# db/users_crud.py
import sqlite3
import logging
import uuid
from werkzeug.security import generate_password_hash
from db.db_connection import get_db_connection

logger = logging.getLogger(__name__)

def add_user(email, password=None, role="client", client_id=None, uid=None):
    """
    Add a new user to the database.
    Password is always hashed before saving.
    UID is always required; for local users, a UUID will be generated if not given.
    Only 'super_admin' and 'client' are allowed as roles.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        password_hash = generate_password_hash(password) if password else None

        if not uid:
            uid = str(uuid.uuid4())

        # Only allow super_admin and client roles
        if role not in ("super_admin", "client"):
            logger.error(f"Invalid user role: {role}")
            return False

        cursor.execute("""
            INSERT INTO users (uid, email, password_hash, role, client_id, active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (uid, email, password_hash, role, client_id))
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

def get_user_by_email(email):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ? AND active = 1", (email,))
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
        cursor.execute("SELECT * FROM users WHERE uid = ? AND active = 1", (uid,))
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
        cursor.execute("SELECT * FROM users WHERE id = ? AND active = 1", (user_id,))
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
        # Fetch active so the template can check it
        cursor.execute("SELECT id, uid, email, role, client_id, active FROM users WHERE active = 1 ORDER BY id ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Error fetching all users: {e}", exc_info=True)
        return []
    finally:
        conn.close()


def get_users_by_role(role):
    if role not in ("super_admin", "client"):
        logger.error(f"Invalid user role for query: {role}")
        return []
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, uid, email, role, client_id FROM users WHERE role = ? AND active = 1", (role,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Error fetching users by role: {e}", exc_info=True)
        return []
    finally:
        conn.close()

def get_users_by_client(client_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, uid, email, role, client_id FROM users WHERE client_id = ? AND active = 1", (client_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Error fetching users by client: {e}", exc_info=True)
        return []
    finally:
        conn.close()

def update_user(user_id, email=None, password=None, role=None, client_id=None, uid=None):
    """
    Update user details. Password will be hashed before saving.
    Only 'super_admin' and 'client' are allowed as roles.
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
            if role not in ("super_admin", "client"):
                logger.error(f"Invalid user role for update: {role}")
                return False
            fields.append("role = ?")
            params.append(role)
        if client_id is not None:
            fields.append("client_id = ?")
            params.append(client_id)
        if uid:
            fields.append("uid = ?")
            params.append(uid)

        if not fields:
            logger.warning("No fields provided for update.")
            return False

        params.append(user_id)
        query = f"UPDATE users SET {', '.join(fields)} WHERE id = ? AND active = 1"
        cursor.execute(query, tuple(params))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error updating user: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def soft_delete_user(user_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET active = 0 WHERE id = ?", (user_id,))
        conn.commit()
        logger.info(f"User with ID {user_id} soft deleted (active set to 0).")
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error soft deleting user: {e}", exc_info=True)
        return False
    finally:
        conn.close()
