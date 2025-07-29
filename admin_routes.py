# admin_routes.py
import logging
import json
from flask import Blueprint, render_template, url_for, flash, redirect, request
from flask_login import login_required, current_user
from config import LOGGING_LEVEL, log_level_map, FIREBASE_CONFIG, FIREBASE_ENABLED  # <-- Add FIREBASE_ENABLED import
from werkzeug.security import generate_password_hash
from utils.auth_decorators import role_required
from firebase_admin_utils import create_user_in_firebase, update_user_in_firebase, delete_user_in_firebase

from db.conversations_crud import (
    get_conversation_count, get_all_conversations, get_conversation_history_by_whatsapp_id,
    get_monthly_conversation_counts, get_daily_conversation_counts
)
from db.faqs_crud import get_all_faqs, get_faq_by_id, add_faq, update_faq, delete_faq_by_id
from db.tenants_crud import get_all_tenants, add_tenant, update_tenant, delete_tenant
from db.users_crud import add_user, get_all_users, update_user, delete_user, get_user_by_id, get_users_by_role
from ai_utils import generate_embedding

admin_bp = Blueprint('admin_routes', __name__, template_folder='../templates', static_folder='../static')
logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))


@admin_bp.route('/')
@login_required
def dashboard():
    try:
        tenant_id = None if current_user.role == 'admin' else getattr(current_user, 'tenant_id', None)
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


@admin_bp.route('/manage_clients', methods=['GET', 'POST'])
@login_required
def manage_clients():
    # ✅ Admin-only access
    if current_user.role != 'admin':
        flash("You do not have permission to manage clients.", "warning")
        logger.warning(f"Unauthorized manage_clients access by {current_user.email}")
        return redirect(url_for('admin_routes.dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')
        tenant_id = request.form.get('tenant_id')

        if action == 'add':
            new_tenant_id = request.form['new_tenant_id']
            whatsapp_number_id = request.form['whatsapp_number_id']
            whatsapp_access_token = request.form['whatsapp_access_token']
            ai_system_instruction = request.form.get('ai_system_instruction', '')

            if not new_tenant_id or not whatsapp_number_id or not whatsapp_access_token:
                flash("All fields are required for adding a tenant.", "danger")
            else:
                if add_tenant(new_tenant_id, new_tenant_id, whatsapp_number_id, whatsapp_access_token, ai_system_instruction):
                    flash(f"Tenant '{new_tenant_id}' added successfully!", "success")
                else:
                    flash(f"Failed to add tenant '{new_tenant_id}'.", "danger")

        elif action == 'update':
            whatsapp_access_token = request.form['whatsapp_access_token']
            ai_system_instruction = request.form.get('ai_system_instruction', '')

            if not tenant_id or not whatsapp_access_token:
                flash("All fields are required for updating a tenant.", "danger")
            else:
                if update_tenant(tenant_id, whatsapp_api_token=whatsapp_access_token, ai_system_instruction=ai_system_instruction):
                    flash(f"Tenant '{tenant_id}' updated successfully!", "success")
                else:
                    flash(f"Failed to update tenant '{tenant_id}'.", "danger")

        elif action == 'delete':
            if delete_tenant(tenant_id):
                flash(f"Tenant '{tenant_id}' deleted successfully!", "success")
            else:
                flash(f"Failed to delete tenant '{tenant_id}'.", "danger")

        return redirect(url_for('admin_routes.manage_clients'))

    try:
        tenants = get_all_tenants()
        return render_template('manage_clients.html', user_email=current_user.email, tenants=tenants)
    except Exception as e:
        logger.error(f"Error fetching tenant configurations: {e}", exc_info=True)
        flash("Error loading tenant configurations.", "danger")
        return render_template('manage_clients.html', user_email=current_user.email, tenants=[])


@admin_bp.route('/view_conversation/<wa_id>')
@login_required
def view_conversation(wa_id):
    tenant_id = getattr(current_user, 'tenant_id', None)
    try:
        conversations = get_conversation_history_by_whatsapp_id(wa_id, tenant_id)
        if not conversations:
            flash(f"No conversation history found for {wa_id}.", "info")
            return redirect(url_for('admin_routes.all_conversations'))
        return render_template('view_conversation.html', user_email=current_user.email, wa_id=wa_id,
                               conversations=conversations)
    except Exception as e:
        logger.error(f"Error fetching conversation history: {e}", exc_info=True)
        flash("Error loading conversation history.", "danger")
        return redirect(url_for('admin_routes.all_conversations'))


@admin_bp.route('/manage_users', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'super_admin'])
def manage_users():
    from db import users_crud, tenants_crud
    tenants = tenants_crud.get_all_tenants()
    users = users_crud.get_all_users()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role')
            tenant_id = request.form.get('tenant_id') or None

            # Enforce role-based constraints
            if current_user.role == 'admin' and role != 'client':
                flash("Tenant admins can only create client users.", "danger")
                return redirect(url_for('admin_routes.manage_users'))

            if FIREBASE_ENABLED:
                firebase_uid = create_user_in_firebase(email, password)
                if firebase_uid:
                    users_crud.add_user(email=email, password=password, role=role, tenant_id=tenant_id, uid=firebase_uid)
                    flash(f"User {email} created successfully (in Firebase and local DB).", "success")
                    logger.info(f"User {email} created via Firebase and added to local DB.")
                else:
                    flash("Failed to create user in Firebase.", "danger")
                    logger.error(f"Failed to create user {email} in Firebase.")
            else:
                # Local DB only
                password_hash = generate_password_hash(password)
                users_crud.add_user(email=email, password_hash=password_hash, role=role, tenant_id=tenant_id)
                flash(f"User {email} created successfully (local DB only).", "success")
                logger.info(f"User {email} created in local DB (Firebase disabled).")

        elif action == 'update':
            user_id = request.form.get('user_id')
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role')
            tenant_id = request.form.get('tenant_id') or None

            user = users_crud.get_user_by_id(user_id)
            if not user:
                flash("User not found.", "danger")
                return redirect(url_for('admin_routes.manage_users'))

            if FIREBASE_ENABLED and user.get('uid'):
                update_user_in_firebase(user['uid'], email=email if email else None, password=password if password else None)
                logger.info(f"User {user['email']} updated in Firebase.")
            else:
                logger.info(f"User {user['email']} update in Firebase skipped (Firebase disabled or user has no UID).")

            # Update local DB
            password_hash = generate_password_hash(password) if password else None
            users_crud.update_user(user_id, email=email, password_hash=password_hash, role=role, tenant_id=tenant_id)
            flash("User updated successfully.", "success")
            logger.info(f"User {user['email']} updated in local DB.")

        elif action == 'delete':
            user_id = request.form.get('user_id')
            user = users_crud.get_user_by_id(user_id)
            if user:
                if FIREBASE_ENABLED and user.get('uid'):
                    delete_user_in_firebase(user['uid'])
                    logger.info(f"User {user['email']} deleted in Firebase.")
                else:
                    logger.info(f"User {user['email']} delete in Firebase skipped (Firebase disabled or no UID).")
                users_crud.delete_user(user_id)
                flash("User deleted successfully.", "success")
                logger.info(f"User {user['email']} deleted in local DB.")
            else:
                flash("User not found.", "danger")

        return redirect(url_for('admin_routes.manage_users'))

    return render_template('manage_users.html', users=users, tenants=tenants)


