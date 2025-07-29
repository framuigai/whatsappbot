# firebase_admin_utils.py
import logging
import os
import json
from config import LOGGING_LEVEL, log_level_map, FIREBASE_ENABLED  # <-- Import FIREBASE_ENABLED

# Import firebase_admin only if enabled to avoid errors in non-Firebase mode
if FIREBASE_ENABLED:
    import firebase_admin
    from firebase_admin import credentials, auth

logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO)) # Set level for this module

# Placeholder for the initialized app
_firebase_app = None

def init_firebase_admin():
    """Initializes the Firebase Admin SDK."""
    global _firebase_app
    if not FIREBASE_ENABLED:
        logger.info("Firebase Admin SDK initialization skipped (FIREBASE_ENABLED is False).")
        return None

    if _firebase_app:
        logger.info("Firebase Admin SDK already initialized.")
        return _firebase_app

    try:
        service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

        if service_account_path:
            if os.path.exists(service_account_path):
                cred = credentials.Certificate(service_account_path)
                _firebase_app = firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized using service account file.")
            else:
                logger.critical(f"Firebase service account file not found at: {service_account_path}. "
                                "Ensure FIREBASE_SERVICE_ACCOUNT_PATH is correct or file exists.")
                raise FileNotFoundError(f"Firebase service account file not found at: {service_account_path}")
        else:
            # If FIREBASE_SERVICE_ACCOUNT_PATH is not set, try to initialize automatically.
            # This works if GOOGLE_APPLICATION_CREDENTIALS env var is set, or running on GCP.
            _firebase_app = firebase_admin.initialize_app()
            logger.warning("FIREBASE_SERVICE_ACCOUNT_PATH environment variable not set. "
                           "Attempting to initialize Firebase Admin SDK without explicit credentials file. "
                           "This may work if GOOGLE_APPLICATION_CREDENTIALS is set or running on GCP. "
                           "Highly recommend using a service account JSON file for production for explicit control.")

        return _firebase_app
    except Exception as e:
        logger.critical(f"Error initializing Firebase Admin SDK: {e}", exc_info=True)
        raise

def verify_id_token(id_token):
    """
    Verifies a Firebase ID token using the Firebase Admin SDK.
    Returns the decoded token (dict) if valid, raises an exception otherwise.
    """
    if not FIREBASE_ENABLED:
        logger.error("verify_id_token called but FIREBASE_ENABLED is False.")
        raise RuntimeError("Firebase is not enabled.")
    try:
        # Ensure Firebase Admin SDK is initialized before trying to verify
        if not _firebase_app:
            # If for some reason init_firebase_admin wasn't called before, try calling it now.
            # This makes verify_id_token more robust.
            init_firebase_admin()
            if not _firebase_app: # If still not initialized after attempt
                raise RuntimeError("Firebase Admin SDK could not be initialized.")

        decoded_token = auth.verify_id_token(id_token)
        logger.info(f"Firebase ID token verified for UID: {decoded_token.get('uid')}, Email: {decoded_token.get('email')}")
        return decoded_token
    except ValueError as e:
        logger.error(f"Invalid ID token: {e}", exc_info=True)
        raise ValueError("Invalid ID token provided")
    except Exception as e:
        logger.error(f"Unexpected error verifying Firebase ID token: {e}", exc_info=True)
        raise Exception("Failed to verify ID token due to an unexpected error")

def create_user_in_firebase(email, password):
    if not FIREBASE_ENABLED:
        logger.info("create_user_in_firebase called but FIREBASE_ENABLED is False. Returning None.")
        return None
    try:
        user = auth.create_user(email=email, password=password)
        return user.uid
    except Exception as e:
        print(f"Error creating Firebase user: {e}")
        return None

def update_user_in_firebase(uid, email=None, password=None):
    if not FIREBASE_ENABLED:
        logger.info("update_user_in_firebase called but FIREBASE_ENABLED is False. Returning False.")
        return False
    try:
        update_data = {}
        if email:
            update_data['email'] = email
        if password:
            update_data['password'] = password
        if update_data:
            auth.update_user(uid, **update_data)
        return True
    except Exception as e:
        print(f"Error updating Firebase user: {e}")
        return False

def delete_user_in_firebase(uid):
    if not FIREBASE_ENABLED:
        logger.info("delete_user_in_firebase called but FIREBASE_ENABLED is False. Returning False.")
        return False
    try:
        auth.delete_user(uid)
        return True
    except Exception as e:
        print(f"Error deleting Firebase user: {e}")
        return False
