import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    admin_email = os.getenv("ADMIN_EMAIL", "admin@saree.com").lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")

    if email != admin_email or password != admin_password:
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(identity=email)
    return jsonify({"access_token": token, "email": email}), 200
