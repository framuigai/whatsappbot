# utils/auth_decorators.py
from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def role_required(roles):
    """Restrict access to specific roles."""
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                flash("Access denied: Insufficient permissions.", "danger")
                return redirect(url_for('admin_routes.dashboard'))
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper
