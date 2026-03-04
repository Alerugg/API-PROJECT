from flask import Blueprint, jsonify

from app.scripts.seed import run_seed

admin_seed_bp = Blueprint("admin_seed", __name__)


@admin_seed_bp.post("/api/admin/seed")
def admin_seed():
    try:
        inserted = run_seed()
        return jsonify({"ok": True, "inserted": inserted}), 200
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(exc)}), 500

