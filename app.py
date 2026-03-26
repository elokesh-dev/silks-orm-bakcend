import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
import mongoengine
from flask_cors import CORS   # 👈 add this

from routes.auth import auth_bp
from routes.clients import clients_bp
from routes.vendors import vendors_bp
from routes.orders import orders_bp


def create_app():
    app = Flask(__name__)

    # ── Config ────────────────────────────────────────────────────────────────
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET", "changeme")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False

    # ── Enable CORS ───────────────────────────────────────────────────────────
    CORS(app)   # 👈 this enables CORS for all routes

    # Optional: restrict origins (recommended for production)
    # CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})

    # ── MongoDB ───────────────────────────────────────────────────────────────
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/saree_db")
    mongoengine.connect(host=mongo_uri)

    # ── Extensions ────────────────────────────────────────────────────────────
    JWTManager(app)

    # ── Blueprints ────────────────────────────────────────────────────────────
    app.register_blueprint(auth_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(vendors_bp)
    app.register_blueprint(orders_bp)

    # ── Error handlers ────────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Internal server error"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)