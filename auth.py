# auth.py
import logging
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import UserMixin, login_user, logout_user, current_user, login_required
import firebase_admin_utils
from config import (
    LOGGING_LEVEL, log_level_map,
    FIREBASE_API_KEY, FIREBASE_AUTH_DOMAIN, FIREBASE_PROJECT_ID,
    FIREBASE_STORAGE_BUCKET, FIREBASE_MESSAGING_SENDER_ID, FIREBASE_APP_ID
)
from db.users_crud import get_user_by_email, add_user, get_user_by_uid
from werkzeug.security import generate_password_hash

auth_bp = Blueprint('auth', __name__, template_folder='../templates', static_folder='../static')
logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))

# --- Flask-Login User Model ---
class User(UserMixin):
    def __init__(self, uid, email, role=None, tenant_id=None):
        self.id = uid  # Flask-Login stores this as the user ID in session
        self.email = email
        self.role = role
        self.tenant_id = tenant_id

    def get_id(self):
        return str(self.id)

# --- Load User Callback ---
def load_user(uid):
    """
    Required by Flask-Login: reload user from UID stored in session.
    """
    if uid:
        user_data = get_user_by_uid(uid)  # ✅ FIX: Query by Firebase UID, not numeric ID
        if user_data:
            return User(user_data['uid'], user_data['email'], user_data['role'], user_data['tenant_id'])
    return None

# --- Routes ---
@auth_bp.route('/login')
def login():
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
    return render_template('login.html', firebase_config=firebase_client_config)

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    id_token = request.json.get('idToken')
    if not id_token:
        return jsonify({"status": "error", "message": "ID token missing"}), 400

    try:
        decoded_token = firebase_admin_utils.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email', 'N/A')

        local_user_data = get_user_by_email(email)
        if not local_user_data:
            logger.info(f"New Firebase user '{email}' detected. Adding to local DB.")
            default_password_hash = generate_password_hash(uid)
            default_role = 'client'
            default_tenant_id = 'default_tenant'
            if not add_user(email, default_password_hash, default_role, default_tenant_id, uid):
                return jsonify({"status": "error", "message": "Failed to provision user"}), 500
            local_user_data = get_user_by_email(email)

        user = User(local_user_data['uid'], local_user_data['email'], local_user_data['role'], local_user_data['tenant_id'])
        login_user(user, remember=True)
        logger.info(f"User {email} logged in. Role: {user.role}, Tenant: {user.tenant_id}")
        return jsonify({"status": "success", "message": "Logged in successfully", "email": email}), 200

    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Authentication failed"}), 500

@auth_bp.route('/logout')
@login_required
def logout():
    try:
        user_email = current_user.email
        logout_user()
        flash("Logged out successfully.", "success")
        logger.info(f"User {user_email} logged out.")
    except Exception as e:
        logger.error(f"Logout error: {e}", exc_info=True)
        flash("Error during logout.", "danger")
    return redirect(url_for('auth.login'))
