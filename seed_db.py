# seed_db.py
import os
import sys
import sqlite3
import logging
import json # For handling embeddings if they are stored as JSON strings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler() # Log to console
    ]
)
logger = logging.getLogger(__name__)

# --- Ensure project root is in path for imports to work ---
# This is crucial when running seed_db.py directly from the project root
# It allows importing modules like 'config' and 'db.db_connection'
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir)) # Assuming seed_db.py is in the root
sys.path.insert(0, project_root)

# --- Import modules from your application ---
from config import DATABASE_NAME, WHATSAPP_PHONE_NUMBER_ID, LOGGING_LEVEL, log_level_map
# Import specific DB functions
from db.db_connection import get_db_connection, create_conversations_table, create_faqs_table, create_tenants_config_table
from db.faqs_crud import add_faq as add_faq_to_db, get_all_faqs # Renamed add_faq to avoid conflict
from db.tenants_crud import add_tenant_config as add_tenant_config_to_db, get_tenant_config_by_whatsapp_id
from ai_utils import generate_embedding # Needed if you want to generate embeddings during seeding

# Reconfigure logger for this script using config's log_level_map
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))


def create_all_tables():
    """Calls all table creation functions from db.db_connection."""
    create_conversations_table()
    create_faqs_table()
    create_tenants_config_table()
    logger.info("All database tables ensured to exist.")

def seed_initial_data():
    """Seeds the initial data into the database, including tenants and FAQs."""
    logger.info("Starting database seeding process...")

    # 1. Ensure all tables are created
    create_all_tables()

    # 2. Initial Tenant Configuration Setup
    logger.info("Checking for initial tenant configuration...")
    YOUR_WHATSAPP_TEST_PHONE_ID_FROM_ENV = WHATSAPP_PHONE_NUMBER_ID
    YOUR_FIRST_INTERNAL_TENANT_ID = "my_initial_client_id" # This should ideally come from env/config if dynamic
    YOUR_FIRST_TENANT_NAME = "My Primary Test Client" # This should ideally come from env/config if dynamic

    if YOUR_WHATSAPP_TEST_PHONE_ID_FROM_ENV:
        if get_tenant_config_by_whatsapp_id(YOUR_WHATSAPP_TEST_PHONE_ID_FROM_ENV) is None:
            logger.info(
                f"Adding initial tenant configuration for WhatsApp Phone ID: {YOUR_WHATSAPP_TEST_PHONE_ID_FROM_ENV}")
            add_tenant_config_to_db(YOUR_WHATSAPP_TEST_PHONE_ID_FROM_ENV, YOUR_FIRST_INTERNAL_TENANT_ID,
                                       YOUR_FIRST_TENANT_NAME)
        else:
            logger.info(
                f"Tenant configuration for WhatsApp Phone ID {YOUR_WHATSAPP_TEST_PHONE_ID_FROM_ENV} already exists. Skipping.")
    else:
        logger.error(
            "WHATSAPP_PHONE_NUMBER_ID environment variable not set. Cannot auto-add initial tenant config.")

    # 3. Initial FAQ Loading
    logger.info("Attempting to add initial FAQs (if not already present)...")
    # Check for FAQs for this specific tenant.
    # Note: get_all_faqs expects a tenant_id. If you want truly global FAQs, you'd need a separate check
    # or a dedicated 'global' tenant_id. For now, associating with the initial tenant.
    if not get_all_faqs(YOUR_FIRST_INTERNAL_TENANT_ID): # Check if FAQs exist for the initial tenant
        faqs_to_add = [
            ("What is the company's return policy?", "Our return policy allows returns within 30 days of purchase with a valid receipt."),
            ("How do I contact customer support?", "You can reach customer support by calling 1-800-555-0199 or emailing support@example.com."),
            ("Where are you located?", "Our main office is located in Nairobi, Kenya."),
            ("Do you offer international shipping?", "Yes, we ship to most countries worldwide. Shipping fees apply."),
            ("What is your refund procedure?", "To get a refund, please bring the item and receipt to any store location or mail it back to us.")
        ]
        for question, answer in faqs_to_add:
            embedding = generate_embedding(question + " " + answer) # Generate embedding during seeding
            if embedding:
                # Use the add_faq from faqs_crud, which expects embedding as a list/array
                add_faq_to_db(question, answer, embedding, YOUR_FIRST_INTERNAL_TENANT_ID)
            else:
                logger.error(f"Failed to generate embedding for FAQ: '{question}'. Skipping FAQ addition.")
        logger.info(f"Initial FAQ seeding complete for tenant '{YOUR_FIRST_INTERNAL_TENANT_ID}'.")
    else:
        logger.info(f"FAQs already exist for tenant '{YOUR_FIRST_INTERNAL_TENANT_ID}'. Skipping initial FAQ seeding.")

    logger.info("Database seeding process finished.")

if __name__ == "__main__":
    seed_initial_data()