@admin_bp.route('/manage_client_admins', methods=['GET', 'POST'])
@login_required
@role_required(['super_admin'])
def manage_client_admins():
    from db import users_crud, tenants_crud
    tenants = tenants_crud.get_all_tenants()
    admins = users_crud.get_users_by_role('admin')  # Only tenant admins

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            email = request.form.get('email')
            password = request.form.get('password')
            tenant_id = request.form.get('tenant_id')

            if FIREBASE_ENABLED:
                firebase_uid = create_user_in_firebase(email, password)
                if firebase_uid:
                    users_crud.add_user(email=email, password=password, role='admin', tenant_id=tenant_id, uid=firebase_uid)
                    flash(f"Tenant Admin {email} added successfully (in Firebase and local DB).", "success")
                    logger.info(f"Tenant Admin {email} created via Firebase and added to local DB.")
                else:
                    flash("Failed to create tenant admin in Firebase.", "danger")
                    logger.error(f"Failed to create tenant admin {email} in Firebase.")
            else:
                # Local DB only
                password_hash = generate_password_hash(password)
                users_crud.add_user(email=email, password_hash=password_hash, role='admin', tenant_id=tenant_id)
                flash(f"Tenant Admin {email} created successfully (local DB only).", "success")
                logger.info(f"Tenant Admin {email} created in local DB (Firebase disabled).")

        elif action == 'delete':
            user_id = request.form.get('user_id')
            user = users_crud.get_user_by_id(user_id)
            if user:
                if FIREBASE_ENABLED and user.get('uid'):
                    delete_user_in_firebase(user['uid'])
                    logger.info(f"Tenant Admin {user['email']} deleted in Firebase.")
                else:
                    logger.info(f"Tenant Admin {user['email']} delete in Firebase skipped (Firebase disabled or no UID).")
                users_crud.delete_user(user_id)
                flash("Tenant Admin deleted successfully.", "success")
                logger.info(f"Tenant Admin {user['email']} deleted in local DB.")
            else:
                flash("User not found.", "danger")

        return redirect(url_for('admin_routes.manage_client_admins'))

    return render_template('manage_client_admins.html', admins=admins, tenants=tenants)


