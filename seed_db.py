# seed_db.py
import os
import sys
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

from config import LOGGING_LEVEL, log_level_map, FIREBASE_ENABLED  # <-- import flag
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

# Optional Firebase logic, only run if enabled
firebase_enabled = FIREBASE_ENABLED
if firebase_enabled:
    try:
        from firebase_admin_utils import init_firebase_admin, create_user_in_firebase
        init_firebase_admin()
        logger.info("Firebase Admin SDK initialized for seeding.")
    except Exception as e:
        logger.warning(f"⚠️ Firebase initialization failed, will proceed without Firebase: {e}")
        firebase_enabled = False
else:
    logger.info("FIREBASE_ENABLED is False. Firebase logic will be skipped in seeding.")

def create_all_tables():
    """Ensure all tables exist before seeding data."""
    create_conversations_table()
    create_faqs_table()
    create_tenants_table()
    create_users_table()
    logger.info("All database tables ensured to exist.")

def seed_initial_data():
    logger.info("Starting DB seeding...")
    create_all_tables()

    # ✅ Create tenants (same phone/token allowed for testing)
    tenants = [
        {
            "tenant_id": "tenant_one",
            "tenant_name": "Tenant One Company",
            "phone_id": os.getenv("WHATSAPP_PHONE_NUMBER_ID") or "TEST_PHONE_ID",
            "wa_token": os.getenv("WHATSAPP_ACCESS_TOKEN") or "TEST_TOKEN",
            "ai_instruction": "You are a helpful assistant for Tenant One."
        },
        {
            "tenant_id": "tenant_two",
            "tenant_name": "Tenant Two Company",
            "phone_id": os.getenv("WHATSAPP_PHONE_NUMBER_ID") or "TEST_PHONE_ID",  # same ID
            "wa_token": os.getenv("WHATSAPP_ACCESS_TOKEN") or "TEST_TOKEN",        # same token
            "ai_instruction": "You are a helpful assistant for Tenant Two."
        }
    ]

    for tenant in tenants:
        if not get_tenant_by_id(tenant["tenant_id"]):
            success = add_tenant(
                tenant["tenant_id"],
                tenant["tenant_name"],
                tenant["phone_id"],
                tenant["wa_token"],
                tenant["ai_instruction"]
            )
            if success:
                logger.info(f"Tenant added: {tenant['tenant_id']}")
        else:
            logger.info(f"Tenant {tenant['tenant_id']} already exists. Skipping.")

    # ✅ Easy Login Credentials for Testing
    users = [
        {"email": "superadmin@example.com", "password": "SuperAdminPass123", "role": "super_admin", "tenant_id": None},
        {"email": "tenantadmin1@example.com", "password": "TenantAdminPass1", "role": "admin", "tenant_id": "tenant_one"},
        {"email": "tenantadmin2@example.com", "password": "TenantAdminPass2", "role": "admin", "tenant_id": "tenant_two"},
        {"email": "client1@example.com", "password": "ClientPass1", "role": "client", "tenant_id": "tenant_one"},
        {"email": "client2@example.com", "password": "ClientPass2", "role": "client", "tenant_id": "tenant_two"}
    ]

    for user in users:
        if not get_user_by_email(user["email"]):
            hashed_password = generate_password_hash(user["password"])
            uid = None
            if firebase_enabled:
                try:
                    uid = create_user_in_firebase(user["email"], user["password"])
                    logger.info(f"✅ Firebase user created: {user['email']}")
                except Exception as e:
                    logger.warning(f"❌ Firebase user skipped for {user['email']}: {e}")
            # Always add user to DB; pass uid if available (None if not)
            add_user(
                email=user["email"],
                password=user["password"],
                role=user["role"],
                tenant_id=user["tenant_id"],
                uid=uid
            )
            logger.info(f"✅ User added to DB: {user['email']}")
        else:
            logger.info(f"User {user['email']} already exists. Skipping.")

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

    logger.info("✅ Seeding complete.")

if __name__ == "__main__":
    seed_initial_data()
