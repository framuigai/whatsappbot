# routes/api_routes.py

import logging
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from db.clients_crud import get_all_clients, get_client_by_id
from db.faqs_crud import get_all_faqs
from db.conversations_crud import (
    get_conversation_history_by_whatsapp_id,
    get_monthly_conversation_counts,
    get_daily_conversation_counts
)

api_bp = Blueprint('api_routes', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)

@api_bp.route('/clients', methods=['GET'])
@login_required
def api_get_clients():
    """
    Return all active clients.
    """
    logger.info(f"User {current_user.email} requested client list.")
    clients = get_all_clients()
    return jsonify({"clients": clients})

@api_bp.route('/clients/<client_id>', methods=['GET'])
@login_required
def api_get_client_by_id(client_id):
    """
    Get a single client by client_id.
    """
    logger.info(f"User {current_user.email} requested client by id: {client_id}")
    client = get_client_by_id(client_id)
    if not client or client.get("active", 1) != 1:
        return jsonify({"error": "Client not found."}), 404
    return jsonify(client)

@api_bp.route('/faqs', methods=['GET'])
@login_required
def api_get_faqs():
    """
    Return all FAQs for the current user's client.
    """
    if current_user.role == "super_admin":
        client_id = request.args.get("client_id")
        if not client_id:
            return jsonify({"error": "client_id required for super_admin."}), 400
    else:
        client_id = getattr(current_user, 'client_id', None)
    faqs = get_all_faqs(client_id)
    return jsonify({"faqs": faqs})

@api_bp.route('/chat_history/<wa_id>', methods=['GET'])
@login_required
def api_get_chat_history(wa_id):
    """
    Return conversation history for a WhatsApp ID, for the current user's client only.
    """
    if current_user.role == "super_admin":
        client_id = request.args.get("client_id")
    else:
        client_id = getattr(current_user, 'client_id', None)
    history = get_conversation_history_by_whatsapp_id(wa_id, client_id=client_id)
    return jsonify({"conversations": history})

@api_bp.route('/reports/monthly', methods=['GET'])
@login_required
def api_get_monthly_report():
    """
    Return monthly conversation counts for current user's client.
    """
    if current_user.role == "super_admin":
        client_id = request.args.get("client_id")
    else:
        client_id = getattr(current_user, 'client_id', None)
    counts = get_monthly_conversation_counts(client_id)
    months = [row['month'] for row in counts]
    values = [row['count'] for row in counts]
    return jsonify({"labels": months, "values": values, "raw": counts})

@api_bp.route('/reports/daily', methods=['GET'])
@login_required
def api_get_daily_report():
    """
    Return daily conversation counts for current user's client.
    """
    if current_user.role == "super_admin":
        client_id = request.args.get("client_id")
    else:
        client_id = getattr(current_user, 'client_id', None)
    counts = get_daily_conversation_counts(client_id)
    days = [row['date'] for row in counts]
    values = [row['count'] for row in counts]
    return jsonify({"labels": days, "values": values, "raw": counts})


