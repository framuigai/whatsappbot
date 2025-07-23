# auth.py
import logging
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
import firebase_admin_utils
from config import (
    LOGGING_LEVEL, log_level_map,
    FIREBASE_API_KEY, FIREBASE_AUTH_DOMAIN, FIREBASE_PROJECT_ID,
    FIREBASE_STORAGE_BUCKET, FIREBASE_MESSAGING_SENDER_ID, FIREBASE_APP_ID
)
# ADDED: Import users_crud for database operations on users
from db.users_crud import get_user_by_id, get_user_by_email, add_user
# ADDED: For password hashing (only for local users, not Firebase Auth users)
from werkzeug.security import generate_password_hash, check_password_hash

auth_bp = Blueprint('auth', __name__, template_folder='../templates', static_folder='../static')
logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))


# --- Flask-Login Setup ---
class User(UserMixin):
    def __init__(self, uid, email, role=None, tenant_id=None):  # MODIFIED: Added role and tenant_id
        self.id = uid
        self.email = email
        self.role = role  # ADDED
        self.tenant_id = tenant_id  # ADDED

    def get_id(self):
        """Returns the unique ID for the user."""
        return str(self.id)  # MODIFIED: Ensure ID is string for Flask-Login


def load_user(user_id):
    """
    Required by Flask-Login. Reloads the user object from the user ID stored in the session.
    Fetches user details from the local 'users' table.
    """
    if user_id:
        user_data = get_user_by_id(user_id)  # MODIFIED: Fetch full user data from local DB
        if user_data:
            return User(user_data['uid'], user_data['email'], user_data['role'], user_data['tenant_id'])
    return None


# --- Auth Routes ---
@auth_bp.route('/login')
def login():
    """Serves the login page."""
    if current_user.is_authenticated:
        return redirect(url_for('admin_routes.dashboard'))

    firebase_client_config = {
        "apiKey": FIREBASE_API_KEY,
        "authDomain": FIREBASE_AUTH_DOMAIN,
        "projectId": FIREBASE_PROJECT_ID,
        "storageBucket": FIREBASE_STORAGE_BUCKET,
        "messagingSenderId": FIREBASE_MESSAGING_SENDER_ID,
        "appId": FIREBASE_APP_ID
    }
    logger.debug(f"Passing Firebase client config to login.html: {firebase_client_config}")

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
        decoded_token = firebase_admin_utils.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email', 'N/A')

        # MODIFIED: Fetch user from local DB. If not found, add them.
        local_user_data = get_user_by_email(email)
        if not local_user_data:
            # This is a new user logging in via Firebase for the first time
            logger.info(f"New Firebase user '{email}' detected. Adding to local DB.")

            # Generate a placeholder password hash (Firebase handles actual password auth)
            default_password_hash = generate_password_hash(uid)
            default_role = 'client'
            default_tenant_id = 'default_tenant'  # Ensure this tenant exists in DB

            # ✅ FIXED: Correct argument order for add_user()
            if not add_user(email, default_password_hash, default_role, default_tenant_id, uid):
                logger.error(f"Failed to add new user '{email}' to local DB.")
                return jsonify({"status": "error", "message": "Failed to provision user account"}), 500

            # Fetch the newly created user's data, including their auto-generated ID
            local_user_data = get_user_by_email(email)
            if not local_user_data:  # Should not happen if add_user was true
                logger.critical(f"Failed to retrieve newly added user '{email}' from DB.")
                return jsonify({"status": "error", "message": "User provisioning error"}), 500

        # Create Flask-Login User object with role and tenant_id from local DB
        user = User(local_user_data['uid'], local_user_data['email'], local_user_data['role'],
                    local_user_data['tenant_id'])
        login_user(user, remember=True)

        logger.info(
            f"User {email} (UID: {uid}) successfully logged in via Flask-Login. Role: {user.role}, Tenant: {user.tenant_id}")
        return jsonify({"status": "success", "message": "Logged in successfully", "email": email}), 200

    except ValueError as e:
        logger.error(f"Firebase ID token verification failed (ValueError): {e}")
        return jsonify({"status": "error", "message": "Invalid authentication token"}), 401
    except Exception as e:
        logger.error(f"Unexpected error during Firebase ID token verification: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Authentication failed due to server error"}), 500


@auth_bp.route('/logout')
@login_required
def logout():
    """Logs out the current user."""
    try:
        user_email = current_user.email if current_user.is_authenticated else 'unknown'
        logout_user()
        flash("You have been logged out successfully.", "success")
        logger.info(f"User {user_email} logged out.")
    except Exception as e:
        logger.error(f"Error during server-side logout: {e}", exc_info=True)
        flash("An error occurred during logout.", "danger")

    return redirect(url_for('auth.login'))
