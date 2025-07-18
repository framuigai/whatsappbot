# db/faqs_crud.py
import sqlite3
import logging
import json
from db.db_connection import get_db_connection
from config import LOGGING_LEVEL, log_level_map

logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))

def add_faq(question, answer, embedding, tenant_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        embedding_json = json.dumps(embedding)
        cursor.execute(
            "INSERT OR REPLACE INTO faqs (question, answer, embedding, tenant_id) VALUES (?, ?, ?, ?)",
            (question, answer, embedding_json, tenant_id)
        )
        conn.commit()
        logger.info(f"FAQ added/updated: Q='{question[:50]}...' for tenant '{tenant_id}'")
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logger.warning(f"FAQ with question '{question[:50]}...' already exists for tenant '{tenant_id}'. Skipping insertion.")
        return None
    except sqlite3.Error as e:
        logger.error(f"Error adding FAQ: {e}", exc_info=True)
        return None
    finally:
        conn.close()

def get_all_faqs(tenant_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    faqs = []
    query = "SELECT id, question, answer, embedding, tenant_id FROM faqs"
    params = []
    if tenant_id:
        query += " WHERE tenant_id = ?"
        params.append(tenant_id)
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
        logger.debug(f"Retrieved {len(faqs)} FAQs from DB for tenant '{tenant_id if tenant_id else 'all'}'.")
    except sqlite3.Error as e:
        logger.error(f"Error retrieving all FAQs from DB: {e}", exc_info=True)
    finally:
        conn.close()
    return faqs

# NEW FUNCTION: Get FAQ by ID
def get_faq_by_id(faq_id, tenant_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    faq_item = None
    query = "SELECT id, question, answer, embedding, tenant_id FROM faqs WHERE id = ?"
    params = [faq_id]
    if tenant_id:
        query += " AND tenant_id = ?"
        params.append(tenant_id)
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
            logger.debug(f"Retrieved FAQ ID {faq_id} for tenant '{tenant_id if tenant_id else 'N/A'}'.")
    except sqlite3.Error as e:
        logger.error(f"Error retrieving FAQ by ID {faq_id}: {e}", exc_info=True)
    finally:
        conn.close()
    return faq_item

# NEW FUNCTION: Update FAQ
def update_faq(faq_id, question, answer, embedding, tenant_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        embedding_json = json.dumps(embedding)
        cursor.execute(
            "UPDATE faqs SET question = ?, answer = ?, embedding = ? WHERE id = ? AND tenant_id = ?",
            (question, answer, embedding_json, faq_id, tenant_id)
        )
        conn.commit()
        if cursor.rowcount > 0:
            logger.info(f"FAQ ID {faq_id} updated successfully for tenant '{tenant_id}'.")
            return True
        else:
            logger.warning(f"No FAQ found with ID {faq_id} for tenant '{tenant_id}' to update.")
            return False
    except sqlite3.Error as e:
        logger.error(f"Error updating FAQ ID {faq_id}: {e}", exc_info=True)
        return False
    finally:
        conn.close()

# RENAMED AND MODIFIED FUNCTION: Delete FAQ by ID
def delete_faq_by_id(faq_id, tenant_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "DELETE FROM faqs WHERE id = ?"
    params = [faq_id]
    if tenant_id:
        query += " AND tenant_id = ?"
        params.append(tenant_id)
    try:
        cursor.execute(query, tuple(params))
        conn.commit()
        if cursor.rowcount > 0:
            logger.info(f"FAQ with ID {faq_id} deleted successfully for tenant '{tenant_id if tenant_id else 'N/A'}'.")
            return True
        else:
            logger.warning(f"No FAQ found with ID {faq_id} for deletion for tenant '{tenant_id if tenant_id else 'N/A'}'.")
            return False
    except sqlite3.Error as e:
        logger.error(f"Error deleting FAQ: {e}", exc_info=True)
        return False
    finally:
        conn.close()