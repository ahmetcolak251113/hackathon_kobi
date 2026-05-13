"""
API Utilities
Harici API'lar (Mack Kargo, KOBI Backend) ile etkileşim
"""

import os
import logging
import requests
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# API Configuration
MACK_KARGO_API_URL = os.getenv("MACK_KARGO_API_URL", "http://127.0.0.1:8001")
# MACK_KARGO_API_KEY = os.getenv("MACK_KARGO_API_KEY", "")  # FastAPI JWT gerekirse

KOBI_API_BASE_URL = os.getenv("KOBI_API_BASE_URL", "http://127.0.0.1:3000")
# KOBI_API_KEY = os.getenv("KOBI_API_KEY", "")  # FastAPI JWT gerekirse

WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")

REQUEST_TIMEOUT = 10  # seconds


class MackKargoAPI:
    """Mack Kargo API işlemleri"""
    
    @staticmethod
    def get_shipment_status(phone_number: str, tracking_number: Optional[str] = None) -> Dict[str, Any]:
        """
        Kargo durumunu sorgula
        
        Args:
            phone_number: Müşteri telefon numarası (10 haneli)
            tracking_number: Takip numarası (opsiyonel)
        
        Returns:
            Kargo durumu bilgisi
            
        Expected Response:
        {
            "status": "in_transit",
            "current_location": "İstanbul Dağıtım Merkezi",
            "tracking_number": "MACK123456",
            "estimated_delivery": "2026-05-15",
            "last_update": "2026-05-10 14:30:00",
            "shipments": [
                {
                    "tracking_number": "MACK123456",
                    "status": "in_transit",
                    "current_location": "Ankara",
                    "estimated_delivery": "2026-05-16"
                }
            ]
        }
        """
        try:
            params = {"phone_number": phone_number}
            if tracking_number:
                params["tracking_number"] = tracking_number
            
            headers = {
                "Content-Type": "application/json"
                # API Key gerekirse: "Authorization": f"Bearer {MACK_KARGO_API_KEY}"
            }
            
            url = f"{MACK_KARGO_API_URL}/api/shipment/status"
            
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Mack Kargo status retrieved for {phone_number}")
            
            return result
        
        except requests.RequestException as e:
            logger.error(f"Mack Kargo API error: {e}")
            return {
                "error": True,
                "message": "Kargo durumu alınamadı",
                "details": str(e)
            }
    
    @staticmethod
    def track_package(tracking_number: str) -> Dict[str, Any]:
        """
        Spesifik paketi takip et
        
        Args:
            tracking_number: Kargo takip numarası
        
        Returns:
            Takip bilgileri
        """
        try:
            headers = {
                "Content-Type": "application/json"
                # API Key gerekirse: "Authorization": f"Bearer {MACK_KARGO_API_KEY}"
            }
            
            url = f"{MACK_KARGO_API_URL}/api/tracking/{tracking_number}"
            
            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Package tracked: {tracking_number}")
            
            return result
        
        except requests.RequestException as e:
            logger.error(f"Mack Kargo tracking error: {e}")
            return {
                "error": True,
                "message": "Takip numarası bulunamadı",
                "details": str(e)
            }


