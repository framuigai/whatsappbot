# db/tenants_crud.py
import sqlite3
import logging
# Import get_db_connection from our new db_connection module
from db.db_connection import get_db_connection
from config import LOGGING_LEVEL, log_level_map

logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))

def add_tenant_config(whatsapp_phone_number_id, tenant_id, tenant_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO tenants_config (whatsapp_phone_number_id, tenant_id, tenant_name) VALUES (?, ?, ?)",
            (whatsapp_phone_number_id, tenant_id, tenant_name)
        )
        conn.commit()
        logger.info(f"Tenant configuration added/updated for WhatsApp Phone ID: {whatsapp_phone_number_id}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error adding tenant configuration: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def get_tenant_config_by_whatsapp_id(whatsapp_phone_number_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    tenant_config = None
    try:
        cursor.execute(
            "SELECT whatsapp_phone_number_id, tenant_id, tenant_name FROM tenants_config WHERE whatsapp_phone_number_id = ?",
            (whatsapp_phone_number_id,)
        )
        result = cursor.fetchone()
        if result:
            tenant_config = dict(result)
            logger.debug(f"Found tenant config for WhatsApp Phone ID '{whatsapp_phone_number_id}'.")
        else:
            logger.warning(f"No tenant configuration found for WhatsApp Phone ID '{whatsapp_phone_number_id}'.")
    except sqlite3.Error as e:
        logger.error(f"Error retrieving tenant config by WhatsApp Phone ID: {e}", exc_info=True)
    finally:
        conn.close()
    return tenant_config

def get_tenant_config_by_tenant_id(tenant_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    tenant_config = None
    try:
        cursor.execute(
            "SELECT whatsapp_phone_number_id, tenant_id, tenant_name FROM tenants_config WHERE tenant_id = ?",
            (tenant_id,)
        )
        result = cursor.fetchone()
        if result:
            tenant_config = dict(result)
            logger.debug(f"Found tenant config for tenant_id '{tenant_id}'.")
        else:
            logger.warning(f"No tenant configuration found for tenant_id '{tenant_id}'.")
    except sqlite3.Error as e:
        logger.error(f"Error retrieving tenant config by tenant_id: {e}", exc_info=True)
    finally:
        conn.close()
    return tenant_config

def update_tenant_config(whatsapp_phone_number_id, new_tenant_id, new_tenant_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Use whatsapp_phone_number_id as the primary key for updates
        cursor.execute(
            "UPDATE tenants_config SET tenant_id = ?, tenant_name = ? WHERE whatsapp_phone_number_id = ?",
            (new_tenant_id, new_tenant_name, whatsapp_phone_number_id)
        )
        conn.commit()
        if cursor.rowcount > 0:
            logger.info(f"Tenant configuration updated for WhatsApp Phone ID: {whatsapp_phone_number_id}")
            return True
        else:
            logger.warning(f"No tenant found with WhatsApp Phone ID {whatsapp_phone_number_id} for update.")
            return False
    except sqlite3.Error as e:
        logger.error(f"Error updating tenant configuration: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def delete_tenant_config(whatsapp_phone_number_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM tenants_config WHERE whatsapp_phone_number_id = ?", (whatsapp_phone_number_id,))
        conn.commit()
        if cursor.rowcount > 0:
            logger.info(f"Tenant configuration deleted for WhatsApp Phone ID: {whatsapp_phone_number_id}.")
            return True
        else:
            logger.warning(f"No tenant found with WhatsApp Phone ID {whatsapp_phone_number_id} for deletion.")
            return False
    except sqlite3.Error as e:
        logger.error(f"Error deleting tenant configuration: {e}", exc_info=True)
        return False
    finally:
        conn.close()

def get_all_tenants_config():
    conn = get_db_connection()
    cursor = conn.cursor()
    tenants = []
    try:
        cursor.execute("SELECT whatsapp_phone_number_id, tenant_id, tenant_name FROM tenants_config")
        for row in cursor.fetchall():
            tenants.append(dict(row))
        logger.debug(f"Retrieved {len(tenants)} tenant configurations from DB.")
    except sqlite3.Error as e:
        logger.error(f"Error retrieving all tenant configurations: {e}", exc_info=True)
    finally:
        conn.close()
    return tenants