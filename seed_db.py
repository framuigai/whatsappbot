# seed_db.py
import os
import sys
import sqlite3
import logging
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir))
sys.path.insert(0, project_root)

from config import LOGGING_LEVEL, log_level_map
from db.db_connection import create_conversations_table, create_faqs_table, create_tenants_table, create_users_table
from db.faqs_crud import add_faq as add_faq_to_db, get_all_faqs
from db.tenants_crud import add_tenant, get_tenant_by_id
from db.users_crud import add_user, get_user_by_email
from ai_utils import generate_embedding

logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))

def create_all_tables():
    """
    ✅ Calls updated create_conversations_table() with correct schema (wa_id).
    """
    create_conversations_table()
    create_faqs_table()
    create_tenants_table()
    create_users_table()
    logger.info("All database tables ensured to exist.")

def seed_initial_data():
    logger.info("Starting DB seeding...")
    create_all_tables()

    tenant_id = "my_initial_client_id"
    tenant_name = "My Primary Test Client"
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID") or "DEFAULT_PHONE_ID"
    wa_token = os.getenv("WHATSAPP_ACCESS_TOKEN") or "DEFAULT_TOKEN"
    ai_instruction = "You are a helpful assistant."

    if not get_tenant_by_id(tenant_id):
        logger.info(f"Adding tenant: {tenant_id}")
        add_tenant(tenant_id, tenant_name, phone_id, wa_token, ai_instruction)
    else:
        logger.info(f"Tenant {tenant_id} already exists. Skipping.")

    admin_email = "admin@example.com"
    admin_password = "adminpassword"
    hashed_password = generate_password_hash(admin_password)

    if not get_user_by_email(admin_email):
        logger.info(f"Adding admin user: {admin_email}")
        add_user(admin_email, hashed_password, "admin", tenant_id)
    else:
        logger.info("Admin user already exists. Skipping.")

    if not get_all_faqs(tenant_id):
        faqs_to_add = [
            ("What is the company's return policy?", "Returns within 30 days."),
            ("How do I contact support?", "Email support@example.com."),
        ]
        for question, answer in faqs_to_add:
            embedding = generate_embedding(question + " " + answer)
            if embedding:
                add_faq_to_db(question, answer, embedding, tenant_id)

    logger.info("Seeding complete.")

if __name__ == "__main__":
    seed_initial_data()
