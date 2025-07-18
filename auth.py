# auth.py
import logging
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app # Import current_app
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
import firebase_admin_utils
from config import (
    LOGGING_LEVEL, log_level_map,
    # Import all Firebase client-side config variables
    FIREBASE_API_KEY, FIREBASE_AUTH_DOMAIN, FIREBASE_PROJECT_ID,
    FIREBASE_STORAGE_BUCKET, FIREBASE_MESSAGING_SENDER_ID, FIREBASE_APP_ID
)

auth_bp = Blueprint('auth', __name__, template_folder='../templates', static_folder='../static')
logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO)) # Set level for this module

# --- Flask-Login Setup ---
class User(UserMixin):
    def __init__(self, uid, email):
        self.id = uid # Flask-Login uses 'id' attribute for the user's unique identifier
        self.email = email

    def get_id(self):
        """Returns the unique ID for the user."""
        return self.id

def load_user(user_id):
    """
    Required by Flask-Login. Reloads the user object from the user ID stored in the session.
    For Firebase authentication, we only need the UID.
    """
    if user_id:
        # In a real app, you might fetch more user details from your database here
        # based on the UID, but for Flask-Login's basic function, just the UID is enough
        # to re-instantiate the User object.
        return User(user_id, email=None) # Email can be fetched later or not stored if not critical for session.
    return None

# --- Auth Routes ---
@auth_bp.route('/login')
def login():
    """Serves the login page."""
    if current_user.is_authenticated:
        # Redirect to the dashboard route defined in admin_routes.py
        return redirect(url_for('admin_routes.dashboard'))

    # Prepare Firebase client-side configuration to pass to the template
    firebase_client_config = {
        "apiKey": FIREBASE_API_KEY,
        "authDomain": FIREBASE_AUTH_DOMAIN,
        "projectId": FIREBASE_PROJECT_ID,
        "storageBucket": FIREBASE_STORAGE_BUCKET,
        "messagingSenderId": FIREBASE_MESSAGING_SENDER_ID,
        "appId": FIREBASE_APP_ID
    }
    logger.debug(f"Passing Firebase client config to login.html: {firebase_client_config}")

    # Pass the firebase_client_config dictionary to the template
    return render_template('login.html', firebase_config=firebase_client_config)


@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    """
    Handles Firebase ID Token verification and Flask-Login.
    Expected JSON: {"idToken": "FIREBASE_ID_TOKEN"}
    """
    id_token = request.json.get('idToken')
    if not id_token:
        logger.warning("Attempted /api/login with missing ID token.")
        return jsonify({"status": "error", "message": "ID token missing"}), 400

    try:
        # --- Contribution to Step 4: Token Validation ---
        # 1. Call verify_id_token from firebase_admin_utils:
        decoded_token = firebase_admin_utils.verify_id_token(id_token)
        # 2. Extract UID and email from the verified token:
        uid = decoded_token['uid']
        email = decoded_token.get('email', 'N/A')

        # --- Contribution to Step 5: Flask-Login Session Handling ---
        # 3. Create a Flask-Login User object:
        user = User(uid, email)
        # 4. Log the user in, establishing a session:
        login_user(user, remember=True) # 'remember=True' for persistent session

        logger.info(f"User {email} (UID: {uid}) successfully logged in via Flask-Login.")
        return jsonify({"status": "success", "message": "Logged in successfully", "email": email}), 200

    except ValueError as e:
        # This specific exception is raised by firebase_admin_utils.verify_id_token for invalid tokens
        logger.error(f"Firebase ID token verification failed (ValueError): {e}")
        return jsonify({"status": "error", "message": "Invalid authentication token"}), 401
    except Exception as e:
        logger.error(f"Unexpected error during Firebase ID token verification: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Authentication failed due to server error"}), 500

@auth_bp.route('/logout')
def logout():
    """Logs out the current user."""
    if current_user.is_authenticated:
        logout_user() # --- Contribution to Step 5: Logout handling ---
        flash('You have been logged out.', 'info')
        logger.info("User logged out.")
    return redirect(url_for('auth.login'))