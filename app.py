# app.py
import sys
import logging
import google.generativeai as genai
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from config import (
    LOGGING_LEVEL, log_level_map, SECRET_KEY, SESSION_COOKIE_SECURE,
    REMEMBER_COOKIE_SECURE, SESSION_COOKIE_HTTPONLY, REMEMBER_COOKIE_HTTPONLY,
    GEMINI_API_KEY, GEMINI_MODEL_NAME, GEMINI_EMBEDDING_MODEL,
    DATABASE_NAME, WHATSAPP_PHONE_NUMBER_ID,
    FLASK_DEBUG, HOST, PORT
)

# Import blueprints and utility functions
from auth import auth_bp, load_user # Import auth_bp and load_user from auth.py
from webhook import webhook_bp      # Import webhook_bp from webhook.py
from admin_routes import admin_bp   # Import admin_bp from admin_routes.py
import db_utils
from ai_utils import generate_embedding # Only generate_embedding for initial FAQ setup
import firebase_admin_utils # For server-side Admin SDK initialization


# --- Logging Configuration (From config.py) ---
logging.basicConfig(
    level=log_level_map.get(LOGGING_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("whatsapp_bot.log"),  # Logs to a file
        logging.StreamHandler(sys.stdout)  # Logs to the console
    ]
)
logger = logging.getLogger(__name__)  # Get a logger for the main app

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

# --- Flask Configuration (From config.py) ---
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SESSION_COOKIE_SECURE'] = SESSION_COOKIE_SECURE
app.config['REMEMBER_COOKIE_SECURE'] = REMEMBER_COOKIE_SECURE
app.config['SESSION_COOKIE_HTTPONLY'] = SESSION_COOKIE_HTTPONLY
app.config['REMEMBER_COOKIE_HTTPONLY'] = REMEMBER_COOKIE_HTTPONLY

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login' # 'auth' is the blueprint name, 'login' is the route function name
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"

# Register the user_loader from the auth blueprint
login_manager.user_loader(load_user)

# --- Register Blueprints ---
app.register_blueprint(auth_bp)
app.register_blueprint(webhook_bp)
app.register_blueprint(admin_bp)

# --- Gemini API Configuration (From config.py) ---
if not GEMINI_API_KEY:
    logger.critical("GEMINI_API_KEY not set. AI functionalities will not work.")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("Gemini API configured successfully.")
    except Exception as e:
        logger.critical(f"Failed to configure Gemini API: {e}")

# --- Initial Routes ---
@app.route('/')
def index():
    """Serves the main index page. Redirects to dashboard if logged in, otherwise to login."""
    return redirect(url_for('auth.login')) # Always redirect to login as per Day 1's index.html