@admin_bp.route('/manage_faqs', methods=['GET', 'POST'])
@login_required
def manage_faqs():
    """Manage FAQs for the user's tenant or multiple tenants if admin."""
    try:
        tenant_id = getattr(current_user, 'tenant_id', None)

        if request.method == 'POST':
            action = request.form.get('action')
            faq_id = request.form.get('faq_id')
            question = request.form.get('question')
            answer = request.form.get('answer')

            # ✅ Admin must provide tenant_id from form
            if current_user.role == 'admin':
                tenant_id = request.form.get('tenant_id')
                if not tenant_id:
                    flash("Tenant selection is required for this action.", "danger")
                    logger.error("Admin attempted FAQ action without tenant_id.")
                    return redirect(url_for('admin_routes.manage_faqs'))

            # ✅ Validate tenant_id presence for non-admin users
            if not tenant_id:
                flash("Tenant information missing. Cannot proceed.", "danger")
                logger.error("FAQ action attempted without tenant_id.")
                return redirect(url_for('admin_routes.manage_faqs'))

            if action == 'add':
                if not question or not answer:
                    flash("Question and Answer are required.", "danger")
                else:
                    embedding = generate_embedding(question)
                    if embedding is None:
                        flash("Failed to generate embedding. Try again.", "danger")
                    else:
                        if add_faq(question, answer, embedding, tenant_id):
                            flash("FAQ added successfully!", "success")
                            logger.info(f"FAQ added for tenant_id={tenant_id}")
                        else:
                            flash("Failed to add FAQ.", "danger")

            elif action == 'update':
                if not faq_id or not question or not answer:
                    flash("FAQ ID, Question, and Answer are required.", "danger")
                else:
                    existing_faq = get_faq_by_id(faq_id, tenant_id)
                    if not existing_faq:
                        flash("FAQ not found.", "danger")
                    else:
                        # ✅ Regenerate embedding only if question changed
                        if existing_faq.get('question') != question:
                            embedding = generate_embedding(question)
                            if embedding is None:
                                flash("Failed to update FAQ embedding.", "danger")
                                return redirect(url_for('admin_routes.manage_faqs'))
                        else:
                            embedding = json.loads(existing_faq.get('embedding', 'null'))

                        if update_faq(faq_id, question, answer, embedding, tenant_id):
                            flash("FAQ updated successfully!", "success")
                        else:
                            flash(f"Failed to update FAQ ID {faq_id}.", "danger")

            elif action == 'delete':
                if not faq_id:
                    flash("FAQ ID is required to delete.", "danger")
                elif delete_faq_by_id(faq_id, tenant_id):
                    flash(f"FAQ ID {faq_id} deleted successfully!", "success")
                else:
                    flash(f"Failed to delete FAQ ID {faq_id}.", "danger")

            return redirect(url_for('admin_routes.manage_faqs'))

        # ✅ GET request: fetch FAQs and tenant list for admin
        tenants = []
        if current_user.role == 'admin':
            tenants = get_all_tenants()

        faqs = get_all_faqs(tenant_id)
        return render_template('manage_faqs.html',
                               user_email=current_user.email,
                               faqs=faqs,
                               tenants=tenants,
                               user_role=current_user.role)

    except Exception as e:
        logger.error(f"Error in manage_faqs: {e}", exc_info=True)
        flash("Error loading FAQs.", "danger")
        return render_template('manage_faqs.html', user_email=current_user.email, faqs=[])


from datetime import datetime

@admin_bp.route('/all-conversations')
@login_required
def all_conversations():
    """Display all conversations for the tenant or all if admin."""
    try:
        # ✅ Admin sees all conversations; others filtered by tenant_id
        tenant_id = None if current_user.role == 'admin' else getattr(current_user, 'tenant_id', None)

        unique_conversations = get_all_conversations(tenant_id)

        return render_template(
            'all_conversations.html',
            user_email=current_user.email,
            conversations=unique_conversations,
            user_role=current_user.role
        )

    except Exception as e:
        logger.error(f"Error fetching conversations: {e}", exc_info=True)
        flash("Error loading conversations. Please try again later.", "danger")
        return render_template(
            'all_conversations.html',
            user_email=current_user.email,
            conversations=[],
            user_role=current_user.role
        )


@admin_bp.route('/view_reports')
@login_required
def view_reports():
    """Admin page to view reports with proper tenant context."""
    try:
        tenant_id = None if current_user.role == 'admin' else getattr(current_user, 'tenant_id', None)

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
