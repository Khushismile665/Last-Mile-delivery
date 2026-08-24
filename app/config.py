import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./delivery_tracker.db")
SECRET_KEY = os.getenv("SECRET_KEY", "lastmile_delivery_tracker_super_secret_jwt_key_2026")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SYSTEM_EMAIL = os.getenv("SYSTEM_EMAIL", "noreply@deliverytracker.com")
