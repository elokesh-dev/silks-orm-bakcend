from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from mongoengine import DoesNotExist

from models.order import Order, SareeItem, VendorDispatch, SareeDispatch
from models.client import Client
from models.vendor import Vendor

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")

VALID_ORDER_TYPES = ["call", "whatsapp", "store_visit", "reference"]
VALID_STATUSES = ["order_pending", "packing_completed", "completed"]
PROCESS_STEPS = ["gum", "polishing", "blouse_work"]


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _get_order(order_id):
    try:
        return Order.objects.get(id=order_id), None
    except (DoesNotExist, Exception):
        return None, jsonify({"error": "Order not found"}), 404


# ─────────────────────────────────────────────────────────────────────────────
# Create Order
# ─────────────────────────────────────────────────────────────────────────────

@orders_bp.route("", methods=["POST"])
@jwt_required()
def create_order():
    data = request.get_json() or {}

    client_id = (data.get("client_id") or "").strip()
    order_type = (data.get("order_type") or "").strip()
    reference_name = (data.get("reference_name") or "").strip()
    sarees_data = data.get("sarees", [])

    if not client_id:
        return jsonify({"error": "client_id is required"}), 400
    if order_type not in VALID_ORDER_TYPES:
        return jsonify({"error": f"order_type must be one of {VALID_ORDER_TYPES}"}), 400

    try:
        client = Client.objects.get(id=client_id)
    except (DoesNotExist, Exception):
        return jsonify({"error": "Client not found"}), 404

    if not isinstance(sarees_data, list) or len(sarees_data) == 0:
        return jsonify({"error": "sarees list is required and cannot be empty"}), 400

    sarees = []
    for i, s in enumerate(sarees_data):
        if not s.get("saree_type"):
            return jsonify({"error": f"sarees[{i}].saree_type is required"}), 400
        if not s.get("quantity") or int(s["quantity"]) < 1:
            return jsonify({"error": f"sarees[{i}].quantity must be >= 1"}), 400
        sarees.append(SareeItem(
            saree_type=s["saree_type"].strip(),
            price=float(s["price"]) if s.get("price") is not None else None,
            quantity=int(s["quantity"]),
        ))

    order = Order(
        client=client,
        client_name=client.name,
        order_type=order_type,
        reference_name=reference_name,
        sarees=sarees
    )
    order.save()
    return jsonify(order.to_dict()), 201


# ─────────────────────────────────────────────────────────────────────────────
# List Orders
# ─────────────────────────────────────────────────────────────────────────────

@orders_bp.route("", methods=["GET"])
@jwt_required()
def list_orders():
    status = request.args.get("status", "").strip()
    client_name = request.args.get("client_name", "").strip()

    qs = Order.objects()
    if status:
        qs = qs.filter(status=status)
    if client_name:
        qs = qs.filter(client_name__icontains=client_name)

    qs = qs.order_by("-created_at")
    return jsonify([o.to_dict() for o in qs]), 200


# ─────────────────────────────────────────────────────────────────────────────
# Get Single Order
# ─────────────────────────────────────────────────────────────────────────────

@orders_bp.route("/<order_id>", methods=["GET"])
@jwt_required()
def get_order(order_id):
    result = _get_order(order_id)
    if len(result) == 3:          # error tuple
        return result[1], result[2]
    order = result[0]
    return jsonify(order.to_dict()), 200


# ─────────────────────────────────────────────────────────────────────────────
# Update Top-level Order Status
# order_pending  →  packing_completed  only
# packing_completed → completed handled via /complete endpoint
# ─────────────────────────────────────────────────────────────────────────────

@orders_bp.route("/<order_id>/status", methods=["PATCH"])
@jwt_required()
def update_order_status(order_id):
    result = _get_order(order_id)
    if len(result) == 3:
        return result[1], result[2]
    order = result[0]

    if order.is_locked:
        return jsonify({"error": "Order is completed and locked"}), 400

    data = request.get_json() or {}
    new_status = (data.get("status") or "").strip()

    allowed_transitions = {
        "order_pending": ["packing_completed"],
        "packing_completed": [],   # use /complete endpoint for final step
    }

    current_allowed = allowed_transitions.get(order.status, [])
    if new_status not in current_allowed:
        return jsonify({
            "error": f"Cannot move from '{order.status}' to '{new_status}'. "
                     f"Allowed: {current_allowed}"
        }), 400

    order.status = new_status
    order.save()
    return jsonify(order.to_dict()), 200


# ─────────────────────────────────────────────────────────────────────────────
# Send sarees to a process vendor  (start a process step)
# POST /api/orders/<id>/process/<step>/send
# ─────────────────────────────────────────────────────────────────────────────

import uuid

