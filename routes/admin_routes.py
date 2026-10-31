import os
import logging
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from config import Config
from services.ai_service import AIService
from services.mcp_service import MCPService
from database.db_manager import db_manager

logger = logging.getLogger("bea.admin_routes")
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def admin_required(f):
    """Enforces admin/lecturer credentials."""
    def wrapper(*args, **kwargs):
        if session.get("role") not in ("admin", "lecturer"):
            flash("Administrator or Lecturer privileges required.", "warning")
            return redirect(url_for("teacher.login"))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    """Admin Settings Wizard for Gemini API, MCP, and Supabase Database."""
    supabase_report = db_manager.test_connection()
    mcp_status = MCPService.get_status()

    # Masked keys for display
    def mask_key(k: str) -> str:
        if not k:
            return ""
        if len(k) <= 8:
            return "••••••••"
        return f"{k[:4]}••••••••{k[-4:]}"

    masked_config = {
        "gemini_api_key_masked": mask_key(Config.GEMINI_API_KEY),
        "gemini_model": Config.GEMINI_MODEL,
        "ai_retry_limit": Config.AI_RETRY_LIMIT,
        "ai_batch_size": Config.AI_BATCH_SIZE,
        "mcp_enabled": Config.MCP_ENABLED,
        "mcp_server_url": Config.MCP_SERVER_URL,
        "mcp_token_masked": mask_key(Config.MCP_AUTH_TOKEN),
        "supabase_url": Config.SUPABASE_URL,
        "supabase_key_masked": mask_key(Config.SUPABASE_KEY),
        "supabase_service_role_masked": mask_key(Config.SUPABASE_SERVICE_ROLE_KEY),
        "supabase_db_url_masked": mask_key(Config.SUPABASE_DB_URL)
    }

    return render_template(
        "admin/settings.html",
        config=masked_config,
        supabase_report=supabase_report,
        mcp_status=mcp_status
    )

@admin_bp.route("/api/test-gemini", methods=["POST"])
@admin_required
def test_gemini():
    """Tests Gemini connection with provided or existing key."""
    data = request.get_json() or {}
    key = data.get("api_key") or Config.GEMINI_API_KEY
    model = data.get("model") or Config.GEMINI_MODEL

    success, msg = AIService.test_connection(api_key=key, model_name=model)
    return jsonify({"success": success, "message": msg})

@admin_bp.route("/api/test-mcp", methods=["POST"])
@admin_required
def test_mcp():
    """Tests connection to MCP server."""
    data = request.get_json() or {}
    url = data.get("server_url") or Config.MCP_SERVER_URL
    token = data.get("auth_token") or Config.MCP_AUTH_TOKEN

    success, info, msg = MCPService.test_connection(server_url=url, auth_token=token)
    return jsonify({"success": success, "info": info, "message": msg})

@admin_bp.route("/api/test-supabase", methods=["POST"])
@admin_required
def test_supabase():
    """Tests Supabase API and PostgreSQL connection and validates 14 tables."""
    report = db_manager.test_connection()
    return jsonify({"success": report["configured"] and (report["api_connected"] or report["db_connected"]), "report": report})

@admin_bp.route("/api/run-migration", methods=["POST"])
@admin_required
def run_migration():
    """Executes 001_initial_bea_schema.sql to provision tables and storage bucket."""
    migration_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "migrations", "001_initial_bea_schema.sql")
    success, msg = db_manager.execute_migration_file(migration_file)
    return jsonify({"success": success, "message": msg})
