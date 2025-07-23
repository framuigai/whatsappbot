# admin_routes.py
import logging
import json
from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify, abort
from flask_login import login_required, current_user
from flask_moment import Moment
from config import LOGGING_LEVEL, log_level_map, FIREBASE_CONFIG

from db.conversations_crud import (
    get_conversation_count,
    get_all_conversations,
    get_conversation_history_by_whatsapp_id,
    get_monthly_conversation_counts,
    get_daily_conversation_counts
)
from db.faqs_crud import (
    get_all_faqs,
    get_faq_by_id,
    add_faq,
    update_faq,
    delete_faq_by_id
)
# ✅ Updated import
from db.tenants_crud import (
    get_all_tenants,
    get_tenant_by_id,
    add_tenant,
    update_tenant,
    delete_tenant
)
from ai_utils import generate_embedding

admin_bp = Blueprint('admin_routes', __name__, template_folder='../templates', static_folder='../static')
logger = logging.getLogger(__name__)
logger.setLevel(log_level_map.get(LOGGING_LEVEL, logging.INFO))


@admin_bp.route('/')
@login_required
def dashboard():
    try:
        tenant_id = current_user.tenant_id if hasattr(current_user, 'tenant_id') else None
        total_conversations = get_conversation_count(tenant_id)
        logger.info(f"User {current_user.email} accessed dashboard.")
        return render_template(
            'dashboard.html',
            user_email=current_user.email,
            total_conversations=total_conversations,
            firebase_config=FIREBASE_CONFIG
        )
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}", exc_info=True)
        flash("Error loading dashboard data.", "danger")
        return render_template('dashboard.html', user_email=current_user.email, total_conversations=0,
                               firebase_config=FIREBASE_CONFIG)


@admin_bp.route('/manage_clients', methods=['GET', 'POST'])
@login_required
def manage_clients():
    if current_user.role != 'admin':
        flash("You do not have permission to manage clients.", "warning")
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
                if add_tenant(new_tenant_id, new_tenant_id, whatsapp_number_id, whatsapp_access_token,
                              ai_system_instruction):
                    flash(f"Tenant '{new_tenant_id}' added successfully!", "success")
                else:
                    flash(f"Failed to add tenant '{new_tenant_id}'.", "danger")

        elif action == 'update':
            whatsapp_access_token = request.form['whatsapp_access_token']
            ai_system_instruction = request.form.get('ai_system_instruction', '')

            if not tenant_id or not whatsapp_access_token:
                flash("All fields are required for updating a tenant.", "danger")
            else:
                if update_tenant(tenant_id, whatsapp_api_token=whatsapp_access_token,
                                 ai_system_instruction=ai_system_instruction):
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

@admin_bp.route('/view_reports')
@login_required
def view_reports():
    """Admin page to view various reports."""
    try:
        # Fetch data for charts/reports
        # Example: monthly conversation counts
        tenant_id = current_user.tenant_id if hasattr(current_user, 'tenant_id') else None
        monthly_counts = get_monthly_conversation_counts(tenant_id)
        daily_counts = get_daily_conversation_counts(tenant_id)

        # Convert counts to format suitable for Chart.js (e.g., labels and data arrays)
        monthly_labels = [m['month'] for m in monthly_counts]
        monthly_data = [m['count'] for m in monthly_counts]

        daily_labels = [d['date'] for d in daily_counts]
        daily_data = [d['count'] for d in daily_counts]

        return render_template(
            'view_reports.html',
            user_email=current_user.email,
            monthly_labels=json.dumps(monthly_labels),  # Pass as JSON string for JS
            monthly_data=json.dumps(monthly_data),
            daily_labels=json.dumps(daily_labels),
            daily_data=json.dumps(daily_data)
        )
    except Exception as e:
        logger.error(f"Error fetching report data: {e}", exc_info=True)
        flash("Error loading reports.", "danger")
        return render_template('view_reports.html', user_email=current_user.email,
                               monthly_labels="[]", monthly_data="[]",
                               daily_labels="[]", daily_data="[]")


