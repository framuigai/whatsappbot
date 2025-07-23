# app.py
import sys
import logging
import google.generativeai as genai
from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager, current_user, login_required, logout_user
from flask_moment import Moment # Import Flask-Moment


from config import (
    LOGGING_LEVEL, log_level_map, SECRET_KEY, SESSION_COOKIE_SECURE,
    REMEMBER_COOKIE_SECURE, SESSION_COOKIE_HTTPONLY, REMEMBER_COOKIE_HTTPONLY,
    GEMINI_API_KEY, GEMINI_MODEL_NAME, GEMINI_EMBEDDING_MODEL,
    DATABASE_NAME, WHATSAPP_PHONE_NUMBER_ID,
    FLASK_DEBUG, HOST, PORT,
    FIREBASE_API_KEY, FIREBASE_AUTH_DOMAIN, FIREBASE_PROJECT_ID,
    FIREBASE_STORAGE_BUCKET, FIREBASE_MESSAGING_SENDER_ID, FIREBASE_APP_ID
)

# Import blueprints and utility functions
from auth import auth_bp, load_user
from webhook import webhook_bp
from admin_routes import admin_bp
from api_routes import api_bp

# --- START MODIFICATION FOR DB REFACTORING ---
from db.db_connection import init_db
# --- END MODIFICATION FOR DB REFACTORING ---

import firebase_admin_utils

# --- Logging Configuration (From config.py) ---
logging.basicConfig(
    level=log_level_map.get(LOGGING_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("whatsapp_bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates')
# Initialize Flask-Moment
moment = Moment(app)

# --- App Configuration (From config.py) ---
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SESSION_COOKIE_SECURE'] = SESSION_COOKIE_SECURE
app.config['REMEMBER_COOKIE_SECURE'] = REMEMBER_COOKIE_SECURE
app.config['SESSION_COOKIE_HTTPONLY'] = SESSION_COOKIE_HTTPONLY
app.config['REMEMBER_COOKIE_HTTPONLY'] = REMEMBER_COOKIE_HTTPONLY

# --- Flask-Login Configuration ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.user_loader(load_user)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(webhook_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(api_bp)

# --- Gemini API Configuration ---
genai.configure(api_key=GEMINI_API_KEY)

@app.context_processor
def inject_firebase_config():
    """Inject Firebase configuration into all templates."""
    return {
        'FIREBASE_API_KEY': FIREBASE_API_KEY,
        'FIREBASE_AUTH_DOMAIN': FIREBASE_AUTH_DOMAIN,
        'FIREBASE_PROJECT_ID': FIREBASE_PROJECT_ID,
        'FIREBASE_STORAGE_BUCKET': FIREBASE_STORAGE_BUCKET,
        'FIREBASE_MESSAGING_SENDER_ID': FIREBASE_MESSAGING_SENDER_ID,
        'FIREBASE_APP_ID': FIREBASE_APP_ID
    }

@app.route('/')
def home():
    """Redirects to the login page or dashboard based on authentication status."""
    if current_user.is_authenticated:
        return redirect(url_for('admin_routes.dashboard'))
    return redirect(url_for('auth.login'))


@app.route('/login-page')
def login_page():
    """Renders the login page template."""
    # The login page needs the client-side Firebase config to initialize the SDK.
    # Pass the config to the template.
    return render_template('login.html', config=app.config)

# --- Database Initialization ---
with app.app_context():
    init_db()
    logger.info("Database initialization complete.")




if __name__ == "__main__":
    logging.getLogger('whatsapp_api_utils').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('db.db_connection').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('db.conversations_crud').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('db.faqs_crud').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('db.tenants_crud').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('ai_utils').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('auth').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('webhook').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('admin_routes').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))
    logging.getLogger('firebase_admin_utils').setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))

    try:
        firebase_admin_utils.init_firebase_admin()
        logger.info("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        logger.critical(f"Failed to initialize Firebase Admin SDK: {e}", exc_info=True)
        sys.exit(1) # Exit if Firebase init fails

    app.run(debug=FLASK_DEBUG, host=HOST, port=PORT, use_reloader=False)