# admin_routes.py
import logging
from flask import Blueprint, render_template, url_for
from flask_login import login_required, current_user
from config import LOGGING_LEVEL, log_level_map
import db_utils # You'll need db_utils for fetching data for reports/tenants

admin_bp = Blueprint('admin_routes', __name__, template_folder='../templates', static_folder='../static')
logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO)) # Set level for this module

@admin_bp.route('/dashboard')
@login_required # Protect this route: only accessible if logged in
def dashboard():
    """Serves the main admin dashboard page."""
    # Example: Fetch some data for the dashboard summary
    total_conversations = db_utils.get_conversation_count() # Assuming this function exists in db_utils
    return render_template('dashboard.html', user_email=current_user.email, total_conversations=total_conversations)

@admin_bp.route('/manage-clients') # <--- Changed route path
@login_required # Protect this route
def manage_clients(): # <--- Changed function name
    """Serves the manage clients page.""" # <--- Changed docstring
    all_tenants = db_utils.get_all_tenants_config()
    return render_template('manage_clients.html', user_email=current_user.email, tenants=all_tenants) # <--- Changed template name

@admin_bp.route('/view-reports')
@login_required # Protect this route
def view_reports():
    """Serves the view reports page."""
    # Example: Fetch data for a simple report
    # This might involve more complex queries or data aggregation
    monthly_stats = {"Jan": 100, "Feb": 120, "Mar": 90} # Placeholder
    return render_template('view_reports.html', user_email=current_user.email, monthly_stats=monthly_stats)