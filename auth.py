# auth.py
import logging
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
import firebase_admin_utils # Import our new utility for Admin SDK
from config import LOGGING_LEVEL, log_level_map # Import logging config

auth_bp = Blueprint('auth', __name__, template_folder='../templates', static_folder='../static')
logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO)) # Set level for this module

# --- Flask-Login Setup (moved from app.py) ---
# This part will be initialized in app.py, but the User class and user_loader
# are defined here for modularity.

class User(UserMixin):
    def __init__(self, uid, email):
        self.id = uid
        self.email = email

    # We need a custom get_id for Flask-Login to work correctly with UIDs
    def get_id(self):
        return self.id

# This function is registered with login_manager in app.py,
# but its definition is here.
# It tells Flask-Login how to load a user object from a user ID.
def load_user(user_id):
    # In a more complex app, you might fetch user details from Firestore here
    # For now, we assume if the user_id is in the session, they are valid.
    # The actual token verification happened at /api/login.
    if user_id:
        return User(user_id, email=None) # Email can't be fetched easily here without another DB lookup
    return None

# --- Auth Routes ---
@auth_bp.route('/login')
def login():
    """Serves the login page."""
    if current_user.is_authenticated:
        return redirect(url_for('admin_routes.dashboard')) # Redirect to dashboard if already logged in
    return render_template('login.html')

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    """
    Handles Firebase ID Token verification and Flask-Login.
    Expected JSON: {"idToken": "FIREBASE_ID_TOKEN"}
    """
    id_token = request.json.get('idToken')
    if not id_token:
        return jsonify({"status": "error", "message": "ID token missing"}), 400

    try:
        # Verify the Firebase ID token using the Admin SDK
        decoded_token = firebase_admin_utils.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email', 'N/A')

        # Create a User object and log them in with Flask-Login
        user = User(uid, email)
        login_user(user, remember=True) # 'remember=True' for persistent session

        logger.info(f"User {email} (UID: {uid}) successfully logged in via Flask-Login.")
        return jsonify({"status": "success", "message": "Logged in successfully", "email": email}), 200

    except Exception as e:
        logger.error(f"Firebase ID token verification failed: {e}")
        return jsonify({"status": "error", "message": "Authentication failed"}), 401

@auth_bp.route('/logout')
def logout():
    """Logs out the current user."""
    if current_user.is_authenticated:
        logout_user()
        flash('You have been logged out.', 'info')
        logger.info("User logged out.")
    return redirect(url_for('auth.login'))