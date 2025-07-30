# db/faqs_crud.py
import sqlite3
import logging
import json
from db.db_connection import get_db_connection
from config import LOGGING_LEVEL, log_level_map

logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))

def add_faq(question, answer, embedding, client_id):
    if not client_id:
        logger.error("Cannot add FAQ without client_id. Operation aborted.")
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        embedding_json = json.dumps(embedding)
        cursor.execute(
            "INSERT INTO faqs (question, answer, embedding, client_id, active) VALUES (?, ?, ?, ?, 1)",
            (question, answer, embedding_json, client_id)
        )
        conn.commit()
        logger.info(f"FAQ added: Q='{question[:50]}...' for client '{client_id}'")
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        logger.warning(f"FAQ with question '{question[:50]}...' may already exist for client '{client_id}'. Error: {e}")
        return None
    except sqlite3.Error as e:
        logger.error(f"Error adding FAQ: {e}", exc_info=True)
        return None
    finally:
        conn.close()

def get_all_faqs(client_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    faqs = []
    query = "SELECT id, question, answer, embedding, client_id FROM faqs WHERE active = 1"
    params = []
    if client_id:
        query += " AND client_id = ?"
        params.append(client_id)
    try:
        cursor.execute(query, tuple(params))
        for row in cursor.fetchall():
            faq_item = dict(row)
            if faq_item.get('embedding'):
                try:
                    faq_item['embedding'] = json.loads(faq_item['embedding'])
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode embedding for FAQ ID {faq_item['id']}. Data might be corrupted.")
                    faq_item['embedding'] = None
            faqs.append(faq_item)
        logger.debug(f"Retrieved {len(faqs)} FAQs from DB for client '{client_id if client_id else 'all'}'.")
    except sqlite3.Error as e:
        logger.error(f"Error retrieving all FAQs from DB: {e}", exc_info=True)
    finally:
        conn.close()
    return faqs

def get_faq_by_id(faq_id, client_id=None):
    if not faq_id:
        logger.error("FAQ ID is required to fetch FAQ.")
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    faq_item = None
    query = "SELECT id, question, answer, embedding, client_id FROM faqs WHERE id = ? AND active = 1"
    params = [faq_id]
    if client_id:
        query += " AND client_id = ?"
        params.append(client_id)
    try:
        cursor.execute(query, tuple(params))
        row = cursor.fetchone()
        if row:
            faq_item = dict(row)
            if faq_item.get('embedding'):
                try:
                    faq_item['embedding'] = json.loads(faq_item['embedding'])
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode embedding for FAQ ID {faq_item['id']}. Data might be corrupted.")
                    faq_item['embedding'] = None
            logger.debug(f"Retrieved FAQ ID {faq_id} for client '{client_id if client_id else 'N/A'}'.")
    except sqlite3.Error as e:
        logger.error(f"Error retrieving FAQ by ID {faq_id}: {e}", exc_info=True)
    finally:
        conn.close()
    return faq_item

def update_faq(faq_id, question, answer, embedding, client_id):
    if not client_id:
        logger.error("Cannot update FAQ without client_id. Operation aborted.")
        return False
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        embedding_json = json.dumps(embedding)
        cursor.execute(
            "UPDATE faqs SET question = ?, answer = ?, embedding = ? WHERE id = ? AND client_id = ? AND active = 1",
            (question, answer, embedding_json, faq_id, client_id)
        )
        conn.commit()
        if cursor.rowcount > 0:
            logger.info(f"FAQ ID {faq_id} updated successfully for client '{client_id}'.")
            return True
        else:
            logger.warning(f"No FAQ found with ID {faq_id} for client '{client_id}' to update.")
            return False
    except sqlite3.Error as e:
        logger.error(f"Error updating FAQ ID {faq_id}: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def soft_delete_faq_by_id(faq_id, client_id=None):
    if not client_id:
        logger.error("Cannot delete FAQ without client_id. Operation aborted.")
        return False
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "UPDATE faqs SET active = 0 WHERE id = ? AND client_id = ?"
    params = [faq_id, client_id]
    try:
        cursor.execute(query, tuple(params))
        conn.commit()
        if cursor.rowcount > 0:
            logger.info(f"FAQ with ID {faq_id} soft deleted (active set to 0) for client '{client_id}'.")
            return True
        else:
            logger.warning(f"No FAQ found with ID {faq_id} for deletion for client '{client_id}'.")
            return False
    except sqlite3.Error as e:
        logger.error(f"Error soft deleting FAQ: {e}", exc_info=True)
        return False
    finally:
        conn.close()