@admin_bp.route('/manage_faqs', methods=['GET', 'POST'])
@login_required
def manage_faqs():
    """Admin page to manage FAQs."""
    tenant_id = current_user.tenant_id if hasattr(current_user, 'tenant_id') else None
    # All users can manage FAQs for their own tenant, so no role check is strictly necessary here.

    if request.method == 'POST':
        action = request.form.get('action')
        faq_id = request.form.get('faq_id')
        question = request.form.get('question')
        answer = request.form.get('answer')

        if action == 'add':
            if not question or not answer:
                flash("Question and Answer are required to add an FAQ.", "danger")
            else:
                # Generate embedding for the new question
                embedding = generate_embedding(question)
                if embedding is None:
                    flash("Failed to generate embedding for the FAQ. Please try again.", "danger")
                else:
                    if add_faq(question, answer, embedding, tenant_id):
                        flash("FAQ added successfully!", "success")
                    else:
                        flash("Failed to add FAQ. It might already exist or there was a database error.", "danger")

        elif action == 'update':
            if not faq_id or not question or not answer:
                flash("FAQ ID, Question, and Answer are required to update an FAQ.", "danger")
            else:
                # Retrieve existing FAQ to check if embedding needs regeneration
                existing_faq = get_faq_by_id(faq_id, tenant_id)
                embedding = None  # Initialize embedding
                if existing_faq and existing_faq.get('question') != question:
                    # Question changed, regenerate embedding
                    embedding = generate_embedding(question)
                    if embedding is None:
                        flash("Failed to generate new embedding for updated question. FAQ update cancelled.", "danger")
                        return redirect(url_for('admin_routes.manage_faqs'))
                elif existing_faq:
                    # Question did not change, use existing embedding
                    embedding = json.loads(existing_faq.get('embedding'))  # Deserialize
                else:
                    flash(f"FAQ with ID {faq_id} not found for update.", "danger")
                    return redirect(url_for('admin_routes.manage_faqs'))

                if update_faq(faq_id, question, answer, embedding, tenant_id):
                    flash("FAQ updated successfully!", "success")
                else:
                    flash(f"Failed to update FAQ ID {faq_id}.", "danger")

        elif action == 'delete':
            if not faq_id:
                flash("FAQ ID is required for deletion.", "danger")
            else:
                if delete_faq_by_id(faq_id, tenant_id):
                    flash(f"FAQ ID {faq_id} deleted successfully!", "success")
                else:
                    flash(f"Failed to delete FAQ ID {faq_id}.", "danger")

        return redirect(url_for('admin_routes.manage_faqs'))

    # GET request
    try:
        faqs = get_all_faqs(tenant_id)
        return render_template('manage_faqs.html', user_email=current_user.email, faqs=faqs)
    except Exception as e:
        logger.error(f"Error fetching FAQs: {e}", exc_info=True)
        flash("Error loading FAQs.", "danger")
        return render_template('manage_faqs.html', user_email=current_user.email, faqs=[])


@admin_bp.route('/view_conversation/<wa_id>')
@login_required
def view_conversation(wa_id):
    """View a specific conversation by WhatsApp ID."""
    tenant_id = current_user.tenant_id if hasattr(current_user, 'tenant_id') else None
    if not tenant_id:
        flash("Tenant ID not found for current user.", "danger")
        return redirect(url_for('admin_routes.all_conversations'))

    try:
        # MODIFIED: Pass tenant_id to the function to scope the search
        conversations = get_conversation_history_by_whatsapp_id(wa_id, tenant_id)
        if not conversations:
            flash(f"No conversation history found for WhatsApp ID: {wa_id} within your tenant.", "info")
            # Redirect to all conversations list instead of dashboard for better UX
            return redirect(url_for('admin_routes.all_conversations'))
        return render_template('view_conversation.html', user_email=current_user.email, wa_id=wa_id,
                               conversations=conversations)
    except Exception as e:
        logger.error(f"Error fetching conversation history for {wa_id}: {e}", exc_info=True)
        flash(f"Error loading conversation history for {wa_id}.", "danger")
        return redirect(url_for('admin_routes.all_conversations')) # Redirect to list on error


@admin_bp.route('/all-conversations')
@login_required
def all_conversations():
    """View a list of all unique WhatsApp conversations."""
    tenant_id = current_user.tenant_id if hasattr(current_user, 'tenant_id') else None
    if not tenant_id:
        flash("Tenant ID not found for current user.", "danger")
        return redirect(url_for('admin_routes.dashboard'))

    try:
        # MODIFIED: Pass tenant_id to the function to scope the search
        unique_conversations = get_all_conversations(tenant_id)
        return render_template('all_conversations.html', user_email=current_user.email,
                               conversations=unique_conversations)
    except Exception as e:
        logger.error(f"Error fetching all conversations: {e}", exc_info=True)
        flash("Error loading all conversations.", "danger")
        return render_template('all_conversations.html', user_email=current_user.email, conversations=[])