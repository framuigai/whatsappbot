# routes/dashboard.py

import logging
import json
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from config import LOGGING_LEVEL, log_level_map, FIREBASE_CONFIG
from db.conversations_crud import (
    get_conversation_count, get_monthly_conversation_counts, get_daily_conversation_counts
)

dashboard_bp = Blueprint('dashboard_routes', __name__, template_folder='../templates')

logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))

@dashboard_bp.route('/')
@login_required
def dashboard():
    try:
        # Fix: super_admin sees all, admin only tenant, client only self
        tenant_id = current_user.tenant_id if hasattr(current_user, 'tenant_id') else None
        if current_user.role == 'super_admin':
            tenant_id = None  # See all
        total_conversations = get_conversation_count(tenant_id)
        logger.info(f"User {current_user.email} accessed dashboard.")
        return render_template(
            'dashboard.html',
            user_email=current_user.email,
            total_conversations=total_conversations,
            firebase_config=FIREBASE_CONFIG,
            user_role=current_user.role
        )
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}", exc_info=True)
        flash("Error loading dashboard data.", "danger")
        return render_template(
            'dashboard.html',
            user_email=current_user.email,
            total_conversations=0,
            firebase_config=FIREBASE_CONFIG,
            user_role=current_user.role
        )

@dashboard_bp.route('/view_reports')
@login_required
def view_reports():
    try:
        tenant_id = current_user.tenant_id if hasattr(current_user, 'tenant_id') else None
        if current_user.role == 'super_admin':
            tenant_id = None
        monthly_counts = get_monthly_conversation_counts(tenant_id)
        daily_counts = get_daily_conversation_counts(tenant_id)
        monthly_labels = [m['month'] for m in monthly_counts]
        monthly_data = [m['count'] for m in monthly_counts]
        daily_labels = [d['date'] for d in daily_counts]
        daily_data = [d['count'] for d in daily_counts]

        return render_template(
            'view_reports.html',
            user_email=current_user.email,
            monthly_labels=json.dumps(monthly_labels),
            monthly_data=json.dumps(monthly_data),
            daily_labels=json.dumps(daily_labels),
            daily_data=json.dumps(daily_data),
            monthly_data_raw=monthly_counts,
            daily_data_raw=daily_counts,
            user_role=current_user.role
        )
    except Exception as e:
        logger.error(f"Error fetching report data: {e}", exc_info=True)
        flash("Error loading reports.", "danger")
        return render_template('view_reports.html', user_email=current_user.email,
                               monthly_labels="[]", monthly_data="[]",
                               daily_labels="[]", daily_data="[]",
                               monthly_data_raw=[], daily_data_raw=[],
                               user_role=current_user.role)
