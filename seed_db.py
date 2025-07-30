# seed_db.py

import os
import sys
import logging
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
import uuid

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure project root is in path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir))
sys.path.insert(0, project_root)

from config import LOGGING_LEVEL, log_level_map, FIREBASE_ENABLED
from db.db_connection import (
    create_conversations_table,
    create_faqs_table,
    create_clients_table,  # CHANGED
    create_users_table
)
from db.faqs_crud import add_faq as add_faq_to_db, get_all_faqs
from db.clients_crud import add_client, get_client_by_id
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
    create_clients_table()
    create_users_table()
    logger.info("All database tables ensured to exist.")

def seed_initial_data():
    logger.info("Starting DB seeding...")
    create_all_tables()

    # --- SEED CLIENTS ---
    clients = [
        {
            "client_id": "client_one",
            "client_name": "Client One Company",
            "phone_id": os.getenv("WHATSAPP_PHONE_NUMBER_ID") or "TEST_PHONE_ID",
            "wa_token": os.getenv("WHATSAPP_ACCESS_TOKEN") or "TEST_TOKEN",
            "ai_instruction": "You are a helpful assistant for Client One.",
            "active": 1
        },
        {
            "client_id": "client_two",
            "client_name": "Client Two Company",
            "phone_id": os.getenv("WHATSAPP_PHONE_NUMBER_ID") or "TEST_PHONE_ID",
            "wa_token": os.getenv("WHATSAPP_ACCESS_TOKEN") or "TEST_TOKEN",
            "ai_instruction": "You are a helpful assistant for Client Two.",
            "active": 1
        }
    ]

    for client in clients:
        if not get_client_by_id(client["client_id"]):
            success = add_client(
                client["client_id"],
                client["client_name"],
                client["phone_id"],
                client["wa_token"],
                client["ai_instruction"],
                client["active"]  # Ensure active=1
            )
            if success:
                logger.info(f"Client added: {client['client_id']}")
            else:
                logger.warning(f"Failed to add client: {client['client_id']}")
        else:
            logger.info(f"Client {client['client_id']} already exists. Skipping.")

    # --- SEED USERS: Only super_admin and client ---
    users = [
        {"email": "superadmin@example.com", "password": "SuperAdminPass123", "role": "super_admin", "client_id": None, "active": 1},
        {"email": "client1@example.com", "password": "ClientPass1", "role": "client", "client_id": "client_one", "active": 1},
        {"email": "client2@example.com", "password": "ClientPass2", "role": "client", "client_id": "client_two", "active": 1}
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
            if not uid:
                uid = str(uuid.uuid4())
            add_user(
                email=user["email"],
                password=user["password"],
                role=user["role"],
                client_id=user["client_id"],
                uid=uid,
                active=user["active"]
            )
            logger.info(f"✅ User added to DB: {user['email']}")
        else:
            logger.info(f"User {user['email']} already exists. Skipping.")

    # --- SEED FAQs: All with active=1 ---
    faqs_to_add = [
        ("What is the company's return policy?", "You can return items within 30 days."),
        ("How do I contact support?", "Please email support@example.com."),
        ("What are your business hours?", "We operate from 9 AM to 6 PM, Monday to Friday.")
    ]

    for client in clients:
        client_id = client["client_id"]
        if not get_all_faqs(client_id):
            for question, answer in faqs_to_add:
                embedding = generate_embedding(question + " " + answer)
                if embedding:
                    add_faq_to_db(question, answer, embedding, client_id, 1)  # active=1
            logger.info(f"FAQs added for client: {client_id}")
        else:
            logger.info(f"FAQs already exist for client {client_id}. Skipping.")

    logger.info("✅ Seeding complete.")

if __name__ == "__main__":
    seed_initial_data()
