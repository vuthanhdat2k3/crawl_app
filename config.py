"""
Configuration - Sử dụng Environment Variables từ .env
Đảm bảo bảo mật bằng cách không hardcode credentials trong code.
"""
import os
from dotenv import load_dotenv

# Load biến môi trường từ file .env nếu có
load_dotenv()

# ==================== MongoDB Configuration ====================
MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "manga_heaven")

if not MONGODB_URI:
    print("⚠️  WARNING: MONGODB_URI chưa được thiết lập trong .env")

# ==================== ImageKit.io Configuration ====================
IMAGEKIT_PUBLIC_KEY = os.getenv("IMAGEKIT_PUBLIC_KEY", "")
IMAGEKIT_PRIVATE_KEY = os.getenv("IMAGEKIT_PRIVATE_KEY", "")
IMAGEKIT_URL_ENDPOINT = os.getenv("IMAGEKIT_URL_ENDPOINT", "")

if not IMAGEKIT_PRIVATE_KEY:
    print("⚠️  WARNING: IMAGEKIT_PRIVATE_KEY chưa được thiết lập trong .env")

# ==================== App Configuration ====================
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-this-in-prod")
