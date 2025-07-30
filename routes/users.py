# routes/users.py

import logging
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from db.users_crud import add_user, update_user, soft_delete_user, get_all_users, get_user_by_id
from db.clients_crud import get_all_clients, get_client_by_id

users_bp = Blueprint('users_routes', __name__, template_folder='../templates')
logger = logging.getLogger(__name__)

@users_bp.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    clients = get_all_clients()
    users = get_all_users()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()
            role = 'client'  # Only client role allowed
            client_id = request.form.get('client_id', '').strip() or None
            if not email or not password:
                flash('Email and password are required.', 'danger')
            else:
                if add_user(email, password, role, client_id):
                    flash('User added successfully.', 'success')
                else:
                    flash('Error adding user. Email may already exist.', 'danger')
            return redirect(url_for('users_routes.manage_users'))

        elif action == 'update':
            user_id = request.form.get('user_id')
            email = request.form.get('email', '').strip() or None
            password = request.form.get('password', '').strip() or None
            role = 'client'  # Only client role allowed
            client_id = request.form.get('client_id', '').strip() or None
            user = get_user_by_id(user_id)
            if not user:
                flash('User not found.', 'danger')
            elif update_user(user_id, email, password, role, client_id):
                flash('User updated successfully.', 'success')
            else:
                flash('Error updating user.', 'danger')
            return redirect(url_for('users_routes.manage_users'))

        elif action == 'delete':
            user_id = request.form.get('user_id')
            user = get_user_by_id(user_id)
            if not user:
                flash('User not found.', 'danger')
            elif soft_delete_user(user_id):
                flash('User deleted successfully.', 'success')
            else:
                flash('Error deleting user.', 'danger')
            return redirect(url_for('users_routes.manage_users'))

    # Only show client users for non-super_admins
    if current_user.role != 'super_admin':
        users = [u for u in users if u['client_id'] == getattr(current_user, 'client_id', None) and u['role'] == 'client']
    return render_template('manage_users.html', users=users, clients=clients)