# --- Database Initialization & FAQ Setup ---
with app.app_context():
    db_utils.init_db()
    logger.info("Database initialization complete.")

    # Helper function for adding FAQs with validation and embedding generation (from original app.py)
    # Kept here as it's part of the *initialization* logic
    def add_faq_with_validation_and_embedding(question, answer):
        """
        Adds an FAQ to the database, generating its embedding.
        Returns True on success, False on failure.
        """
        if not question or not question.strip():
            logger.error(f"Validation failed: FAQ question cannot be empty. Q: '{question}'")
            return False
        if not answer or not answer.strip():
            logger.error(f"Validation failed: FAQ question: '{question}', answer cannot be empty. A: '{answer}'")
            return False

        embedding = generate_embedding(question)
        if embedding:
            faq_id = db_utils.add_faq(question, answer, embedding)
            if faq_id:
                logger.info(f"Successfully added FAQ (ID: {faq_id}): Q='{question[:50]}...'")
                return True
            else:
                logger.error(f"Failed to add FAQ to DB after embedding: Q='{question[:50]}...'")
                return False
        else:
            logger.error(f"Failed to generate embedding for FAQ: Q='{question[:50]}...'")
            return False

    # --- Initial FAQ Loading (EXISTING - KEPT AS IS, COMMENTED OUT) ---
    """
    logger.info("Attempting to add initial FAQs (if not already present)...")
    if not db_utils.get_all_faqs(): # Only add if no FAQs exist
        if add_faq_with_validation_and_embedding("What is the company's return policy?", "Our return policy allows returns within 30 days of purchase with a valid receipt."):
            pass
        else:
            logger.error("Failed to add initial FAQ 1.")

        if add_faq_with_validation_and_embedding("How do I contact customer support?", "You can reach customer support by calling 1-800-555-0199 or emailing support@example.com."):
            pass
        else:
            logger.error("Failed to add initial FAQ 2.")

        if add_faq_with_validation_and_embedding("Where are you located?", "Our main office is located in Nairobi, Kenya."):
            pass
        else:
            logger.error("Failed to add initial FAQ 3.")

        if add_faq_with_validation_and_embedding("Do you offer international shipping?", "Yes, we ship to most countries worldwide. Shipping fees apply."):
            pass
        else:
            logger.error("Failed to add initial FAQ 4.")

        if add_faq_with_validation_and_embedding("What is your refund procedure?", "To get a refund, please bring the item and receipt to any store location or mail it back to us."):
            pass
        else:
            logger.error("Failed to add initial FAQ 5.")
    else:
        logger.info("FAQs already exist in the database. Skipping initial FAQ loading.")
    """
    # --- End of Initial FAQ Loading Block ---

    # --- IMPORTANT: Initial tenant configuration setup (EXISTING - KEPT AS IS, COMMENTED OUT) ---
    """
    # This block will add your first tenant mapping to the 'tenants_config' table.
    # Replace the placeholder values with your ACTUAL WhatsApp Business Phone Number ID
    # and your chosen unique tenant ID for this client.
    # !!! YOU MUST COMMENT OUT OR REMOVE THIS BLOCK AFTER THE FIRST SUCCESSFUL RUN !!!
    # !!! Otherwise, it will try to add the same entry on every restart, which is harmless
    # !!! due to INSERT OR REPLACE, but unnecessary.

    YOUR_WHATSAPP_TEST_PHONE_ID_FROM_ENV = WHATSAPP_PHONE_NUMBER_ID # Using value from config
    YOUR_FIRST_INTERNAL_TENANT_ID = "my_initial_client_id"
    YOUR_FIRST_TENANT_NAME = "My Primary Test Client"

    if YOUR_WHATSAPP_TEST_PHONE_ID_FROM_ENV:
        if db_utils.get_tenant_id_from_whatsapp_phone_number(YOUR_WHATSAPP_TEST_PHONE_ID_FROM_ENV) is None:
            logger.info(
                f"Adding initial tenant configuration for WhatsApp Phone ID: {YOUR_WHATSAPP_TEST_PHONE_ID_FROM_ENV}")
            db_utils.add_tenant_config(YOUR_WHATSAPP_TEST_PHONE_ID_FROM_ENV, YOUR_FIRST_INTERNAL_TENANT_ID,
                                       YOUR_FIRST_TENANT_NAME)
        else:
            logger.info(
                f"Tenant configuration for WhatsApp Phone ID {YOUR_WHATSAPP_TEST_PHONE_ID_FROM_ENV} already exists in DB.")
    else:
        logger.error(
            "WHATSAPP_PHONE_NUMBER_ID environment variable not set. Cannot auto-add initial tenant config.")
    """
    # --- END IMPORTANT: Initial tenant configuration setup ---


if __name__ == "__main__":
    # Set logging levels for imported modules (from config.py)
    logging.getLogger('whatsapp_api_utils').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('db_utils').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('ai_utils').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('auth').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('webhook').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('admin_routes').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('firebase_admin_utils').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))

    # --- Firebase Admin SDK Initialization ---
    # Call this here to ensure it runs when the app starts
    try:
        firebase_admin_utils.init_firebase_admin()
        logger.info("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        logger.critical(f"Failed to initialize Firebase Admin SDK: {e}")
        # Consider exiting or disabling auth features if Admin SDK fails to initialize

    logger.info("Flask app starting...")
    app.run(debug=FLASK_DEBUG, host=HOST, port=PORT)