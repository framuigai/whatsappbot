# firebase_admin_utils.py
import firebase_admin
from firebase_admin import credentials, auth
import logging
import os
import json
from config import (
    FIREBASE_API_KEY, FIREBASE_AUTH_DOMAIN, FIREBASE_PROJECT_ID,
    FIREBASE_STORAGE_BUCKET, FIREBASE_MESSAGING_SENDER_ID, FIREBASE_APP_ID,
    LOGGING_LEVEL, log_level_map
)

logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO)) # Set level for this module

# Placeholder for the initialized app
_firebase_app = None

def init_firebase_admin():
    """Initializes the Firebase Admin SDK."""
    global _firebase_app
    if _firebase_app:
        logger.info("Firebase Admin SDK already initialized.")
        return _firebase_app

    try:
        # Check if a service account JSON file exists
        service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        if service_account_path and os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized using service account file.")
        else:
            # Fallback to environment variables (less secure for prod, but works if service account is too complex)
            # This requires you to set the environment variables that usually go into the service account JSON
            # NOT RECOMMENDED FOR PRODUCTION. Use a service account file.
            # Example if you MUST use env vars directly (adapt keys as needed):
            # For demonstration, we'll try to use Project ID if no service account path.
            # In a real scenario, you'd usually have a `GOOGLE_APPLICATION_CREDENTIALS` env var
            # pointing to the service account file, which firebase_admin.initialize_app() picks up automatically.
            # For direct initialization without a file:
            # You would typically load a JSON string from an env var, or provide values
            # for "project_id", "private_key_id", "private_key", "client_email", etc.
            # directly to credentials.Certificate().
            # For simplicity, if no path, we'll just initialize without specific credentials
            # (which might work on GCP or if GOOGLE_APPLICATION_CREDENTIALS is set elsewhere).

            if FIREBASE_PROJECT_ID:
                # If you don't have a service account file, Firebase Admin SDK might try
                # to find credentials automatically (e.g., on GCP services) or use
                # GOOGLE_APPLICATION_CREDENTIALS environment variable.
                # If neither, direct initialization without creds might fail or have limited scope.
                # It's best to always use a service account file for local dev and prod.
                _firebase_app = firebase_admin.initialize_app() # Tries to find credentials automatically
                logger.warning("Firebase Admin SDK initialized without explicit credentials file. "
                               "Ensure GOOGLE_APPLICATION_CREDENTIALS is set or it's running on GCP. "
                               "Highly recommend using a service account JSON file for production.")
            else:
                logger.critical("FIREBASE_SERVICE_ACCOUNT_PATH not set, and FIREBASE_PROJECT_ID not found. "
                                "Cannot initialize Firebase Admin SDK.")
                raise ValueError("Firebase credentials not configured.")

        return _firebase_app
    except Exception as e:
        logger.critical(f"Error initializing Firebase Admin SDK: {e}")
        raise

def verify_id_token(id_token):
    """
    Verifies a Firebase ID token using the Firebase Admin SDK.
    Returns the decoded token (dict) if valid, raises an exception otherwise.
    """
    try:
        # Ensure Firebase Admin SDK is initialized
        if not _firebase_app:
            init_firebase_admin() # Attempt to initialize if not already

        decoded_token = auth.verify_id_token(id_token)
        logger.info(f"Firebase ID token verified for UID: {decoded_token.get('uid')}, Email: {decoded_token.get('email')}")
        return decoded_token
    except ValueError as e:
        logger.error(f"Invalid ID token: {e}")
        raise ValueError("Invalid ID token")
    except Exception as e:
        logger.error(f"Error verifying Firebase ID token: {e}")
        raise Exception("Failed to verify ID token")