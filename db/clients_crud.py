# db/clients_crud.py
import sqlite3
import logging
from db.db_connection import get_db_connection

logger = logging.getLogger(__name__)

def add_client(client_id, client_name, whatsapp_phone_number_id, whatsapp_api_token,
               ai_system_instruction=None, ai_model_name=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO clients (client_id, client_name, whatsapp_phone_number_id, whatsapp_api_token, ai_system_instruction, ai_model_name, active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (client_id, client_name, whatsapp_phone_number_id, whatsapp_api_token, ai_system_instruction, ai_model_name))
        conn.commit()
        logger.info(f"Client '{client_id}' added successfully.")
        return True
    except sqlite3.IntegrityError as e:
        logger.error(f"IntegrityError adding client {client_id}: {e}", exc_info=True)
        return False
    except sqlite3.Error as e:
        logger.error(f"Database error adding client {client_id}: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def get_all_clients():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE active = 1")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Error fetching clients: {e}", exc_info=True)
        return []
    finally:
        conn.close()

def get_client_by_id(client_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE client_id = ? AND active = 1", (client_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Error fetching client by ID {client_id}: {e}", exc_info=True)
        return None
    finally:
        conn.close()

def update_client(client_id, whatsapp_api_token=None, ai_system_instruction=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        updates = []
        params = []
        if whatsapp_api_token:
            updates.append("whatsapp_api_token = ?")
            params.append(whatsapp_api_token)
        if ai_system_instruction:
            updates.append("ai_system_instruction = ?")
            params.append(ai_system_instruction)
        if not updates:
            return False
        params.append(client_id)
        query = f"UPDATE clients SET {', '.join(updates)} WHERE client_id = ? AND active = 1"
        cursor.execute(query, params)
        conn.commit()
        logger.info(f"Client '{client_id}' updated successfully.")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error updating client {client_id}: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def soft_delete_client(client_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE clients SET active = 0 WHERE client_id = ?", (client_id,))
        conn.commit()
        logger.info(f"Client '{client_id}' soft deleted (active set to 0).")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error soft deleting client {client_id}: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def get_client_config_by_whatsapp_id(whatsapp_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT client_id, client_name, whatsapp_phone_number_id, whatsapp_api_token, ai_system_instruction, ai_model_name
            FROM clients
            WHERE whatsapp_phone_number_id = ? AND active = 1
        """, (whatsapp_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Error fetching client config by WhatsApp ID {whatsapp_id}: {e}", exc_info=True)
        return None
    finally:
        conn.close()
