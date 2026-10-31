import os
from datetime import timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base application configuration with strict security defaults."""
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "bea-secure-session-key-dev-default-38f92b71c4")
    
    # Session security
    SESSION_COOKIE_NAME = "bea_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=4)
    
    # Timezone (Asia/Kolkata default as required for Diploma assessments)
    TIMEZONE_NAME = os.getenv("APP_TIMEZONE", "Asia/Kolkata")
    try:
        from zoneinfo import ZoneInfo
        TIMEZONE = ZoneInfo(TIMEZONE_NAME)
    except Exception:
        from datetime import timezone as dt_timezone
        # IST is UTC + 5 hours 30 minutes
        TIMEZONE = dt_timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()  # Public / Anon key
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()  # Backend only
    SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "").strip()
    STORAGE_BUCKET = "bea-answer-scripts"
    
    # Google Gemini AI Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    AI_RETRY_LIMIT = int(os.getenv("AI_RETRY_LIMIT", "3"))
    AI_BATCH_SIZE = int(os.getenv("AI_BATCH_SIZE", "5"))
    
    # MCP Integration Configuration
    MCP_ENABLED = os.getenv("MCP_ENABLED", "false").lower() in ("true", "1", "yes")
    MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "").strip()
    MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "").strip()
    
    # Student PIN Authentication & Rate Limiting
    MAX_FAILED_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15
    
    # File upload rules
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max payload
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "pdf"}
    MAX_PAGE_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB limit per page
    TARGET_COMPRESSED_KB = 400  # Target image size for fast AI & mobile viewing
