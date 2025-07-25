# auth.py
import logging
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import UserMixin, login_user, logout_user, current_user, login_required
from firebase_admin import auth as firebase_auth
from config import (
    LOGGING_LEVEL, log_level_map,
    FIREBASE_API_KEY, FIREBASE_AUTH_DOMAIN, FIREBASE_PROJECT_ID,
    FIREBASE_STORAGE_BUCKET, FIREBASE_MESSAGING_SENDER_ID, FIREBASE_APP_ID
)
from db.users_crud import get_user_by_email, add_user, get_user_by_uid

auth_bp = Blueprint('auth', __name__, template_folder='../templates', static_folder='../static')
logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))


# --- Flask-Login User Model ---
class User(UserMixin):
    def __init__(self, uid, email, role=None, tenant_id=None):
        self.id = uid  # Flask-Login stores this in session
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
        user_data = get_user_by_uid(uid)  # Fetch user from DB by UID
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
def firebase_login():
    try:
        data = request.get_json()
        id_token = data.get('idToken')
        if not id_token:
            return jsonify({"message": "Missing ID token"}), 400

        # Verify Firebase token
        decoded_token = firebase_auth.verify_id_token(id_token)
        firebase_uid = decoded_token['uid']
        email = decoded_token.get('email')

        logger.info(f"Firebase ID token verified for UID: {firebase_uid}, Email: {email}")

        # Check if user exists locally
        user_record = get_user_by_email(email)

        if user_record:
            logger.info(f"Existing user '{email}' found. Logging in.")
            user = User(uid=user_record['uid'], email=user_record['email'], role=user_record['role'], tenant_id=user_record.get('tenant_id'))
        else:
            logger.info(f"New Firebase user '{email}' detected. Adding to local DB.")
            # Provision user with Firebase UID and default role
            created = add_user(uid=firebase_uid, email=email, password_hash=None, role='client', tenant_id=None)
            if created:
                user_record = get_user_by_email(email)
                user = User(uid=user_record['uid'], email=user_record['email'], role=user_record['role'], tenant_id=user_record.get('tenant_id'))
            else:
                logger.error(f"Failed to add user '{email}' to local DB.")
                return jsonify({"message": "Failed to provision user"}), 500

        # Log in user
        login_user(user)
        return jsonify({"message": "Login successful", "email": email}), 200

    except Exception as e:
        logger.error(f"Error during Firebase login: {e}", exc_info=True)
        return jsonify({"message": "Internal server error"}), 500


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