@orders_bp.route("/<order_id>/process/<step>/send", methods=["POST"])
@jwt_required()
def send_to_process(order_id, step):
    if step not in PROCESS_STEPS:
        return jsonify({"error": f"step must be one of {PROCESS_STEPS}"}), 400

    result = _get_order(order_id)
    if len(result) == 3:
        return result[1], result[2]
    order = result[0]

    if order.is_locked:
        return jsonify({"error": "Order is completed and locked"}), 400
    if order.status == "order_pending":
        return jsonify({"error": "Complete packing before sending to process"}), 400

    data = request.get_json() or {}
    vendor_id   = (data.get("vendor_id") or "").strip()
    sarees_data = data.get("sarees_sent", [])
    price       = data.get("price")
    logistics_vendor = (data.get("logistics_vendor") or "").strip()
    logistics_type   = (data.get("logistics_type") or "").strip()

    if not vendor_id:
        return jsonify({"error": "vendor_id is required"}), 400
    if not sarees_data:
        return jsonify({"error": "sarees_sent is required"}), 400

    try:
        vendor = Vendor.objects.get(id=vendor_id)
    except (DoesNotExist, Exception):
        return jsonify({"error": "Vendor not found"}), 404

    if vendor.process_type != step:
        return jsonify({"error": f"Vendor is for '{vendor.process_type}', not '{step}'"}), 400

    # Build locked-quantity map: sum all in_process dispatches across ALL steps
    order_saree_map = {s.saree_type: s.quantity for s in order.sarees}
    locked_map = {}
    for s_step in PROCESS_STEPS:
        for dispatch in getattr(order, s_step):
            if dispatch.status == "in_process":
                for sent in dispatch.sarees_sent:
                    locked_map[sent.saree_type] = locked_map.get(sent.saree_type, 0) + sent.quantity

    sarees_sent = []
    for item in sarees_data:
        stype = (item.get("saree_type") or "").strip()
        qty   = int(item.get("quantity", 0))
        if not stype:
            return jsonify({"error": "saree_type required in sarees_sent"}), 400
        if qty < 1:
            return jsonify({"error": f"quantity for {stype} must be >= 1"}), 400
        if stype not in order_saree_map:
            return jsonify({"error": f"Saree type '{stype}' not in this order"}), 400
        available = order_saree_map[stype] - locked_map.get(stype, 0)
        if qty > available:
            return jsonify({
                "error": f"Only {available} of '{stype}' available (rest are in_process)"
            }), 400
        sarees_sent.append(SareeDispatch(saree_type=stype, quantity=qty))

    dispatch = VendorDispatch(
        id=str(uuid.uuid4()),
        vendor_id=str(vendor.id),
        vendor_name=vendor.name,
        sarees_sent=sarees_sent,
        price=float(price) if price is not None else None,
        logistics_vendor=logistics_vendor,
        logistics_type=logistics_type,
        sent_at=datetime.utcnow(),
        status="in_process",
    )

    # Append to the step list
    current = list(getattr(order, step))
    current.append(dispatch)
    setattr(order, step, current)
    order.save()
    return jsonify(order.to_dict()), 200

# ─────────────────────────────────────────────────────────────────────────────
# Mark a process step as completed
# PATCH /api/orders/<id>/process/<step>/complete
# ─────────────────────────────────────────────────────────────────────────────

# PATCH /api/orders/<id>/process/<step>/complete/<dispatch_id>
@orders_bp.route("/<order_id>/process/<step>/complete/<dispatch_id>", methods=["PATCH"])
@jwt_required()
def complete_process_step(order_id, step, dispatch_id):
    if step not in PROCESS_STEPS:
        return jsonify({"error": f"step must be one of {PROCESS_STEPS}"}), 400

    result = _get_order(order_id)
    if len(result) == 3:
        return result[1], result[2]
    order = result[0]

    if order.is_locked:
        return jsonify({"error": "Order is completed and locked"}), 400

    dispatches = list(getattr(order, step))
    target = next((d for d in dispatches if d.id == dispatch_id), None)
    if not target:
        return jsonify({"error": "Dispatch not found"}), 404
    if target.status == "completed":
        return jsonify({"error": "Already completed"}), 400

    target.status = "completed"
    target.completed_at = datetime.utcnow()
    setattr(order, step, dispatches)
    order.save()
    return jsonify(order.to_dict()), 200

# ─────────────────────────────────────────────────────────────────────────────
# Complete the entire order
# PATCH /api/orders/<id>/complete
# Requires: packing_completed status + all started process steps completed
# ─────────────────────────────────────────────────────────────────────────────

@orders_bp.route("/<order_id>/complete", methods=["PATCH"])
@jwt_required()
def complete_order(order_id):
    result = _get_order(order_id)
    if len(result) == 3:
        return result[1], result[2]
    order = result[0]

    if order.is_locked:
        return jsonify({"error": "Order is already completed and locked"}), 400
    if order.status != "packing_completed":
        return jsonify({"error": "Order must be in 'packing_completed' status first"}), 400

    # Block if any dispatch is still in_process
    for s in PROCESS_STEPS:
        for dispatch in getattr(order, s):
            if dispatch.status == "in_process":
                return jsonify({
                    "error": f"A dispatch in '{s}' step is still in progress (vendor: {dispatch.vendor_name}). Complete it first."
                }), 400

    data = request.get_json() or {}
    order.invoice_number = (data.get("invoice_number") or "").strip()
    order.remarks = (data.get("remarks") or "").strip()
    order.status = "completed"
    order.is_locked = True
    order.save()
    return jsonify(order.to_dict()), 200