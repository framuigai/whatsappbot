# routes/users.py

import logging
from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from utils.auth_decorators import role_required
from db.users_crud import add_user, get_all_users, update_user, delete_user, get_user_by_id, get_user_by_email
from db.tenants_crud import get_all_tenants

users_bp = Blueprint('users_routes', __name__, template_folder='../templates')

logger = logging.getLogger(__name__)

@users_bp.route('/manage_users', methods=['GET', 'POST'])
@login_required
@role_required(['super_admin', 'admin'])
def manage_users():
    tenants = get_all_tenants()
    messages = []

    if request.method == 'POST':
        action = request.form.get('action')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        tenant_id = request.form.get('tenant_id') or None
        user_id = request.form.get('user_id')

        if current_user.role == 'admin':
            tenant_id = current_user.tenant_id
            role = 'client'

        if action == 'add':
            if get_user_by_email(email):
                messages.append(('error', f'User with email {email} already exists.'))
            else:
                add_user(
                    email=email,
                    password=password,
                    role=role,
                    tenant_id=tenant_id
                )
                messages.append(('success', f'User {email} added.'))
        elif action == 'update':
            if current_user.role == 'admin':
                target_user = get_user_by_id(user_id)
                if not target_user or target_user['tenant_id'] != current_user.tenant_id:
                    messages.append(('error', "You cannot modify users outside your tenant."))
                else:
                    update_user(
                        user_id=user_id,
                        email=email,
                        password=password,
                        role='client',
                        tenant_id=current_user.tenant_id
                    )
                    messages.append(('success', f'User {email} updated.'))
            else:
                update_user(
                    user_id=user_id,
                    email=email,
                    password=password,
                    role=role,
                    tenant_id=tenant_id
                )
                messages.append(('success', f'User {email} updated.'))
        elif action == 'delete':
            if current_user.role == 'admin':
                target_user = get_user_by_id(user_id)
                if not target_user or target_user['tenant_id'] != current_user.tenant_id:
                    messages.append(('error', "You cannot delete users outside your tenant."))
                else:
                    delete_user(user_id)
                    messages.append(('success', f'User {user_id} deleted.'))
            else:
                delete_user(user_id)
                messages.append(('success', f'User {user_id} deleted.'))

    if current_user.role == 'super_admin':
        users = get_all_users()
    elif current_user.role == 'admin':
        users = [
            user for user in get_all_users()
            if user['tenant_id'] == current_user.tenant_id and user['role'] == 'client'
        ]
    else:
        users = []
    return render_template('manage_users.html', tenants=tenants, users=users, current_user=current_user, messages=messages)

@users_bp.route('/manage_client_admins', methods=['GET', 'POST'])
@login_required
@role_required(['super_admin'])
def manage_client_admins():
    tenants = get_all_tenants()
    admins = [user for user in get_all_users() if user['role'] == 'admin']
    messages = []
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            email = request.form.get('email')
            password = request.form.get('password')
            tenant_id = request.form.get('tenant_id')
            if get_user_by_email(email):
                messages.append(('error', f'Admin with email {email} already exists.'))
            else:
                add_user(
                    email=email,
                    password=password,
                    role='admin',
                    tenant_id=tenant_id
                )
                messages.append(('success', f'Admin {email} added.'))
        elif action == 'delete':
            user_id = request.form.get('user_id')
            delete_user(user_id)
            messages.append(('success', f'Admin {user_id} deleted.'))
    return render_template('manage_client_admins.html', tenants=tenants, admins=admins, messages=messages)

# FIX: Add /manage_clients route to support menu and templates!
@users_bp.route('/manage_clients', methods=['GET'])
@login_required
@role_required(['super_admin', 'admin'])
def manage_clients():
    tenants = get_all_tenants()
    # For admin: show only their own tenant
    if current_user.role == 'admin':
        tenants = [t for t in tenants if t['tenant_id'] == current_user.tenant_id]
    return render_template('manage_clients.html', tenants=tenants, current_user=current_user)

