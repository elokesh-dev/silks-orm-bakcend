from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from mongoengine import ValidationError, DoesNotExist
from models.client import Client

clients_bp = Blueprint("clients", __name__, url_prefix="/api/clients")


@clients_bp.route("", methods=["GET"])
@jwt_required()
def list_clients():
    search = request.args.get("search", "").strip()
    print(search)
    if search:
        print(search)
        clients = Client.objects(name__icontains=search)
    else:
        clients = Client.objects()
        print('s')
        print(clients)
    return jsonify([c.to_dict() for c in clients]), 200


@clients_bp.route("", methods=["POST"])
@jwt_required()
def create_client():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    client = Client(
        name=name,
        phone=(data.get("phone") or "").strip(),
        address=(data.get("address") or "").strip(),
    )
    try:
        client.save()
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(client.to_dict()), 201


@clients_bp.route("/<client_id>", methods=["GET"])
@jwt_required()
def get_client(client_id):
    try:
        client = Client.objects.get(id=client_id)
    except (DoesNotExist, Exception):
        return jsonify({"error": "Client not found"}), 404
    return jsonify(client.to_dict()), 200


@clients_bp.route("/<client_id>", methods=["PUT"])
@jwt_required()
def update_client(client_id):
    try:
        client = Client.objects.get(id=client_id)
    except (DoesNotExist, Exception):
        return jsonify({"error": "Client not found"}), 404

    data = request.get_json() or {}
    if "name" in data:
        name = data["name"].strip()
        if not name:
            return jsonify({"error": "name cannot be empty"}), 400
        client.name = name
    if "phone" in data:
        client.phone = data["phone"].strip()
    if "address" in data:
        client.address = data["address"].strip()

    client.save()
    return jsonify(client.to_dict()), 200


@clients_bp.route("/<client_id>", methods=["DELETE"])
@jwt_required()
def delete_client(client_id):
    try:
        client = Client.objects.get(id=client_id)
    except (DoesNotExist, Exception):
        return jsonify({"error": "Client not found"}), 404
    client.delete()
    return jsonify({"message": "Client deleted"}), 200
