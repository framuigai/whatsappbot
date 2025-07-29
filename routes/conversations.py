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
        # Filter conversations: super_admin sees all, admin only their tenant, client only their own
        if current_user.role == 'super_admin':
            tenant_id = None
        elif current_user.role == 'admin':
            tenant_id = current_user.tenant_id
        else:  # client
            tenant_id = current_user.tenant_id

        all_convs = get_all_conversations(tenant_id)
        if current_user.role == 'client':
            # Only show conversations relevant to this client (e.g. by wa_id/user_id)
            wa_id = getattr(current_user, 'wa_id', None)
            conversations = [conv for conv in all_convs if conv.wa_id == wa_id]
        else:
            conversations = all_convs

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
        tenant_id = getattr(current_user, 'tenant_id', None)
        conversations = get_conversation_history_by_whatsapp_id(wa_id, tenant_id)
        if not conversations:
            flash(f"No conversation history found for {wa_id}.", "info")
            return redirect(url_for('conversations_routes.all_conversations'))
        return render_template('view_conversation.html', user_email=current_user.email, wa_id=wa_id,
                               conversations=conversations)
    except Exception as e:
        logger.error(f"Error fetching conversation history: {e}", exc_info=True)
        flash("Error loading conversation history.", "danger")
        return redirect(url_for('conversations_routes.all_conversations'))
