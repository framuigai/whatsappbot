# routes/users.py

import logging
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from db.users_crud import add_user, update_user, soft_delete_user, get_all_users, get_user_by_id
from db.clients_crud import get_all_clients, get_client_by_id, add_client

users_bp = Blueprint('users_routes', __name__, template_folder='../templates')
logger = logging.getLogger(__name__)


@users_bp.route('/manage_users', methods=['GET'])
@login_required
def manage_users():
    #clients = get_all_clients()
    users = get_all_users()
    # Only show client users for non-super_admins
    if current_user.role != 'super_admin':
        users = [u for u in users if u['client_id'] == getattr(current_user, 'client_id', None) and u['role'] == 'client']
    return render_template('manage_users.html', users=users)


@users_bp.route('/manage_clients', methods=['GET', 'POST'])
@login_required
def manage_clients():
    if current_user.role != 'super_admin':
        flash("Access denied. Only super admins can view or add clients.", "danger")
        return redirect(url_for('dashboard_routes.dashboard'))

    if request.method == 'POST':
        client_id = request.form.get('client_id', '').strip()
        client_name = request.form.get('client_name', '').strip()
        phone_id = request.form.get('phone_id', '').strip()
        wa_token = request.form.get('wa_token', '').strip()
        ai_instruction = request.form.get('ai_instruction', '').strip() or None

        # Validate required fields
        if not client_id or not phone_id or not wa_token:
            flash("Client ID, WhatsApp Phone ID, and API Token are required.", "danger")
        else:
            # Check for duplicate client_id
            if get_client_by_id(client_id):
                flash(f"Client ID '{client_id}' already exists.", "danger")
            else:
                added = add_client(
                    client_id,
                    client_name,
                    phone_id,
                    wa_token,
                    ai_instruction,
                    None  # ai_model_name not set by form
                )
                if added:
                    flash(f"Client '{client_id}' added successfully.", "success")
                else:
                    flash("Failed to add client. Check logs for details.", "danger")
        return redirect(url_for('users_routes.manage_clients'))

    clients = get_all_clients()
    return render_template('manage_clients.html', clients=clients)

