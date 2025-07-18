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
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN") # Custom token for webhook verification
# The WhatsApp Access Token should be retrieved securely, e.g., from a database per tenant
# For development, you might have a default here, but ensure it's handled for multi-tenancy
DEFAULT_WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")

# --- Gemini AI Configuration ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logging.error("GEMINI_API_KEY not set in environment variables!")
    # Depending on your application's needs, you might want to raise an error or exit
    # sys.exit("GEMINI_API_KEY is required.")

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

# --- Firebase Client Config for Frontend ---
# These variables are read from .env but are combined into a dict for easy passing to frontend
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
FIREBASE_AUTH_DOMAIN = os.getenv("FIREBASE_AUTH_DOMAIN")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")
FIREBASE_MESSAGING_SENDER_ID = os.getenv("FIREBASE_MESSAGING_SENDER_ID")
FIREBASE_APP_ID = os.getenv("FIREBASE_APP_ID")
FIREBASE_MEASUREMENT_ID = os.getenv("FIREBASE_MEASUREMENT_ID") # Optional, for Analytics

# Define the FIREBASE_CONFIG dictionary to be imported by other modules
FIREBASE_CONFIG = {
    "apiKey": FIREBASE_API_KEY,
    "authDomain": FIREBASE_AUTH_DOMAIN,
    "projectId": FIREBASE_PROJECT_ID,
    "storageBucket": FIREBASE_STORAGE_BUCKET,
    "messagingSenderId": FIREBASE_MESSAGING_SENDER_ID,
    "appId": FIREBASE_APP_ID,
    "measurementId": FIREBASE_MEASUREMENT_ID # Optional
}