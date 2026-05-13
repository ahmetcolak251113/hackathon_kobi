"""
Konfigürasyon Dosyası
Bot ayarlarını ve sabitlerini merkezi yerde tutma
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base konfigürasyon"""
    
    # Flask
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = FLASK_ENV == "development"
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
    
    # Gemini
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = "gemini-2.0-flash"  # Veya "gemini-1.5-pro", "gemini-2.5-flash"
    GEMINI_TIMEOUT = 30  # saniye
    GEMINI_MAX_TOKENS = 1024
    
    # WhatsApp
    WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN")
    WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
    WHATSAPP_API_VERSION = "v18.0"
    VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "test_token")
    WHATSAPP_BASE_URL = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"
    
    # KOBI Backend
    KOBI_API_BASE_URL = os.getenv("KOBI_API_BASE_URL", "http://127.0.0.1:3000")
    # KOBI_API_KEY = os.getenv("KOBI_API_KEY", "")  # FastAPI: JWT gerekirse
    KOBI_API_TIMEOUT = 10  # saniye
    
    # Mack Kargo
    MACK_KARGO_API_URL = os.getenv("MACK_KARGO_API_URL", "http://127.0.0.1:8001")
    # MACK_KARGO_API_KEY = os.getenv("MACK_KARGO_API_KEY", "")  # FastAPI: JWT gerekirse
    MACK_KARGO_TIMEOUT = 10  # saniye
    
    # Database (Opsiyonel - API'lar kullanıyoruz)
    # Eğer veritabanı gerekirse, aşağıdaki satırları düzenleme
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        ""  # Boş - API'lar kullanıyoruz
    )
    
    # LLM Tool Calling
    LLM_TOOL_TIMEOUT = 30  # saniye
    LLM_MAX_ITERATIONS = 5  # Tool calling döngüsü maksimum iterasyonu
    
    # Messaging
    MAX_MESSAGE_LENGTH = 4096  # WhatsApp max
    MESSAGE_QUEUE_SIZE = 1000
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Timeouts
    REQUEST_TIMEOUT = 10  # genel HTTP istek timeout
    WEBHOOK_TIMEOUT = 30
    
    # Cache
    ENABLE_CACHE = True
    CACHE_TTL = 300  # 5 dakika
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_REQUESTS_PER_MINUTE = 60
    RATE_LIMIT_BURST = 10


class DevelopmentConfig(Config):
    """Development konfigürasyonu"""
    DEBUG = True
    FLASK_ENV = "development"
    GEMINI_TIMEOUT = 60  # Daha uzun timeout development'te
    LOG_LEVEL = "DEBUG"


class ProductionConfig(Config):
    """Production konfigürasyonu"""
    DEBUG = False
    FLASK_ENV = "production"
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_REQUESTS_PER_MINUTE = 30
    LOG_LEVEL = "INFO"


class TestingConfig(Config):
    """Testing konfigürasyonu"""
    DEBUG = True
    TESTING = True
    DATABASE_URL = "sqlite:///:memory:"
    GEMINI_TIMEOUT = 5


# Mevcut konfigürasyonu seçer
config = DevelopmentConfig if Config.FLASK_ENV == "development" else ProductionConfig

# Gerekli API keys kontrolü
def validate_config():
    """Gerekli konfigürasyonları kontrol et"""
    required_keys = [
        "GEMINI_API_KEY",
        "WHATSAPP_API_TOKEN",
        "WHATSAPP_PHONE_ID",
    ]
    
    missing_keys = []
    for key in required_keys:
        if not getattr(Config, key):
            missing_keys.append(key)
    
    if missing_keys:
        print(f"⚠️  Uyarı: Aşağıdaki env keys eksik: {', '.join(missing_keys)}")
        print("   Lütfen .env dosyanızı kontrol edin")
    
    optional_keys = [
        "KOBI_API_BASE_URL",
        "KOBI_API_KEY",
        "MACK_KARGO_API_URL",
        "MACK_KARGO_API_KEY",
        "DATABASE_URL",
    ]
    
    print("\n📋 Opsiyonel konfigürasyonlar (kullanıcı sağlayacak):")
    for key in optional_keys:
        status = "✅ Ayarlanmış" if getattr(Config, key) else "⏳ Beklemede"
        print(f"   {key}: {status}")


if __name__ == "__main__":
    print("🔧 Bot Konfigürasyonu")
    print("=" * 50)
    print(f"Ortam: {config.FLASK_ENV}")
    print(f"Debug Mode: {config.DEBUG}")
    print(f"Port: {config.FLASK_PORT}")
    print(f"LLM Model: {config.GEMINI_MODEL}")
    print()
    validate_config()