class KOBIBackendAPI:
    """KOBI Backend API işlemleri"""
    
    @staticmethod
    def search_product(kobi_id: str, product_name: str) -> Dict[str, Any]:
        """
        Ürün ara (Backend API)
        
        Args:
            kobi_id: KOBI ID'si
            product_name: Ürün adı veya parçası
        
        Returns:
            Ürün bilgileri
            
        Expected Response:
        {
            "product": {
                "id": "prod_123",
                "name": "Ürün Adı",
                "description": "Ürün açıklaması",
                "price": 99.99,
                "stock_quantity": 50,
                "unit": "piece",
                "sku": "SKU123"
            }
        }
        """
        try:
            headers = {
                "Content-Type": "application/json"
                # API Key gerekirse: "Authorization": f"Bearer {KOBI_API_KEY}"
            }
            
            url = f"{KOBI_API_BASE_URL}/api/products/search"
            payload = {
                "kobi_id": kobi_id,
                "product_name": product_name
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Product search: {product_name} in KOBI {kobi_id}")
            
            return result
        
        except requests.RequestException as e:
            logger.error(f"KOBI Backend API error: {e}")
            return {
                "error": True,
                "message": "Ürün bulunamadı",
                "details": str(e)
            }
    
    @staticmethod
    def get_customer_kobis(customer_phone: str) -> Dict[str, Any]:
        """
        Müşterinin ilişkili KOBI'lerini getir
        
        Args:
            customer_phone: Müşteri telefon numarası
        
        Returns:
            KOBI listesi
            
        Expected Response:
        {
            "kobis": [
                {
                    "id": "kobi_123",
                    "name": "KOBI Adı",
                    "phone": "5551234567",
                    "email": "kobi@example.com"
                }
            ]
        }
        """
        try:
            headers = {
                "Content-Type": "application/json"
                # API Key gerekirse: "Authorization": f"Bearer {KOBI_API_KEY}"
            }
            
            url = f"{KOBI_API_BASE_URL}/api/customers/{customer_phone}/kobis"
            
            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Customer KOBIs retrieved for {customer_phone}")
            
            return result
        
        except requests.RequestException as e:
            logger.error(f"KOBI Backend API error: {e}")
            return {
                "error": True,
                "message": "KOBI listesi alınamadı",
                "details": str(e)
            }
    
    @staticmethod
    def create_order(kobi_id: str, customer_phone: str, products: list) -> Dict[str, Any]:
        """
        Yeni sipariş oluştur
        
        Args:
            kobi_id: KOBI ID'si
            customer_phone: Müşteri telefon numarası
            products: Ürün listesi [{"product_id": "123", "quantity": 5}]
        
        Returns:
            Sipariş bilgileri
        """
        try:
            headers = {
                "Content-Type": "application/json"
                # API Key gerekirse: "Authorization": f"Bearer {KOBI_API_KEY}"
            }
            
            url = f"{KOBI_API_BASE_URL}/api/orders/create"
            payload = {
                "kobi_id": kobi_id,
                "customer_phone": customer_phone,
                "products": products
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Order created for customer {customer_phone}")
            
            return result
        
        except requests.RequestException as e:
            logger.error(f"KOBI Backend API error: {e}")
            return {
                "error": True,
                "message": "Sipariş oluşturulamadı",
                "details": str(e)
            }


class WhatsAppAPI:
    """WhatsApp Business API işlemleri"""
    
    @staticmethod
    def send_message(recipient_phone: str, message_text: str) -> bool:
        """
        WhatsApp mesajı gönder
        
        Args:
            recipient_phone: Alıcı telefon numarası
            message_text: Mesaj metni
        
        Returns:
            Başarılı mı
        """
        try:
            url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"
            
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_phone,
                "type": "text",
                "text": {
                    "body": message_text
                }
            }
            
            headers = {
                "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            
            response.raise_for_status()
            
            logger.info(f"WhatsApp message sent to {recipient_phone}")
            return True
        
        except requests.RequestException as e:
            logger.error(f"WhatsApp API error: {e}")
            return False
    
    @staticmethod
    def send_template_message(recipient_phone: str, template_name: str, parameters: dict) -> bool:
        """
        WhatsApp şablon mesajı gönder
        
        Args:
            recipient_phone: Alıcı telefon numarası
            template_name: Şablon adı
            parameters: Şablon parametreleri
        
        Returns:
            Başarılı mı
        """
        try:
            url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"
            
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_phone,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "tr"},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": str(p)} for p in parameters.values()
                            ]
                        }
                    ]
                }
            }
            
            headers = {
                "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            
            response.raise_for_status()
            
            logger.info(f"WhatsApp template message sent to {recipient_phone}")
            return True
        
        except requests.RequestException as e:
            logger.error(f"WhatsApp API error: {e}")
            return False
