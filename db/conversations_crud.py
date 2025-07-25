# db/conversations_crud.py
import sqlite3
import logging
import time
# Import get_db_connection from our new db_connection module
from db.db_connection import get_db_connection
from config import LOGGING_LEVEL, log_level_map
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))

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

def get_conversation_history_by_whatsapp_id(wa_id, limit=10, tenant_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    conversations = []
    query = "SELECT * FROM conversations WHERE wa_id = ?"
    params = [wa_id]

    if tenant_id:
        query += " AND tenant_id = ?"
        params.append(tenant_id)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    try:
        cursor.execute(query, tuple(params))
        for row in cursor.fetchall():
            conversations.append(dict(row))
        logger.debug(f"Retrieved {len(conversations)} messages for WA ID {wa_id} (Tenant: {tenant_id}).")
    except sqlite3.Error as e:
        logger.error(f"Error getting conversation history for {wa_id}: {e}", exc_info=True)
    finally:
        conn.close()
    return conversations[::-1]


def get_all_conversations(tenant_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    unique_conversations = []
    try:
        query = """
            SELECT
                c.wa_id,
                c.message_text,
                c.response_text,
                c.timestamp,
                c.tenant_id,
                t.tenant_name
            FROM conversations c
            INNER JOIN (
                SELECT wa_id, MAX(timestamp) AS max_timestamp
                FROM conversations
        """
        params = []
        if tenant_id:
            query += " WHERE tenant_id = ?"
            params.append(tenant_id)

        query += """
                GROUP BY wa_id
            ) AS latest_messages
            ON c.wa_id = latest_messages.wa_id AND c.timestamp = latest_messages.max_timestamp
            LEFT JOIN tenants t ON c.tenant_id = t.tenant_id
        """

        # ✅ Apply tenant_id filter again for admin check
        if tenant_id:
            query += " WHERE c.tenant_id = ?"
            params.append(tenant_id)

        query += " ORDER BY c.timestamp DESC"

        cursor.execute(query, tuple(params))
        for row in cursor.fetchall():
            unique_conversations.append({
                "wa_id": row["wa_id"],
                "last_message_text": row["message_text"],
                "ai_response": row["response_text"],
                "last_timestamp": datetime.fromtimestamp(row["timestamp"]),  # ✅ Convert UNIX to datetime
                "tenant_id": row["tenant_id"],
                "tenant_name": row["tenant_name"] or "Unknown"
            })
        logger.debug(f"Retrieved {len(unique_conversations)} unique conversations (Tenant: {tenant_id}).")
    except sqlite3.Error as e:
        logger.error(f"Error getting all conversations: {e}", exc_info=True)
    finally:
        conn.close()
    return unique_conversations



def get_conversation_count(tenant_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    count = 0
    query = "SELECT COUNT(*) FROM conversations"
    params = []
    if tenant_id:
        query += " WHERE tenant_id = ?"
        params.append(tenant_id)
    try:
        cursor.execute(query, tuple(params))
        count = cursor.fetchone()[0]
        logger.debug(f"Total conversations in DB (Tenant: {tenant_id}): {count}")
    except sqlite3.Error as e:
        logger.error(f"Error getting conversation count: {e}", exc_info=True)
    finally:
        conn.close()
    return count

def get_recent_conversations(limit=20, wa_id=None, tenant_id=None):
    """
    Fetches recent conversations from the database.
    Can be filtered by wa_id or tenant_id.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    conversations = []
    query = "SELECT * FROM conversations"
    params = []
    conditions = []

    if wa_id:
        conditions.append("wa_id = ?")
        params.append(wa_id)
    if tenant_id:
        conditions.append("tenant_id = ?")
        params.append(tenant_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    try:
        cursor.execute(query, tuple(params))
        for row in cursor.fetchall():
            conversations.append(dict(row))
        logger.debug(f"Retrieved {len(conversations)} recent conversations (WA ID: {wa_id}, Tenant: {tenant_id}).")
    except sqlite3.Error as e:
        logger.error(f"Error getting recent conversations: {e}", exc_info=True)
    finally:
        conn.close()
    return conversations

def get_monthly_conversation_counts(tenant_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    counts = []
    try:
        query = """
        SELECT
            strftime('%Y-%m', datetime(timestamp, 'unixepoch')) AS month,
            COUNT(*) AS count
        FROM conversations
        WHERE 1=1
        """
        params = []
        if tenant_id:
            query += " AND tenant_id = ?"
            params.append(tenant_id)
        query += " GROUP BY month ORDER BY month"

        cursor.execute(query, tuple(params))
        for row in cursor.fetchall():
            counts.append(dict(row))
        logger.debug(f"Fetched monthly conversation counts (Tenant: {tenant_id}).")
    except sqlite3.Error as e:
        logger.error(f"Error fetching monthly conversation counts: {e}", exc_info=True)
    finally:
        conn.close()
    return counts


def get_daily_conversation_counts(tenant_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    counts = []
    try:
        query = """
        SELECT
            strftime('%Y-%m-%d', datetime(timestamp, 'unixepoch')) AS date,
            COUNT(*) AS count
        FROM conversations
        WHERE 1=1
        """
        params = []
        if tenant_id:
            query += " AND tenant_id = ?"
            params.append(tenant_id)
        query += " GROUP BY date ORDER BY date"

        cursor.execute(query, tuple(params))
        for row in cursor.fetchall():
            counts.append(dict(row))
        logger.debug(f"Fetched daily conversation counts (Tenant: {tenant_id}).")
    except sqlite3.Error as e:
        logger.error(f"Error fetching daily conversation counts: {e}", exc_info=True)
    finally:
        conn.close()
    return counts