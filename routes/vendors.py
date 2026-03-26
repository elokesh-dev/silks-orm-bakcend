from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from mongoengine import DoesNotExist
from models.vendor import Vendor

vendors_bp = Blueprint("vendors", __name__, url_prefix="/api/vendors")

VALID_PROCESS_TYPES = ["gum", "polishing", "blouse_work"]


@vendors_bp.route("", methods=["GET"])
@jwt_required()
def list_vendors():
    process_type = request.args.get("process_type", "").strip()
    if process_type:
        vendors = Vendor.objects(process_type=process_type)
    else:
        vendors = Vendor.objects()
    return jsonify([v.to_dict() for v in vendors]), 200


@vendors_bp.route("", methods=["POST"])
@jwt_required()
def create_vendor():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    process_type = (data.get("process_type") or "").strip()

    if not name:
        return jsonify({"error": "name is required"}), 400
    if process_type not in VALID_PROCESS_TYPES:
        return jsonify({"error": f"process_type must be one of {VALID_PROCESS_TYPES}"}), 400

    vendor = Vendor(
        name=name,
        process_type=process_type,
        phone=(data.get("phone") or "").strip(),
        address=(data.get("address") or "").strip(),
    )
    vendor.save()
    return jsonify(vendor.to_dict()), 201


@vendors_bp.route("/<vendor_id>", methods=["GET"])
@jwt_required()
def get_vendor(vendor_id):
    try:
        vendor = Vendor.objects.get(id=vendor_id)
    except (DoesNotExist, Exception):
        return jsonify({"error": "Vendor not found"}), 404
    return jsonify(vendor.to_dict()), 200


@vendors_bp.route("/<vendor_id>", methods=["PUT"])
@jwt_required()
def update_vendor(vendor_id):
    try:
        vendor = Vendor.objects.get(id=vendor_id)
    except (DoesNotExist, Exception):
        return jsonify({"error": "Vendor not found"}), 404

    data = request.get_json() or {}
    if "name" in data:
        vendor.name = data["name"].strip()
    if "process_type" in data:
        pt = data["process_type"].strip()
        if pt not in VALID_PROCESS_TYPES:
            return jsonify({"error": f"process_type must be one of {VALID_PROCESS_TYPES}"}), 400
        vendor.process_type = pt
    if "phone" in data:
        vendor.phone = data["phone"].strip()
    if "address" in data:
        vendor.address = data["address"].strip()

    vendor.save()
    return jsonify(vendor.to_dict()), 200


@vendors_bp.route("/<vendor_id>", methods=["DELETE"])
@jwt_required()
def delete_vendor(vendor_id):
    try:
        vendor = Vendor.objects.get(id=vendor_id)
    except (DoesNotExist, Exception):
        return jsonify({"error": "Vendor not found"}), 404
    vendor.delete()
    return jsonify({"message": "Vendor deleted"}), 200
