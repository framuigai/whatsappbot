# routes/users.py

import logging
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user

from db.users_crud import add_user, update_user, delete_user, get_all_users, get_user_by_id
from db.tenants_crud import get_all_tenants, get_tenant_by_id

users_bp = Blueprint('users_routes', __name__, template_folder='../templates')
logger = logging.getLogger(__name__)

@users_bp.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    tenants = get_all_tenants()
    users = get_all_users()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()
            role = 'client'  # force role for all users added here
            tenant_id = request.form.get('tenant_id', '').strip() or None
            if not email or not password:
                flash('Email and password are required.', 'danger')
            elif (current_user.role == 'admin' and (not tenant_id or tenant_id != current_user.tenant_id)):
                flash('Tenant admins can only add users to their own tenant.', 'danger')
            else:
                if add_user(email, password, role, tenant_id):
                    flash('User added successfully.', 'success')
                else:
                    flash('Error adding user. Email may already exist.', 'danger')
            return redirect(url_for('users_routes.manage_users'))

        elif action == 'update':
            user_id = request.form.get('user_id')
            email = request.form.get('email', '').strip() or None
            password = request.form.get('password', '').strip() or None
            role = 'client'  # force role
            tenant_id = request.form.get('tenant_id', '').strip() or None
            user = get_user_by_id(user_id)
            if not user:
                flash('User not found.', 'danger')
            elif (current_user.role == 'admin' and (not tenant_id or tenant_id != current_user.tenant_id)):
                flash('Tenant admins can only update users in their own tenant.', 'danger')
            elif update_user(user_id, email, password, role, tenant_id):
                flash('User updated successfully.', 'success')
            else:
                flash('Error updating user.', 'danger')
            return redirect(url_for('users_routes.manage_users'))

        elif action == 'delete':
            user_id = request.form.get('user_id')
            user = get_user_by_id(user_id)
            if not user:
                flash('User not found.', 'danger')
            elif (current_user.role == 'admin' and user['tenant_id'] != current_user.tenant_id):
                flash('Tenant admins can only delete users in their own tenant.', 'danger')
            elif delete_user(user_id):
                flash('User deleted successfully.', 'success')
            else:
                flash('Error deleting user.', 'danger')
            return redirect(url_for('users_routes.manage_users'))

    # Only show clients to tenant admins; super admin sees all
    if current_user.role == 'admin':
        users = [u for u in users if u['tenant_id'] == current_user.tenant_id and u['role'] == 'client']
    return render_template('manage_users.html', users=users, tenants=tenants)

@users_bp.route('/manage_client_admins', methods=['GET', 'POST'])
@login_required
def manage_client_admins():
    if current_user.role != 'super_admin':
        abort(403)
    tenants = get_all_tenants()
    admins = [u for u in get_all_users() if u['role'] == 'admin']

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()
            role = 'admin'  # force role for admins
            tenant_id = request.form.get('tenant_id', '').strip() or None
            if not email or not password or not tenant_id:
                flash('All fields are required.', 'danger')
            elif add_user(email, password, role, tenant_id):
                flash('Tenant admin added successfully.', 'success')
            else:
                flash('Error adding tenant admin. Email may already exist.', 'danger')
            return redirect(url_for('users_routes.manage_client_admins'))
        elif action == 'delete':
            user_id = request.form.get('user_id')
            user = get_user_by_id(user_id)
            if not user:
                flash('Tenant admin not found.', 'danger')
            elif delete_user(user_id):
                flash('Tenant admin deleted.', 'success')
            else:
                flash('Error deleting tenant admin.', 'danger')
            return redirect(url_for('users_routes.manage_client_admins'))

    return render_template('manage_client_admins.html', admins=admins, tenants=tenants)
