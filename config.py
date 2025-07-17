# config.py
import os
import logging
from dotenv import load_dotenv

load_dotenv() # Load environment variables once here

# --- Logging Configuration ---
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO").upper()
log_level_map = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

# --- Flask Configuration ---
# Generate a strong random key for production.
# You can generate one using: os.urandom(24).hex()
SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'a_very_strong_and_secret_key_please_change_this_in_production')
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
REMEMBER_COOKIE_SECURE = os.getenv('REMEMBER_COOKIE_SECURE', 'True').lower() == 'true'
SESSION_COOKIE_HTTPONLY = os.getenv('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
REMEMBER_COOKIE_HTTPONLY = os.getenv('REMEMBER_COOKIE_HTTPONLY', 'True').lower() == 'true'
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
HOST = '0.0.0.0'
PORT = 5000

# --- WhatsApp API Configuration ---
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
# Add WHATSAPP_ACCESS_TOKEN if it's not already read in whatsapp_api_utils
# WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")

# --- Gemini API Configuration ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL_NAME = os.getenv('GEMINI_MODEL_NAME', 'gemini-pro')
GEMINI_EMBEDDING_MODEL = os.getenv('GEMINI_EMBEDDING_MODEL', 'embedding-001')

# --- Database Configuration ---
DATABASE_NAME = os.getenv('DATABASE_NAME', 'conversations.db')

# --- Rate Limiting Configuration ---
try:
    RATE_LIMIT_SECONDS = int(os.getenv("RATE_LIMIT_SECONDS", 5))
except ValueError:
    logging.warning("Invalid RATE_LIMIT_SECONDS in .env. Defaulting to 5 seconds.")
    RATE_LIMIT_SECONDS = 5

# --- FAQ Configuration ---
try:
    FAQ_SIMILARITY_THRESHOLD = float(os.getenv('FAQ_SIMILARITY_THRESHOLD', 0.75))
except ValueError:
    logging.warning("Invalid FAQ_SIMILARITY_THRESHOLD in .env. Defaulting to 0.75.")
    FAQ_SIMILARITY_THRESHOLD = 0.75

# --- Firebase Client Config for Frontend (these will be read from .env in firebase_admin_utils for backend use) ---
# For client-side JS, you'll still construct this from env vars in your HTML/JS directly
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
FIREBASE_AUTH_DOMAIN = os.getenv("FIREBASE_AUTH_DOMAIN")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")
FIREBASE_MESSAGING_SENDER_ID = os.getenv("FIREBASE_MESSAGING_SENDER_ID")
FIREBASE_APP_ID = os.getenv("FIREBASE_APP_ID")

# Log the loaded configuration levels
logger = logging.getLogger(__name__) # Get a logger for config.py
logger.info(f"Logging level set to: {LOGGING_LEVEL}")
logger.info(f"FAQ Similarity Threshold set to: {FAQ_SIMILARITY_THRESHOLD}")
logger.info(f"Database name: {DATABASE_NAME}")