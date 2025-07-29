# routes/conversations.py

import logging
from flask import Blueprint, render_template, flash, url_for, redirect
from flask_login import login_required, current_user
from db.conversations_crud import (
    get_all_conversations, get_conversation_history_by_whatsapp_id
)

conversations_bp = Blueprint('conversations_routes', __name__, template_folder='../templates')
logger = logging.getLogger(__name__)

@conversations_bp.route('/all-conversations')
@login_required
def all_conversations():
    try:
        if current_user.role == 'super_admin':
            conversations = get_all_conversations()
        elif current_user.role == 'admin':
            tenant_id = getattr(current_user, 'tenant_id', None)
            conversations = get_all_conversations(tenant_id=tenant_id)
        elif current_user.role == 'client':
            tenant_id = getattr(current_user, 'tenant_id', None)
            wa_id = getattr(current_user, 'wa_id', None)
            # Optionally: log for debug
            logger.debug(f"Client email: {current_user.email}, tenant_id: {tenant_id}, wa_id: {wa_id}")
            if wa_id:
                conversations = get_all_conversations(tenant_id=tenant_id, wa_id=wa_id)
            else:
                conversations = []
        else:
            conversations = []
        return render_template(
            'all_conversations.html',
            user_email=current_user.email,
            conversations=conversations,
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


@conversations_bp.route('/view_conversation/<wa_id>')
@login_required
def view_conversation(wa_id):
    try:
        # Super admin can view any; admin only their tenant; client only their own
        tenant_id = getattr(current_user, 'tenant_id', None)
        # Only allow client to view their own wa_id!
        if current_user.role == 'client':
            client_wa_id = getattr(current_user, 'wa_id', None) or current_user.email
            if wa_id != client_wa_id:
                flash("You are not authorized to view this conversation.", "danger")
                return redirect(url_for('conversations_routes.all_conversations'))

        conversations = get_conversation_history_by_whatsapp_id(wa_id, tenant_id=tenant_id)
        if not conversations:
            flash(f"No conversation history found for {wa_id}.", "info")
            return redirect(url_for('conversations_routes.all_conversations'))

        return render_template('view_conversation.html', user_email=current_user.email, wa_id=wa_id,
                               conversations=conversations)
    except Exception as e:
        logger.error(f"Error fetching conversation history: {e}", exc_info=True)
        flash("Error loading conversation history.", "danger")
        return redirect(url_for('conversations_routes.all_conversations'))
