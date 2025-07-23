# db/tenants_crud.py
import sqlite3
import logging
from db.db_connection import get_db_connection
from config import LOGGING_LEVEL, log_level_map

logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))


def add_tenant(tenant_id, tenant_name, whatsapp_phone_number_id, whatsapp_api_token, ai_system_instruction=None, ai_model_name=None):
    """
    Adds or updates a tenant record in the tenants table.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO tenants
            (tenant_id, tenant_name, whatsapp_phone_number_id, whatsapp_api_token, ai_system_instruction, ai_model_name)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (tenant_id, tenant_name, whatsapp_phone_number_id, whatsapp_api_token, ai_system_instruction, ai_model_name))
        conn.commit()
        logger.info(f"Tenant added/updated: ID={tenant_id}, Name={tenant_name}, PhoneID={whatsapp_phone_number_id}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error adding tenant: {e}", exc_info=True)
        return False
    finally:
        conn.close()


def get_tenant_by_phone_id(whatsapp_phone_number_id):
    """
    Retrieves a tenant by its WhatsApp phone number ID.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    tenant = None
    try:
        cursor.execute('SELECT * FROM tenants WHERE whatsapp_phone_number_id = ?', (whatsapp_phone_number_id,))
        result = cursor.fetchone()
        if result:
            tenant = dict(result)
            logger.debug(f"Found tenant for WhatsApp Phone ID '{whatsapp_phone_number_id}'.")
        else:
            logger.warning(f"No tenant found for WhatsApp Phone ID '{whatsapp_phone_number_id}'.")
    except sqlite3.Error as e:
        logger.error(f"Error retrieving tenant by WhatsApp Phone ID: {e}", exc_info=True)
    finally:
        conn.close()
    return tenant


def get_tenant_by_id(tenant_id):
    """
    Retrieves tenant configuration by tenant_id.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    tenant = None
    try:
        cursor.execute('SELECT * FROM tenants WHERE tenant_id = ?', (tenant_id,))
        result = cursor.fetchone()
        if result:
            tenant = dict(result)
            logger.debug(f"Found tenant for tenant_id '{tenant_id}'.")
        else:
            logger.warning(f"No tenant found for tenant_id '{tenant_id}'.")
    except sqlite3.Error as e:
        logger.error(f"Error retrieving tenant by tenant_id: {e}", exc_info=True)
    finally:
        conn.close()
    return tenant


def update_tenant(tenant_id, tenant_name=None, whatsapp_api_token=None, ai_system_instruction=None, ai_model_name=None):
    """
    Updates tenant details by tenant_id.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        fields = []
        params = []

        if tenant_name:
            fields.append("tenant_name = ?")
            params.append(tenant_name)
        if whatsapp_api_token:
            fields.append("whatsapp_api_token = ?")
            params.append(whatsapp_api_token)
        if ai_system_instruction:
            fields.append("ai_system_instruction = ?")
            params.append(ai_system_instruction)
        if ai_model_name:
            fields.append("ai_model_name = ?")
            params.append(ai_model_name)

        if not fields:
            logger.warning("No fields provided for tenant update.")
            return False

        params.append(tenant_id)
        query = f"UPDATE tenants SET {', '.join(fields)} WHERE tenant_id = ?"
        cursor.execute(query, tuple(params))
        conn.commit()

        if cursor.rowcount > 0:
            logger.info(f"Tenant '{tenant_id}' updated successfully.")
            return True
        else:
            logger.warning(f"No tenant found with tenant_id '{tenant_id}' to update.")
            return False
    except sqlite3.Error as e:
        logger.error(f"Error updating tenant: {e}", exc_info=True)
        return False
    finally:
        conn.close()


def delete_tenant(tenant_id):
    """
    Deletes a tenant by tenant_id.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM tenants WHERE tenant_id = ?", (tenant_id,))
        conn.commit()
        if cursor.rowcount > 0:
            logger.info(f"Tenant '{tenant_id}' deleted successfully.")
            return True
        else:
            logger.warning(f"No tenant found with tenant_id '{tenant_id}' to delete.")
            return False
    except sqlite3.Error as e:
        logger.error(f"Error deleting tenant: {e}", exc_info=True)
        return False
    finally:
        conn.close()


def get_all_tenants():
    """
    Retrieves all tenants.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    tenants = []
    try:
        cursor.execute("SELECT * FROM tenants")
        for row in cursor.fetchall():
            tenants.append(dict(row))
        logger.debug(f"Retrieved {len(tenants)} tenants from DB.")
    except sqlite3.Error as e:
        logger.error(f"Error retrieving tenants: {e}", exc_info=True)
    finally:
        conn.close()
    return tenants
