# db/conversations_crud.py
import sqlite3
import logging
import time
from db.db_connection import get_db_connection
from config import LOGGING_LEVEL, log_level_map
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))

def add_message(wa_id, message_text, sender, client_id, response_text=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = int(time.time())
    try:
        cursor.execute(
            "INSERT INTO conversations (wa_id, timestamp, message_text, sender, response_text, client_id, active) VALUES (?, ?, ?, ?, ?, ?, 1)",
            (wa_id, timestamp, message_text, sender, response_text, client_id)
        )
        conn.commit()
        logger.info(f"Message added to DB from {sender} (Client: {client_id}): '{message_text[:50]}...'")
        return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"Error adding message to DB: {e}", exc_info=True)
        return None
    finally:
        conn.close()

def get_conversation_history_by_whatsapp_id(wa_id, limit=10, client_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    conversations = []
    query = "SELECT * FROM conversations WHERE wa_id = ? AND active = 1"
    params = [wa_id]

    if client_id:
        query += " AND client_id = ?"
        params.append(client_id)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    try:
        cursor.execute(query, tuple(params))
        for row in cursor.fetchall():
            conversations.append(dict(row))
        logger.debug(f"Retrieved {len(conversations)} messages for WA ID {wa_id} (Client: {client_id}).")
    except sqlite3.Error as e:
        logger.error(f"Error getting conversation history for {wa_id}: {e}", exc_info=True)
    finally:
        conn.close()
    return conversations[::-1]

def get_all_conversations(client_id=None, wa_id=None, limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    conversations = []

    sub_conditions = ["active = 1"]
    params = []
    if client_id:
        sub_conditions.append("client_id = ?")
        params.append(client_id)
    if wa_id:
        sub_conditions.append("wa_id = ?")
        params.append(wa_id)

    sub_query = " AND ".join(sub_conditions)
    if sub_query:
        sub_query = "WHERE " + sub_query

    query = f"""
    SELECT c.*, cl.client_name
    FROM conversations c
    LEFT JOIN clients cl ON c.client_id = cl.client_id
    INNER JOIN (
        SELECT wa_id, MAX(timestamp) as last_timestamp
        FROM conversations
        {sub_query}
        GROUP BY wa_id
    ) sub
    ON c.wa_id = sub.wa_id AND c.timestamp = sub.last_timestamp
    """
    # Additional main query filtering for c.client_id, c.wa_id
    main_conditions = ["c.active = 1"]
    if client_id:
        main_conditions.append("c.client_id = ?")
        params.append(client_id)
    if wa_id:
        main_conditions.append("c.wa_id = ?")
        params.append(wa_id)
    if main_conditions:
        query += " WHERE " + " AND ".join(main_conditions)
    query += " ORDER BY c.timestamp DESC LIMIT ?"
    params.append(limit)

    try:
        cursor.execute(query, tuple(params))
        for row in cursor.fetchall():
            conversations.append(dict(row))
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}", exc_info=True)
    finally:
        conn.close()
    return conversations

def get_conversation_count(client_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    count = 0
    query = "SELECT COUNT(*) FROM conversations WHERE active = 1"
    params = []
    if client_id:
        query += " AND client_id = ?"
        params.append(client_id)
    try:
        cursor.execute(query, tuple(params))
        count = cursor.fetchone()[0]
        logger.debug(f"Total conversations in DB (Client: {client_id}): {count}")
    except sqlite3.Error as e:
        logger.error(f"Error getting conversation count: {e}", exc_info=True)
    finally:
        conn.close()
    return count

def get_recent_conversations(limit=20, wa_id=None, client_id=None):
    """
    Fetches recent conversations from the database.
    Can be filtered by wa_id or client_id.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    conversations = []
    query = "SELECT * FROM conversations WHERE active = 1"
    params = []
    conditions = []

    if wa_id:
        conditions.append("wa_id = ?")
        params.append(wa_id)
    if client_id:
        conditions.append("client_id = ?")
        params.append(client_id)

    if conditions:
        query += " AND " + " AND ".join(conditions)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    try:
        cursor.execute(query, tuple(params))
        for row in cursor.fetchall():
            conversations.append(dict(row))
        logger.debug(f"Retrieved {len(conversations)} recent conversations (WA ID: {wa_id}, Client: {client_id}).")
    except sqlite3.Error as e:
        logger.error(f"Error getting recent conversations: {e}", exc_info=True)
    finally:
        conn.close()
    return conversations

def get_monthly_conversation_counts(client_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    counts = []
    try:
        query = """
        SELECT
            strftime('%Y-%m', datetime(timestamp, 'unixepoch')) AS month,
            COUNT(*) AS count
        FROM conversations
        WHERE active = 1
        """
        params = []
        if client_id:
            query += " AND client_id = ?"
            params.append(client_id)
        query += " GROUP BY month ORDER BY month"

        cursor.execute(query, tuple(params))
        for row in cursor.fetchall():
            counts.append(dict(row))
        logger.debug(f"Fetched monthly conversation counts (Client: {client_id}).")
    except sqlite3.Error as e:
        logger.error(f"Error fetching monthly conversation counts: {e}", exc_info=True)
    finally:
        conn.close()
    return counts

def get_daily_conversation_counts(client_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    counts = []
    try:
        query = """
        SELECT
            strftime('%Y-%m-%d', datetime(timestamp, 'unixepoch')) AS date,
            COUNT(*) AS count
        FROM conversations
        WHERE active = 1
        """
        params = []
        if client_id:
            query += " AND client_id = ?"
            params.append(client_id)
        query += " GROUP BY date ORDER BY date"

        cursor.execute(query, tuple(params))
        for row in cursor.fetchall():
            counts.append(dict(row))
        logger.debug(f"Fetched daily conversation counts (Client: {client_id}).")
    except sqlite3.Error as e:
        logger.error(f"Error fetching daily conversation counts: {e}", exc_info=True)
    finally:
        conn.close()
    return counts

def soft_delete_conversation(conversation_id):
    """
    Soft deletes a conversation (sets active to 0).
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE conversations SET active = 0 WHERE id = ?", (conversation_id,))
        conn.commit()
        logger.info(f"Conversation with ID {conversation_id} soft deleted (active set to 0).")
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error(f"Error soft deleting conversation: {e}", exc_info=True)
        return False
    finally:
        conn.close()
