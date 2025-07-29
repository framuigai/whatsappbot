# routes/faqs.py

import logging
from flask import Blueprint, render_template, flash, request
from flask_login import login_required, current_user
from db.faqs_crud import add_faq, get_all_faqs
from db.tenants_crud import get_all_tenants

faqs_bp = Blueprint('faqs_routes', __name__, template_folder='../templates')
logger = logging.getLogger(__name__)

@faqs_bp.route('/manage_faqs', methods=['GET', 'POST'])
@login_required
def manage_faqs():
    messages = []
    if current_user.role == 'super_admin':
        tenants = get_all_tenants()
        tenant_id = request.args.get('tenant_id') or request.form.get('tenant_id')
        if not tenant_id and tenants:
            tenant_id = tenants[0]['tenant_id']
    else:
        tenants = None
        tenant_id = current_user.tenant_id

    if request.method == 'POST':
        question = request.form.get('question')
        answer = request.form.get('answer')
        if current_user.role == 'super_admin':
            tenant_id = request.form.get('tenant_id')
        else:
            tenant_id = current_user.tenant_id
        if not tenant_id:
            logger.error("Admin attempted FAQ action without tenant_id.")
            messages.append(('error', "Tenant selection is required for this action."))
        else:
            add_faq(question, answer, None, tenant_id)
            messages.append(('success', "FAQ added."))

    faqs = get_all_faqs(tenant_id) if tenant_id else []
    return render_template('manage_faqs.html', faqs=faqs, tenants=tenants, tenant_id=tenant_id, current_user=current_user, messages=messages)
