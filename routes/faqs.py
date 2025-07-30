# routes/faqs.py

import logging
from flask import Blueprint, render_template, flash, request
from flask_login import login_required, current_user
from db.faqs_crud import add_faq, get_all_faqs
from db.clients_crud import get_all_clients  # Changed from tenants_crud

faqs_bp = Blueprint('faqs_routes', __name__, template_folder='../templates')
logger = logging.getLogger(__name__)

@faqs_bp.route('/manage_faqs', methods=['GET', 'POST'])
@login_required
def manage_faqs():
    messages = []
    if current_user.role == 'super_admin':
        clients = get_all_clients()
        client_id = request.args.get('client_id') or request.form.get('client_id')
        if not client_id and clients:
            client_id = clients[0]['client_id']
    else:
        clients = None
        client_id = getattr(current_user, 'client_id', None)

    if request.method == 'POST':
        question = request.form.get('question')
        answer = request.form.get('answer')
        if current_user.role == 'super_admin':
            client_id = request.form.get('client_id')
        else:
            client_id = getattr(current_user, 'client_id', None)
        if not client_id:
            logger.error("Super admin attempted FAQ action without client_id.")
            messages.append(('error', "Client selection is required for this action."))
        else:
            add_faq(question, answer, None, client_id)
            messages.append(('success', "FAQ added."))

    faqs = get_all_faqs(client_id) if client_id else []
    return render_template(
        'manage_faqs.html',
        faqs=faqs,
        clients=clients,
        client_id=client_id,
        current_user=current_user,
        messages=messages
    )
