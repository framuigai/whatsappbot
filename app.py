# app.py
import sys
import logging
import google.generativeai as genai
from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager
from config import (
    LOGGING_LEVEL, log_level_map, SECRET_KEY, SESSION_COOKIE_SECURE,
    REMEMBER_COOKIE_SECURE, SESSION_COOKIE_HTTPONLY, REMEMBER_COOKIE_HTTPONLY,
    GEMINI_API_KEY, GEMINI_MODEL_NAME, GEMINI_EMBEDDING_MODEL,
    DATABASE_NAME, WHATSAPP_PHONE_NUMBER_ID,
    FLASK_DEBUG, HOST, PORT
)

# Import blueprints and utility functions
from auth import auth_bp, load_user
from webhook import webhook_bp
from admin_routes import admin_bp

# --- START MODIFICATION FOR DB REFACTORING ---
# Removed: import db_utils
# New: Import specific functions from the new database modules
from db.db_connection import init_db # init_db is now in db/db_connection.py
# Removed: from db.conversations_crud import get_all_faqs, add_faq # These were for the commented FAQ block
# Removed: from db.faqs_crud import add_faq, get_all_faqs # These were for the commented FAQ block
# Removed: from db.tenants_crud import get_tenant_config_by_whatsapp_id, add_tenant_config # These were for the commented tenant block
# --- END MODIFICATION FOR DB REFACTORING ---

# Removed: from ai_utils import generate_embedding # No longer needed in app.py after removing FAQ init block
import firebase_admin_utils


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

@app.route('/login')
def login():
    """Serves the login page."""
    # We removed the redirect here, as the JS on login.html will handle redirection
    return render_template('login.html', config=app.config) # Pass app.config to template

# --- Database Initialization ---
with app.app_context():
    # Call init_db from the new db_connection module
    init_db()
    logger.info("Database initialization complete.")

    # Removed: Helper function add_faq_with_validation_and_embedding
    # Removed: Initial FAQ Loading Block
    # Removed: Initial Tenant Configuration Setup Block

if __name__ == "__main__":
    # Set logging levels for imported modules (from config.py)
    logging.getLogger('whatsapp_api_utils').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    # --- START MODIFICATION FOR DB REFACTORING ---
    # Removed: logging.getLogger('db_utils').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    # New: Update loggers to point to the new, specific DB modules
    logging.getLogger('db.db_connection').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('db.conversations_crud').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('db.faqs_crud').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('db.tenants_crud').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    # --- END MODIFICATION FOR DB REFACTORING ---
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