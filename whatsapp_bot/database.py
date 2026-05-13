"""
Database Utilities (Opsiyonel)
Not: Şu anda FastAPI Backend API'larını kullanıyoruz.
Veritabanı ihtiyacı olursa, aşağıdaki placeholder'ları doldurun.

KOBI Database Architecture:
- Tablo 1: kobis (KOBI'ler)
- Tablo 2: products (Ürünler)
- Tablo 3: customers (Müşteriler)
- Tablo 4: customer_kobi (İlişkiler)
- Tablo 5: shipments (Siparişler)
"""

import os
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# DATABASE CONFIGURATION (Opsiyonel - şu anda API'lar kullanılıyor)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "kobi_db")
DB_USER = os.getenv("DB_USER", "kobi_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# DATABASE_URL format örneği:
# PostgreSQL: postgresql://user:password@localhost:5432/kobi_db
# MySQL: mysql+pymysql://user:password@localhost:3306/kobi_db
DB_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Not: Şu anda FastAPI Backend API'larını kullanıyoruz
# api_clients.py dosyasında KOBIBackendAPI ve MackKargoAPI sınıfları varsa
# Veritabanı gerek yok.


class KOBIDatabase:
    """
    KOBI veritabanı işlemleri sınıfı (Opsiyonel)
    
    ℹ️ Şu anda kullanılmıyor - FastAPI Backend API'larını kullanıyoruz
    
    Gerekli Tablolar (İleride):
    - kobis: KOBI'ler
      - id, name, phone, email, address
    - products: KOBI Ürünleri
      - id, kobi_id, name, price, stock_quantity, description
    - customers: Müşteriler
      - id, phone, name, email
    - customer_kobi: Müşteri-KOBI ilişkisi
      - customer_id, kobi_id
    - shipments: Siparişler/Kargolar
      - id, customer_id, kobi_id, tracking_number, status, created_at, estimated_delivery
    """
    
    def __init__(self):
        self.connection = None
        # ℹ️ Veritabanı bağlantısı şimdilik başlatılmıyor
        # Gerekirse: self._init_connection()
    
    def _init_connection(self):
        """
        Veritabanına bağlan
        
        TODO: İleride veritabanı gerekirse doldurun
        Örnek (PostgreSQL ile psycopg2):
        ```
        import psycopg2
        self.connection = psycopg2.connect(DB_URL)
        ```
        
        Örnek (MySQL ile pymysql):
        ```
        import pymysql
        self.connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        ```
        """
        pass
    
    def close_connection(self):
        """Bağlantıyı kapat"""
        if self.connection:
            self.connection.close()
    
    # Şimdilik tüm veriler FastAPI Backend API'larından geliyor
    # get_product() → KOBIBackendAPI.search_product() kullan
    # get_shipment_status() → MackKargoAPI.get_shipment_status() kullan
    # Detaylar: api_clients.py dosyasına bakın


# Global database instance
db = KOBIDatabase()


def get_db() -> KOBIDatabase:
    """Veritabanı instance'ını getir"""
    return db

