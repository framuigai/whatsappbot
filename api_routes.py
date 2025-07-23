# api_routes.py
import logging
from flask import Blueprint, jsonify, abort
from flask_login import login_required, current_user
from db.tenants_crud import get_all_tenants, get_tenant_by_id
from db.conversations_crud import get_conversation_history_by_whatsapp_id, get_monthly_conversation_counts
from db.faqs_crud import get_all_faqs

api_bp = Blueprint('api_routes', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)


# --- Health Check ---
@api_bp.route('/ping', methods=['GET'])
def ping():
    return jsonify({"message": "API is alive"}), 200


# --- API: Get Clients ---
@api_bp.route('/clients', methods=['GET'])
@login_required
def get_clients():
    try:
        if current_user.role == 'admin':
            tenants = get_all_tenants()
        else:
            tenant = get_tenant_by_id(current_user.tenant_id)
            tenants = [tenant] if tenant else []
        return jsonify({"tenants": tenants}), 200
    except Exception as e:
        logger.error(f"Error fetching clients: {e}", exc_info=True)
        return jsonify({"message": "Internal server error"}), 500


# --- API: Get Chat History ---
@api_bp.route('/chat_history/<string:wa_id>', methods=['GET'])
@login_required
def get_chat_history(wa_id):
    try:
        tenant_id = None if current_user.role == 'admin' else current_user.tenant_id
        conversations = get_conversation_history_by_whatsapp_id(wa_id, tenant_id=tenant_id)
        if not conversations and current_user.role != 'admin':
            abort(403, description="Access denied for this WhatsApp ID.")
        return jsonify({"wa_id": wa_id, "conversations": conversations}), 200
    except Exception as e:
        logger.error(f"Error fetching chat history for {wa_id}: {e}", exc_info=True)
        return jsonify({"message": "Internal server error"}), 500


# --- API: Get FAQs ---
@api_bp.route('/faqs', methods=['GET'])
@login_required
def get_faqs():
    try:
        tenant_id = None if current_user.role == 'admin' else current_user.tenant_id
        faqs = get_all_faqs(tenant_id=tenant_id)
        return jsonify({"faqs": faqs}), 200
    except Exception as e:
        logger.error(f"Error fetching FAQs: {e}", exc_info=True)
        return jsonify({"message": "Internal server error"}), 500


# --- ✅ NEW API: Get Monthly Report Data ---
@api_bp.route('/reports/monthly', methods=['GET'])
@login_required
def get_monthly_report():
    try:
        tenant_id = None if current_user.role == 'admin' else current_user.tenant_id
        monthly_counts = get_monthly_conversation_counts(tenant_id=tenant_id)

        labels = [item['month'] for item in monthly_counts]
        values = [item['count'] for item in monthly_counts]

        logger.info(f"Monthly report generated for tenant_id: {tenant_id}, Data points: {len(labels)}")
        return jsonify({"labels": labels, "values": values}), 200
    except Exception as e:
        logger.error(f"Error fetching monthly report: {e}", exc_info=True)
        return jsonify({"message": "Internal server error"}), 500
