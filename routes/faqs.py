# routes/faqs.py

import logging
from flask import Blueprint, render_template, flash, request, redirect, url_for
from flask_login import login_required, current_user
from db.faqs_crud import add_faq, get_all_faqs
from db.clients_crud import get_all_clients
from ai_utils import generate_embedding

faqs_bp = Blueprint('faqs_routes', __name__, template_folder='../templates')
logger = logging.getLogger(__name__)

@faqs_bp.route('/manage_faqs', methods=['GET', 'POST'])
@login_required
def manage_faqs():
    if current_user.role == 'super_admin':
        clients = get_all_clients()
        client_id = request.args.get('client_id') or request.form.get('client_id')
        if not client_id and clients:
            client_id = clients[0]['client_id']
    else:
        clients = None
        client_id = getattr(current_user, 'client_id', None)

    if request.method == 'POST':
        if current_user.role == 'client':
            question = request.form.get('question')
            answer = request.form.get('answer')
            embedding = generate_embedding(f"{question} {answer}")
            if embedding is not None:
                add_faq(question, answer, embedding, client_id, 1)
                flash("FAQ added.", "success")
            else:
                flash("Failed to generate embedding. FAQ not added.", "danger")
        else:
            flash("Super admin cannot add FAQs.", "danger")
        # Redirect to clear POST and show updated FAQs
        return redirect(url_for('faqs_routes.manage_faqs'))

    faqs = get_all_faqs(client_id) if client_id else []
    return render_template(
        'manage_faqs.html',
        faqs=faqs,
        clients=clients,
        client_id=client_id,
        current_user=current_user
    )
