import os
import logging
from datetime import datetime
from flask import Flask, redirect, url_for, session, render_template, jsonify
from config import Config
from routes.student_routes import student_bp
from routes.teacher_routes import teacher_bp
from routes.admin_routes import admin_bp

# Set up clean logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bea.app")

def create_app() -> Flask:
    """Application factory for BEA AI Assessment System."""
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    # Register blueprints
    app.register_blueprint(student_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(admin_bp)

    # Custom Jinja filters
    @app.template_filter("to_kolkata_time")
    def to_kolkata_time(value):
        if not value:
            return "—"
        try:
            if isinstance(value, str):
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            else:
                dt = value
            return dt.astimezone(Config.TIMEZONE).strftime("%d %b %Y, %I:%M %p %Z")
        except Exception:
            return str(value)

    @app.route("/")
    def index():
        """Smart root redirect based on active session."""
        if session.get("role") == "admin":
            return redirect(url_for("admin.manage_lecturers"))
        elif session.get("role") == "lecturer":
            return redirect(url_for("teacher.dashboard"))
        elif session.get("role") == "student":
            return redirect(url_for("student.dashboard"))
        return render_template("portal_home.html")

    @app.route("/health")
    def health():
        """Render / cloud deployment health probe."""
        return jsonify({
            "status": "healthy",
            "service": "BEA AI Assessment System",
            "environment": app.config.get("ENV", "production"),
            "timezone": Config.TIMEZONE_NAME
        })

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template(
            "error.html",
            error_code=404,
            error_title="Page Not Found",
            error_message="The requested assessment or page could not be located."
        ), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error("Internal server error: %s", e)
        return render_template(
            "error.html",
            error_code=500,
            error_title="Server Error",
            error_message="An unexpected system error occurred. The audit trace has been logged."
        ), 500

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", os.getenv("FLASK_ENV", "")).lower() in (
        "1", "true", "yes", "development"
    )
    logger.info("Starting BEA AI Assessment System on http://127.0.0.1:%s (debug=%s)", port, debug)
    app.run(host="0.0.0.0", port=port, debug=debug)
