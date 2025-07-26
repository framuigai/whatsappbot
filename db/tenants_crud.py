# db/tenants_crud.py
import sqlite3
import logging
from db.db_connection import get_db_connection

logger = logging.getLogger(__name__)

def add_tenant(tenant_id, tenant_name, whatsapp_phone_number_id, whatsapp_api_token,
               ai_system_instruction=None, ai_model_name=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO tenants (tenant_id, tenant_name, whatsapp_phone_number_id, whatsapp_api_token, ai_system_instruction, ai_model_name)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (tenant_id, tenant_name, whatsapp_phone_number_id, whatsapp_api_token, ai_system_instruction, ai_model_name))
        conn.commit()
        logger.info(f"Tenant '{tenant_id}' added successfully.")
        return True
    except sqlite3.IntegrityError as e:
        logger.error(f"IntegrityError adding tenant {tenant_id}: {e}", exc_info=True)
        return False
    except sqlite3.Error as e:
        logger.error(f"Database error adding tenant {tenant_id}: {e}", exc_info=True)
        return False
    finally:
        conn.close()


def get_all_tenants():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tenants")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Error fetching tenants: {e}", exc_info=True)
        return []
    finally:
        conn.close()


def get_tenant_by_id(tenant_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tenants WHERE tenant_id = ?", (tenant_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Error fetching tenant by ID {tenant_id}: {e}", exc_info=True)
        return None
    finally:
        conn.close()


def update_tenant(tenant_id, whatsapp_api_token=None, ai_system_instruction=None):
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

        params.append(tenant_id)
        query = f"UPDATE tenants SET {', '.join(updates)} WHERE tenant_id = ?"
        cursor.execute(query, params)
        conn.commit()
        logger.info(f"Tenant '{tenant_id}' updated successfully.")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error updating tenant {tenant_id}: {e}", exc_info=True)
        return False
    finally:
        conn.close()


def delete_tenant(tenant_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tenants WHERE tenant_id = ?", (tenant_id,))
        conn.commit()
        logger.info(f"Tenant '{tenant_id}' deleted successfully.")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error deleting tenant {tenant_id}: {e}", exc_info=True)
        return False
    finally:
        conn.close()


def get_tenant_config_by_whatsapp_id(whatsapp_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT tenant_id, tenant_name, whatsapp_phone_number_id, whatsapp_api_token, ai_system_instruction, ai_model_name
            FROM tenants
            WHERE whatsapp_phone_number_id = ?
        """, (whatsapp_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Error fetching tenant config by WhatsApp ID {whatsapp_id}: {e}", exc_info=True)
        return None
    finally:
        conn.close()
