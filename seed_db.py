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

# Add project root for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir))
sys.path.insert(0, project_root)

from config import LOGGING_LEVEL, log_level_map
from db.db_connection import (
    create_conversations_table,
    create_faqs_table,
    create_tenants_table,
    create_users_table
)
from db.faqs_crud import add_faq as add_faq_to_db, get_all_faqs
from db.tenants_crud import add_tenant, get_tenant_by_id
from db.users_crud import add_user, get_user_by_email
from ai_utils import generate_embedding

logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))


def create_all_tables():
    """
    ✅ Ensure all tables exist before seeding data.
    """
    create_conversations_table()
    create_faqs_table()
    create_tenants_table()
    create_users_table()
    logger.info("All database tables ensured to exist.")


def seed_initial_data():
    logger.info("Starting DB seeding...")
    create_all_tables()

    # ✅ Create tenants
    tenants = [
        {
            "tenant_id": "tenant_one",
            "tenant_name": "Tenant One Company",
            "phone_id": os.getenv("WHATSAPP_PHONE_NUMBER_ID") or "PHONE_ID_1",
            "wa_token": os.getenv("WHATSAPP_ACCESS_TOKEN") or "TOKEN_1",
            "ai_instruction": "You are a helpful assistant for Tenant One."
        },
        {
            "tenant_id": "tenant_two",
            "tenant_name": "Tenant Two Company",
            "phone_id": "PHONE_ID_2",
            "wa_token": "TOKEN_2",
            "ai_instruction": "You are a helpful assistant for Tenant Two."
        }
    ]

    for tenant in tenants:
        if not get_tenant_by_id(tenant["tenant_id"]):
            logger.info(f"Adding tenant: {tenant['tenant_id']}")
            add_tenant(
                tenant["tenant_id"],
                tenant["tenant_name"],
                tenant["phone_id"],
                tenant["wa_token"],
                tenant["ai_instruction"]
            )
        else:
            logger.info(f"Tenant {tenant['tenant_id']} already exists. Skipping.")

    # ✅ Create Global Admin (no tenant_id)
    admin_email = "admin@example.com"
    admin_password = "adminpassword"
    hashed_password = generate_password_hash(admin_password)

    if not get_user_by_email(admin_email):
        logger.info(f"Adding global admin user: {admin_email}")
        add_user(admin_email, hashed_password, "admin", None)
    else:
        logger.info("Global admin user already exists. Skipping.")

    # ✅ Seed FAQs for ALL tenants
    faqs_to_add = [
        ("What is the company's return policy?", "You can return items within 30 days."),
        ("How do I contact support?", "Please email support@example.com."),
        ("What are your business hours?", "We operate from 9 AM to 6 PM, Monday to Friday.")
    ]

    for tenant in tenants:
        tenant_id = tenant["tenant_id"]
        if not get_all_faqs(tenant_id):
            for question, answer in faqs_to_add:
                embedding = generate_embedding(question + " " + answer)
                if embedding:
                    add_faq_to_db(question, answer, embedding, tenant_id)
            logger.info(f"FAQs added for tenant: {tenant_id}")
        else:
            logger.info(f"FAQs already exist for tenant {tenant_id}. Skipping.")

    logger.info("Seeding complete.")


if __name__ == "__main__":
    seed_initial_data()
