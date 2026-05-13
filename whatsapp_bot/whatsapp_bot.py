"""
WhatsApp KOBI Bot - Ana Orchestration
Müşteri mesajlarını alır, akışa göre işler ve gerektiğinde LLM'i sadece yorumlama/metin üretme için kullanır
"""

import os
import json
import logging
import sys
import datetime
import re
from typing import Optional, Any, Dict, List
from dotenv import load_dotenv
# Gemini/genai removed — using direct API calls only
from flask import Flask, request
import requests
 # genai/Gemini client removed — bot uses direct shipment endpoint


# Setup logging - stderr'e de yazacak
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

print("=" * 60, file=sys.stderr)
print("BOT BAŞLATILIYOR...", file=sys.stderr)
print("=" * 60, file=sys.stderr)

load_dotenv()
print(f"GEMINI_API_KEY loaded: {bool(os.getenv('GEMINI_API_KEY'))}", file=sys.stderr)
print(f"WHATSAPP_API_TOKEN loaded: {bool(os.getenv('WHATSAPP_API_TOKEN'))}", file=sys.stderr)
print(f"WHATSAPP_PHONE_ID: {os.getenv('WHATSAPP_PHONE_ID')}", file=sys.stderr)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "test_token")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Backend URLs (Placeholder - kullanıcı sağlayacak)
KOBI_API_BASE_URL = os.getenv("KOBI_API_BASE_URL", "http://localhost:3000")
MACK_KARGO_API_URL = os.getenv("MACK_KARGO_API_URL", "http://127.0.0.1:3000")
MACK_KARGO_API_KEY = os.getenv("MACK_KARGO_API_KEY")
WEBHOOK_DEBUG_ECHO = os.getenv("WEBHOOK_DEBUG_ECHO", "true").lower() in ("1", "true", "yes", "on")
DEFAULT_KOBI_ID = int(os.getenv("DEFAULT_KOBI_ID", "1"))

# No Gemini client initialized (we call shipment API directly)

app = Flask(__name__)

# Recent inbound message IDs to avoid duplicate replies when webhook is retried.
RECENT_MESSAGE_IDS: Dict[str, datetime.datetime] = {}
MESSAGE_DEDUP_WINDOW_SECONDS = int(os.getenv("MESSAGE_DEDUP_WINDOW_SECONDS", "180"))

# Simple in-memory conversation state keyed by phone number.
CONVERSATION_STATE: Dict[str, Dict[str, Any]] = {}


def should_process_message(message_id: Optional[str]) -> bool:
    if not message_id:
        # If message id is missing, process it to avoid dropping legitimate traffic.
        return True

    now = datetime.datetime.utcnow()
    expiry_cutoff = now - datetime.timedelta(seconds=MESSAGE_DEDUP_WINDOW_SECONDS)

    # Cleanup expired IDs.
    expired_ids = [msg_id for msg_id, seen_at in RECENT_MESSAGE_IDS.items() if seen_at < expiry_cutoff]
    for msg_id in expired_ids:
        RECENT_MESSAGE_IDS.pop(msg_id, None)

    if message_id in RECENT_MESSAGE_IDS:
        return False

    RECENT_MESSAGE_IDS[message_id] = now
    return True


def get_conversation_state(customer_phone: str) -> Dict[str, Any]:
    return CONVERSATION_STATE.get(customer_phone, {"state": "idle", "data": {}})


def set_conversation_state(customer_phone: str, state: str, data: Optional[Dict[str, Any]] = None) -> None:
    CONVERSATION_STATE[customer_phone] = {
        "state": state,
        "data": data or {},
        "updated_at": datetime.datetime.utcnow().isoformat(),
    }


def clear_conversation_state(customer_phone: str) -> None:
    CONVERSATION_STATE.pop(customer_phone, None)

# ============================
# API ve Mesaj Yardımcıları
# ============================


def _api_request_json(
    method: str,
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = 15,
) -> Any:
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)

    response = requests.request(
        method=method,
        url=url,
        headers=request_headers,
        params=params,
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()

    if not response.text.strip():
        return {}

    return response.json()


def _as_list(value: Any) -> List[Dict[str, Any]]:
    if isinstance(value, list):
        return value

    if isinstance(value, dict):
        for key in ("items", "data", "results", "products", "urunler", "customers", "orders", "shipments"):
            nested = value.get(key)
            if isinstance(nested, list):
                return nested

        for key in ("product", "urun", "order", "shipment"):
            nested = value.get(key)
            if isinstance(nested, dict):
                return [nested]

        return [value]

    return []


def _clean_query_text(text: str) -> str:
    return " ".join(text.lower().split())


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _auth_headers_for_cargo() -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if MACK_KARGO_API_KEY:
        headers["X-API-Key"] = MACK_KARGO_API_KEY
    return headers


def _extract_json_object(raw_text: str) -> Optional[Dict[str, Any]]:
    if not raw_text:
        return None

    start_idx = raw_text.find("{")
    end_idx = raw_text.rfind("}")
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        return None

    try:
        parsed = json.loads(raw_text[start_idx:end_idx + 1])
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        return None
    return None


def llm_interpret_message(message: str, state_name: str = "idle") -> Dict[str, Any]:
    """LLM'den intent ve kritik alanları JSON olarak alır; başarısız olursa boş döner."""
    if not GEMINI_API_KEY:
        return {}

    prompt = (
        "Sen bir WhatsApp asistanı için intent ve entity parser'sın. "
        "Kullanıcı yazım hatası yapsa da anlam çıkar. "
        "Sadece JSON döndür.\n\n"
        f"Mevcut state: {state_name}\n"
        f"Mesaj: {message}\n\n"
        "JSON şeması:\n"
        "{\n"
        '  "intent": "shipment_inquiry|product_inquiry|create_order|greeting|unknown",\n'
        '  "tracking_number": "string|null",\n'
        '  "shipment_lookup_method": "tracking|phone|unknown",\n'
        '  "items": [{"product_name": "string", "quantity": 1, "unit": "string|null"}],\n'
        '  "affirmation": true,\n'
        '  "negation": false,\n'
        '  "confidence": 0.0\n'
        "}\n"
    )

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }
        resp = requests.post(url, json=payload, timeout=12)
        resp.raise_for_status()
        data = resp.json()

        candidates = data.get("candidates") or []
        if not candidates:
            return {}
        parts = (((candidates[0] or {}).get("content") or {}).get("parts") or [])
        if not parts:
            return {}
        text = (parts[0] or {}).get("text", "")

        parsed = _extract_json_object(text)
        return parsed or {}
    except requests.RequestException as exc:
        logger.warning(f"LLM request failed, manual fallback active: {exc}")
        return {}


def _extract_tracking_candidate(message: str) -> Optional[str]:
    normalized = (message or "").strip()
    if not normalized:
        return None

    match = re.search(r"\b([A-Za-z0-9][A-Za-z0-9\-]{5,})\b", normalized)
    if not match:
        return None

    candidate = match.group(1).strip()
    if any(char.isdigit() for char in candidate):
        return candidate
    return None


def get_shipment_status(tracking_number: str) -> dict:
    """
    Tracking code ile kargo servisindeki /shipments/{tracking_code} endpoint'ine sorgu atar.
    """
    try:
        shipment = _api_request_json(
            "GET",
            f"{MACK_KARGO_API_URL}/shipments/{tracking_number}",
            headers=_auth_headers_for_cargo(),
        )
        return {"shipment": shipment}
    except requests.RequestException as e:
        logger.error(f"Kargo API error: {e}")
        return {"error": "Kargo durumu alınamadı", "details": str(e)}


def get_shipment_history(tracking_number: str) -> dict:
    headers = _auth_headers_for_cargo()
    try:
        history = _api_request_json(
            "GET",
            f"{MACK_KARGO_API_URL}/shipments/{tracking_number}/history",
            headers=headers,
        )
        return {"tracking_number": tracking_number, "history": history}
    except requests.RequestException as e:
        logger.error(f"Kargo history API error: {e}")
        return {
            "error": "Kargo geçmişi alınamadı",
            "details": str(e),
            "hint": "MACK_KARGO_API_KEY gerekiyorsa .env dosyasına ekle.",
        }


# No LLM tooling — direct API calls only


def build_debug_reply(message_text: str, customer_phone: str) -> str:
    """Eski test akışına benzer, doğrudan ve kısa bir yanıt üretir."""
    return (
        f"Mesajını aldım: {message_text}\n\n"
        f"Telefon: {customer_phone}\n"
        f"Durum: webhook çalışıyor"
    )


def build_intro_message() -> str:
    return (
        "Merhaba, ben *X KOBİ*'nin dijital asistanıyım.\n"
        "Size:\n- Ürün, fiyat bilgisi öğrenme\n- Sipariş verme\n- Kargo takibi\nkonularında yardımcı olabilirim."
    )


def build_shipment_menu_message() -> str:
    return (
        "Kargo durumunu kontrol etmek için takip numarasını yazabilirsiniz; takip numaranız yoksa siparişinizi telefon numaranızla da kontrol etmeye çalışırım."
    )


def build_order_help_message() -> str:
    return (
        "Siparişinizi doğal şekilde yazabilirsiniz; ürün adı, miktar ve varsa ek detayları ben ayıklamaya çalışırım."
    )


def build_order_confirmation_buttons() -> List[Dict[str, str]]:
    return [
        {"id": "btn_order_confirm_yes", "title": "Onaylıyorum"},
        {"id": "btn_order_confirm_no", "title": "Onaylamıyorum"},
    ]


def build_payment_buttons() -> List[Dict[str, str]]:
    return [
        {"id": "btn_payment_cash", "title": "Nakit"},
        {"id": "btn_payment_iban", "title": "IBAN"},
    ]


def build_shipment_lookup_buttons() -> List[Dict[str, str]]:
    return [
        {"id": "btn_shipment_lookup_tracking", "title": "Takip numarası ile"},
        {"id": "btn_shipment_lookup_phone", "title": "Telefon numarası ile"},
    ]


def build_clarification_message() -> str:
    return (
        "Bana istediğinizi doğal şekilde yazın, ben ne demek istediğinizi anlamaya çalışayım."
    )


def _normalize_message_text(message: str) -> str:
    return " ".join((message or "").strip().lower().split())


def is_phone_lookup_message(message: str) -> bool:
    normalized = _normalize_message_text(message)
    phone_keywords = (
        "telefon numaram",
        "telefon numarası",
        "telefonla dene",
        "numaramla dene",
        "telefonla kontrol et",
        "telefon numarasıyla kontrol et",
        "telefon numarası ile kontrol et",
        "telefon numaramla kontrol et",
        "numaramla kontrol et",
        "telefon numaram ile dene",
        "telefon numaramla bak",
        "telefon numarasıyla bak",
        "telefon numarası ile bak",
    )
    return any(keyword in normalized for keyword in phone_keywords)


def is_no_tracking_message(message: str) -> bool:
    normalized = _normalize_message_text(message)
    no_tracking_keywords = (
        "takip numaram yok",
        "takip numarası yok",
        "takip no yok",
        "takip kodum yok",
        "kargo takip numaram yok",
        "takip numarası bilmiyorum",
        "yok",
    )
    return normalized in no_tracking_keywords or any(keyword in normalized for keyword in no_tracking_keywords)


def is_greeting_message(message: str) -> bool:
    normalized = _normalize_message_text(message)
    if not normalized:
        return True

    greeting_keywords = ("selam", "merhaba", "slm", "hey", "hello", "günaydın", "iyi akşamlar", "iyi günler")
    return any(keyword in normalized for keyword in greeting_keywords)


def is_shipment_message(message: str) -> bool:
    normalized = _normalize_message_text(message)
    shipment_keywords = (
        "kargo",
        "takip",
        "takip numarası",
        "kargom",
        "siparişim ne durumda",
        "siparişim nerede",
        "siparişim yolda mı",
        "siparişim geldi mi",
        "siparişim durumu",
        "siparişimin durumu",
        "siparişim nerede",
        "nerede",
        "teslimat",
        "yolda mı",
        "ne durumda",
        "durumu nedir",
        "durumu",
    )
    return any(keyword in normalized for keyword in shipment_keywords) or _extract_tracking_candidate(message) is not None


def is_product_message(message: str) -> bool:
    normalized = _normalize_message_text(message)
    product_keywords = (
        "ürün",
        "fiyat",
        "satıyor",
        "satıyorsunuz",
        "var mı",
        "elinizde",
        "ne var",
        "stok",
    )
    return any(keyword in normalized for keyword in product_keywords)


def is_order_message(message: str) -> bool:
    normalized = _normalize_message_text(message)
    order_keywords = (
        "almak istiyorum",
        "alabilir miyim",
        "sipariş vermek",
        "sipariş etmek",
        "sipariş oluştur",
        "adet",
        "tane",
        "gönderir misiniz",
        "isterim",
        "istiyorum",
        "vermek istiyorum",
    )
    if any(keyword in normalized for keyword in order_keywords):
        return True

    quantity_match = re.search(r"\b\d+(?:[\.,]\d+)?\s*(?:kilo|kg|gram|gr|g|litre|lt|adet|tane|paket|şişe|sise|kutu)\b", normalized)
    return quantity_match is not None and not is_shipment_message(message)


def is_affirmative_message(message: str) -> bool:
    normalized = _normalize_message_text(message)
    return normalized in {
        "evet",
        "evet doğru anladın",
        "doğru",
        "doğru anladın",
        "onaylıyorum",
        "tamam",
        "olur",
        "aynen",
    }


def is_negative_message(message: str) -> bool:
    normalized = _normalize_message_text(message)
    return normalized in {
        "hayır",
        "hayir",
        "yanlış",
        "yanlis",
        "onaylamıyorum",
        "istemiyorum",
        "iptal",
        "vazgeçtim",
        "vazgectim",
    }


def is_cash_message(message: str) -> bool:
    normalized = _normalize_message_text(message)
    return normalized in {"nakit", "cash"}


def is_iban_message(message: str) -> bool:
    normalized = _normalize_message_text(message)
    return normalized in {"iban", "havale", "eft"}


def parse_order_request(message: str) -> Optional[Dict[str, Any]]:
    normalized = _normalize_message_text(message)
    if not normalized:
        return None

    if is_shipment_message(message):
        return None

    quantity_match = re.search(
        r"\b(?P<quantity>\d+(?:[\.,]\d+)?)\s*(?P<unit>kilo|kg|gram|gr|g|litre|litre|lt|adet|tane|kavanoz|paket|şişe|sise|kutu)?\b",
        normalized,
    )

    quantity = None
    unit = None
    remaining_text = normalized

    if quantity_match:
        raw_quantity = quantity_match.group("quantity").replace(",", ".")
        try:
            parsed_quantity = float(raw_quantity)
            quantity = int(parsed_quantity) if parsed_quantity.is_integer() else parsed_quantity
        except ValueError:
            quantity = None

        raw_unit = quantity_match.group("unit")
        if raw_unit:
            unit_aliases = {
                "kg": "kilo",
                "gr": "gram",
                "g": "gram",
                "lt": "litre",
                "sise": "şişe",
            }
            unit = unit_aliases.get(raw_unit, raw_unit)

        start, end = quantity_match.span()
        remaining_text = (normalized[:start] + " " + normalized[end:]).strip()

    cleaned_text = remaining_text
    for filler in (
        "siparişi vermek istiyorum",
        "sipariş vermek istiyorum",
        "sipariş istiyorum",
        "sipariş ne durumda",
        "siparişim ne durumda",
        "sipariş",
        "etmek",
        "vermek istiyorum",
        "almak istiyorum",
        "isterim",
        "istiyorum",
        "lütfen",
    ):
        cleaned_text = cleaned_text.replace(filler, " ")

    if unit:
        cleaned_text = re.sub(rf"\b{re.escape(unit)}\b", " ", cleaned_text)

    cleaned_text = re.sub(r"\b(?:adet|tane|kavanoz|kutu|paket|şişe|sise|kilo|kg|gram|gr|g|litre|lt)\b", " ", cleaned_text)

    cleaned_text = " ".join(cleaned_text.split())
    if not cleaned_text:
        return None

    return {
        "quantity": quantity,
        "unit": unit,
        "product_name": cleaned_text,
    }


def _extract_order_items_from_llm(message: str, llm_parse: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    parsed = llm_parse if isinstance(llm_parse, dict) else {}
    raw_items = parsed.get("items") if isinstance(parsed, dict) else None
    normalized_items: List[Dict[str, Any]] = []

    if isinstance(raw_items, list):
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            product_name = _first_present(
                raw_item.get("product_name"),
                raw_item.get("name"),
                raw_item.get("urun_adi"),
                raw_item.get("ad"),
                raw_item.get("title"),
            )
            if not product_name:
                continue

            quantity = _first_present(raw_item.get("quantity"), raw_item.get("adet"), raw_item.get("count"), raw_item.get("qty"))
            unit = _first_present(raw_item.get("unit"), raw_item.get("birim"), raw_item.get("measurement_unit"))

            if quantity is None:
                quantity = 1

            try:
                quantity_value = float(quantity)
                quantity = int(quantity_value) if quantity_value.is_integer() else quantity_value
            except (TypeError, ValueError):
                quantity = 1

            normalized_items.append({
                "product_name": str(product_name).strip(),
                "quantity": quantity,
                "unit": unit,
            })

    if normalized_items:
        return normalized_items

    fallback_segments = [segment.strip() for segment in re.split(r"[,;\n]+|\s+ve\s+", message or "", flags=re.IGNORECASE) if segment.strip()]
    for segment in fallback_segments:
        parsed_segment = parse_order_request(segment)
        if parsed_segment:
            normalized_items.append(parsed_segment)

    return normalized_items


def _normalize_product_text(text: str) -> str:
    normalized = _normalize_message_text(text)
    normalized = normalized.replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c")
    for filler in ("etmek", "ediyorum", "istiyorum", "siparis", "siparisi", "tane", "adet"):
        normalized = normalized.replace(f" {filler} ", " ")
    return " ".join(normalized.split())


def _normalize_stock_value(stock: Any) -> Optional[float]:
    if isinstance(stock, (int, float)):
        return float(stock)
    if isinstance(stock, str):
        stock_value = stock.strip().lower().replace(",", ".")
        try:
            return float(stock_value)
        except ValueError:
            return None
    return None


def match_catalog_product(query_text: str, catalog: Any) -> Optional[Dict[str, Any]]:
    products = _as_list(catalog)
    if not products:
        return None

    query_normalized = _normalize_product_text(query_text)
    query_tokens = [token for token in query_normalized.split() if len(token) > 1]
    best_match: Optional[Dict[str, Any]] = None
    best_score = 0

    for product in products:
        name = str(
            _first_present(
                product.get("name"),
                product.get("urun_adi"),
                product.get("product_name"),
                product.get("title"),
                product.get("ad"),
            )
            or ""
        )
        if not name:
            continue

        name_normalized = _normalize_product_text(name)
        name_tokens = [token for token in name_normalized.split() if len(token) > 1]

        score = 0
        if query_normalized == name_normalized:
            score += 100
        elif query_normalized in name_normalized or name_normalized in query_normalized:
            score += 70

        shared_tokens = set(query_tokens).intersection(name_tokens)
        score += len(shared_tokens) * 15

        if query_tokens and name_tokens:
            first_query = query_tokens[0]
            first_name = name_tokens[0]
            if first_query == first_name:
                score += 10

        if score > best_score:
            best_score = score
            best_match = product

    return best_match if best_score >= 20 else None


def format_product_order_confirmation(product: Dict[str, Any], order_data: Dict[str, Any]) -> str:
    name = str(
        _first_present(
            product.get("name"),
            product.get("urun_adi"),
            product.get("product_name"),
            product.get("title"),
            product.get("ad"),
        )
        or order_data.get("product_name")
    )

    price = _first_present(
        product.get("satis_fiyati"),
        product.get("satış_fiyatı"),
        product.get("price"),
        product.get("fiyat"),
        product.get("unit_price"),
        product.get("sale_price"),
    )
    stock = _normalize_stock_value(
        _first_present(
            product.get("stok_miktari"),
            product.get("stok_miktarı"),
            product.get("stock"),
            product.get("stock_quantity"),
            product.get("stok"),
            product.get("quantity"),
        )
    )
    product_unit = _first_present(
        product.get("birim"),
        product.get("unit"),
        product.get("measurement_unit"),
    )

    quantity = order_data.get("quantity")
    unit = order_data.get("unit") or product_unit
    stock_text = None
    if stock is not None:
        amount_text = int(stock) if float(stock).is_integer() else stock
        stock_text = f"{amount_text} {product_unit}".strip() if product_unit else str(amount_text)

    if stock is not None and stock <= 0:
        stock_suffix = f" Mevcut stok: {stock_text}." if stock_text else ""
        return f"Maalesef {name} şu anda stokta yok.{stock_suffix}"

    if stock is not None and quantity is not None and stock < float(quantity):
        stock_suffix = f" Mevcut stok: {stock_text}." if stock_text else ""
        return (
            f"Maalesef {name} için yeterli stok yok.{stock_suffix}\n"
            f"İstediğiniz miktar: {quantity} {unit or 'adet'}"
        )

    parts = [f"{name} için sipariş vermek istiyor musunuz?"]
    if quantity is not None:
        if unit:
            parts.append(f"Miktar: {quantity} {unit}")
        else:
            parts.append(f"Miktar: {quantity} adet")
    if price is not None and str(price).strip() != "":
        parts.append(f"Fiyat: ₺{str(price).strip().removeprefix('₺')}")

    parts.append("Onaylarsanız siparişi ilerletebilirim.")
    return "\n".join(parts)


def format_order_summary(order_data: Dict[str, Any]) -> str:
    items = order_data.get("items")
    if isinstance(items, list) and items:
        return format_order_summary_for_items(items)

    quantity = order_data.get("quantity")
    unit = order_data.get("unit")
    product_name = order_data.get("product_name") or "ürün"

    parts = ["Siparişinizi anladım:"]

    if quantity is not None:
        if unit:
            parts.append(f"- {quantity} {unit} {product_name}")
        else:
            parts.append(f"- {quantity} adet {product_name}")
    else:
        parts.append(f"- {product_name}")

    parts.append("")
    parts.append("Bu doğruysa devam edebilirim; yanlışsa ürün adını veya miktarı tek cümlede düzeltebilirsiniz.")
    return "\n".join(parts)


def format_order_summary_for_items(items: List[Dict[str, Any]]) -> str:
    lines = ["Siparişinizi anladım:"]
    for item in items:
        product_name = item.get("matched_product_name") or item.get("product_name") or "ürün"
        quantity = item.get("quantity")
        unit = item.get("unit")

        if quantity is not None:
            if unit:
                lines.append(f"- {quantity} {unit} {product_name}")
            else:
                lines.append(f"- {quantity} adet {product_name}")
        else:
            lines.append(f"- {product_name}")

    lines.append("")
    lines.append("Bu doğruysa devam edebilirim; yanlışsa ürünleri tek mesajda düzeltebilirsiniz.")
    return "\n".join(lines)


def _extract_stock_value(product: Dict[str, Any]) -> Optional[float]:
    return _normalize_stock_value(
        _first_present(
            product.get("stok_miktari"),
            product.get("stok_miktarı"),
            product.get("stock"),
            product.get("stock_quantity"),
            product.get("stok"),
            product.get("quantity"),
        )
    )


def extract_tracking_number(message: str) -> Optional[str]:
    import re

    normalized = (message or "").strip()
    match = re.search(r"\b([A-Za-z0-9][A-Za-z0-9\-]{5,})\b", normalized)
    if match:
        candidate = match.group(1).strip()
        if any(char.isdigit() for char in candidate):
            return candidate
    return None


def get_product_catalog() -> Any:
    try:
        return _api_request_json("GET", f"{KOBI_API_BASE_URL}/api/urunler")
    except requests.RequestException as e:
        logger.error(f"Product catalog error: {e}")
        return {"error": "Ürün listesi alınamadı", "details": str(e)}


def format_product_catalog(catalog: Any) -> str:
    products = _as_list(catalog)
    if not products:
        return (
            "Şu anda ürün listesini alamadım.\n"
            "Lütfen almak istediğiniz ürünü ve adedini yazın."
        )

    available_lines: List[str] = []
    out_of_stock_lines: List[str] = []

    for product in products[:5]:
        name = (
            _first_present(
                product.get("name"),
                product.get("urun_adi"),
                product.get("product_name"),
                product.get("title"),
                product.get("ad"),
            )
            or "Ürün"
        )
        price = _first_present(
            product.get("satis_fiyati"),
            product.get("satış_fiyatı"),
            product.get("price"),
            product.get("fiyat"),
            product.get("unit_price"),
            product.get("sale_price"),
        )
        stock = _first_present(
            product.get("stok_miktari"),
            product.get("stok_miktarı"),
            product.get("stock"),
            product.get("stock_quantity"),
            product.get("stok"),
            product.get("quantity"),
        )
        available = _first_present(product.get("available"), product.get("is_available"))
        status = str(_first_present(product.get("status"), product.get("durum"), product.get("availability")) or "").strip().lower()

        parts = [f"- {name}"]

        if price is not None and str(price).strip() != "":
            price_text = str(price).strip()
            if not price_text.startswith("₺"):
                price_text = f"₺{price_text}"
            parts.append(price_text)

        is_out_of_stock = False
        if isinstance(stock, (int, float)):
            is_out_of_stock = stock <= 0
        elif isinstance(stock, str):
            stock_value = stock.strip().lower()
            if stock_value in {"stokta yok", "stok yok", "yok", "false", "none"}:
                is_out_of_stock = True
            else:
                try:
                    is_out_of_stock = float(stock_value.replace(",", ".")) <= 0
                except ValueError:
                    is_out_of_stock = False
        elif isinstance(available, bool):
            is_out_of_stock = not available
        elif status:
            is_out_of_stock = status in {"out_of_stock", "stokta yok", "stok yok", "unavailable", "false", "0"}

        if is_out_of_stock:
            parts.append("Stokta yok")
            out_of_stock_lines.append(" | ".join(parts))
        else:
            available_lines.append(" | ".join(parts))

    lines = ["Satıştaki ürünlerimiz:"]
    if available_lines:
        lines.extend(available_lines)
    if out_of_stock_lines:
        if available_lines:
            lines.append("")
        lines.append("Stokta olmayan ürünler:")
        lines.extend(out_of_stock_lines)

    lines.append("")
    lines.append("İsterseniz ürün adı ve adetini yazın, size yardımcı olayım.")
    return "\n".join(lines)


def get_shipment_by_phone(phone_number: str) -> Any:
    try:
        return _api_request_json("GET", f"{MACK_KARGO_API_URL}/shipments/by-phone/{phone_number}", headers=_auth_headers_for_cargo())
    except requests.RequestException as e:
        logger.error(f"Shipment lookup by phone error: {e}")
        return {"error": "Kargo bilgisi alınamadı", "details": str(e)}


def _format_datetime_for_user(value: Any) -> str:
    if not value:
        return "Bilinmiyor"

    if isinstance(value, datetime.datetime):
        dt = value
    elif isinstance(value, datetime.date):
        dt = datetime.datetime.combine(value, datetime.time.min)
    elif isinstance(value, str):
        raw = value.strip()
        try:
            dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return raw
    else:
        return str(value)

    return dt.replace(tzinfo=None).strftime("%d.%m.%Y %H:%M")


def _format_shipment_products(item: Dict[str, Any]) -> List[str]:
    raw_items = _first_present(
        item.get("items"),
        item.get("urunler"),
        item.get("products"),
        item.get("order_items"),
        item.get("shipment_items"),
    )

    if not isinstance(raw_items, list):
        return []

    lines: List[str] = []
    for product in raw_items:
        if not isinstance(product, dict):
            continue

        product_name = _first_present(
            product.get("custom_product_name"),
            product.get("product_name"),
            product.get("urun_adi"),
            product.get("name"),
            product.get("ad"),
            product.get("title"),
        )
        quantity = _first_present(
            product.get("quantity"),
            product.get("adet"),
            product.get("miktar"),
            product.get("qty"),
            product.get("count"),
        )
        unit = _first_present(
            product.get("unit"),
            product.get("birim"),
            product.get("measurement_unit"),
        )

        if product_name is None:
            continue

        name_text = str(product_name).strip()
        if not name_text:
            continue

        if quantity is not None:
            try:
                quantity_float = float(quantity)
                quantity_text = str(int(quantity_float)) if quantity_float.is_integer() else str(quantity_float)
            except (ValueError, TypeError):
                quantity_text = str(quantity)

            if unit:
                lines.append(f"- {name_text}: {quantity_text} {unit}")
            else:
                lines.append(f"- {name_text}: {quantity_text} adet")
        else:
            lines.append(f"- {name_text}")

    return lines


def _format_shipment_item(item: Dict[str, Any], tracking_number: Optional[str] = None) -> str:
    status = item.get("status_text") or item.get("status") or item.get("current_status") or item.get("state") or "Bilinmiyor"
    location = item.get("location") or item.get("current_location") or item.get("last_location") or "Bilinmiyor"
    eta_raw = item.get("estimated_delivery") or item.get("eta") or item.get("expected_delivery")
    eta = _format_datetime_for_user(eta_raw)
    delay_reason = item.get("delay_reason")
    resolved_tracking = tracking_number or item.get("tracking_code") or item.get("tracking_number") or item.get("trackingCode") or "Bilinmiyor"
    product_lines = _format_shipment_products(item)

    lines = [
        "*Kargo Bilgisi:*",
        f"- Takip No: {resolved_tracking}",
        f"- Durum: {status}",
        f"- Konum: {location}",
        f"- Tahmini teslim: {eta}",
    ]
    if delay_reason:
        lines.append(f"- Gecikme nedeni: {delay_reason}")
    if product_lines:
        lines.append("*Siparişteki ürünler:*")
        lines.extend(product_lines)
    return "\n".join(lines)


def _shipment_sort_timestamp(item: Dict[str, Any]) -> datetime.datetime:
    candidate_fields = (
        item.get("updated_at"),
        item.get("updatedAt"),
        item.get("visible_at"),
        item.get("visibleAt"),
        item.get("created_at"),
        item.get("createdAt"),
        item.get("estimated_delivery"),
        item.get("eta"),
        item.get("expected_delivery"),
    )

    for value in candidate_fields:
        if not value:
            continue
        if isinstance(value, datetime.datetime):
            return value.replace(tzinfo=None)
        if isinstance(value, datetime.date):
            return datetime.datetime.combine(value, datetime.time.min)
        if isinstance(value, str):
            candidate = value.strip().replace("Z", "+00:00")
            for parser in (datetime.datetime.fromisoformat,):
                try:
                    parsed_value = parser(candidate)
                    return parsed_value.replace(tzinfo=None)
                except ValueError:
                    continue

    return datetime.datetime.min


def _latest_shipment_item(items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not items:
        return None
    return max(items, key=_shipment_sort_timestamp)


def build_tracking_fallback_message(tracking_number: str, shipment_result: Any) -> str:
    if isinstance(shipment_result, dict) and shipment_result.get("error"):
        return (
            f"Bu takip numarasıyla kargo bilgisine ulaşamadım: {tracking_number}.\n"
            "Telefon numaranızla da kontrol etmeye çalıştım ama kayıt bulamadım.\n"
            "Lütfen takip numarasını kontrol eder misiniz?"
        )

    formatted_shipment = format_shipment_response(shipment_result, tracking_number=tracking_number)
    if formatted_shipment.startswith("Kargo bilgisine ulaşamadım"):
        return (
            f"Bu takip numarasıyla kargo bilgisine ulaşamadım: {tracking_number}.\n"
            "Telefon numaranızla da kontrol etmeye çalıştım.\n"
            "Şu kargo sizin miydi?\n\n"
            f"{formatted_shipment}"
        )

    return (
        f"Bu takip numarasıyla kargo bilgisine ulaşamadım: {tracking_number}.\n"
        "Telefon numaranızla da kontrol etmeye çalıştım.\n"
        "Şu kargo sizin miydi?\n\n"
        f"{formatted_shipment}"
    )


def build_phone_lookup_confirmation_message(shipment_result: Any) -> str:
    if isinstance(shipment_result, dict) and shipment_result.get("error"):
        return "Telefon numaranızla kargo kaydı bulamadım. Takip numaranızı paylaşırsanız daha net kontrol edebilirim."

    formatted_shipment = format_shipment_response(shipment_result)
    if formatted_shipment.startswith("Telefon numaranızla eşleşen bir kargo bulamadım"):
        return "Telefon numaranızla eşleşen bir kargo bulamadım. Takip numaranızı paylaşırsanız daha net kontrol edebilirim."

    return (
        "Takip numarası olmadan telefon numaranız üzerinden eşleşen en son kargo kaydını kontrol ettim.\n"
        "Bu kayıt sizin kargonuz olabilir:\n\n"
        f"{formatted_shipment}"
    )


def format_shipment_response(shipment: Any, tracking_number: Optional[str] = None) -> str:
    if isinstance(shipment, dict) and shipment.get("error"):
        return "Bu takip numarasıyla kargo bilgisine ulaşamadım. Lütfen takip numarasını kontrol eder misiniz?"

    if isinstance(shipment, list):
        if not shipment:
            return "Telefon numaranızla eşleşen bir kargo bulamadım."
        if len(shipment) == 1:
            first_item = shipment[0] if isinstance(shipment[0], dict) else {"status_text": str(shipment[0])}
            return _format_shipment_item(first_item, tracking_number=tracking_number)

        dict_items = [item for item in shipment if isinstance(item, dict)]
        latest_item = _latest_shipment_item(dict_items)
        if latest_item:
            return _format_shipment_item(latest_item, tracking_number=tracking_number)

        lines = ["Telefon numaranızla bulunan kargolar:"]
        for item in shipment[:3]:
            if isinstance(item, dict):
                item_tracking = item.get("tracking_code") or item.get("tracking_number") or item.get("trackingCode") or "Bilinmiyor"
                item_status = item.get("status_text") or item.get("status") or item.get("current_status") or item.get("state") or "Bilinmiyor"
                item_location = item.get("location") or item.get("current_location") or item.get("last_location") or "Bilinmiyor"
                lines.append(f"- {item_tracking} | {item_status} | {item_location}")
        return "\n".join(lines)

    if isinstance(shipment, dict):
        data = shipment.get("shipment") or shipment.get("data") or shipment
        if isinstance(data, dict):
            return _format_shipment_item(data, tracking_number=tracking_number)

    return "Kargo bilgisine ulaşamadım. Lütfen takip numarasını kontrol eder misiniz?"


def send_whatsapp_interactive_buttons(recipient_phone: str, body_text: str, buttons: List[Dict[str, str]]) -> bool:
    try:
        if not WHATSAPP_API_TOKEN or not WHATSAPP_PHONE_ID:
            logger.error("WhatsApp token veya phone id eksik")
            return False

        url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": button["id"], "title": button["title"]},
                        }
                        for button in buttons[:3]
                    ]
                },
            },
        }

        headers = {
            "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
            "Content-Type": "application/json",
        }
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error(f"WhatsApp interactive send failed: {e}")
        return False


# ============================
# Mesaj Yorumlama Akışı
# ============================

def process_customer_message(customer_phone: str, message: str, kobi_id: Optional[str] = None) -> str:
    """
    Müşteri mesajını temel bir yorumlama akışıyla işle.
    
    Args:
        customer_phone: Müşteri telefon numarası
        message: Müşteri mesajı
        kobi_id: KOBI ID (opsiyonel)
    
    Returns:
        Üretilen kısa cevap
    """
    
    try:
        current_state = get_conversation_state(customer_phone)
        state_name = current_state.get("state", "idle")
        llm_parse = llm_interpret_message(message, state_name=state_name)

        llm_tracking_number = llm_parse.get("tracking_number") if isinstance(llm_parse, dict) else None
        tracking_number = llm_tracking_number or _extract_tracking_candidate(message)

        llm_lookup_method = str(llm_parse.get("shipment_lookup_method", "unknown")).strip().lower() if isinstance(llm_parse, dict) else "unknown"
        llm_intent = str(llm_parse.get("intent", "unknown")).strip().lower() if isinstance(llm_parse, dict) else "unknown"

        phone_lookup_requested = llm_lookup_method == "phone" or is_phone_lookup_message(message)
        no_tracking_requested = is_no_tracking_message(message)
        tracking_lookup_requested = llm_lookup_method == "tracking"
        shipment_intent_detected = llm_intent == "shipment_inquiry" or is_shipment_message(message)

        if tracking_number or shipment_intent_detected:
            if state_name in {"waiting_order_confirmation", "waiting_payment_method"}:
                clear_conversation_state(customer_phone)

            if not tracking_number:
                if phone_lookup_requested or no_tracking_requested:
                    clear_conversation_state(customer_phone)
                    phone_lookup_result = get_shipment_by_phone(customer_phone)
                    return build_phone_lookup_confirmation_message(phone_lookup_result)

                set_conversation_state(customer_phone, "waiting_shipment_lookup_method", {})
                return "Kargo durumunu hangi yöntemle kontrol edelim?"

            if tracking_lookup_requested and not tracking_number:
                set_conversation_state(customer_phone, "waiting_shipment_tracking", {})
                return (
                    "Kargo durumunu net kontrol etmem için takip numarasını paylaşabilir misiniz?\n"
                    "Takip numaranız yoksa 'telefon numaramla kontrol et' yazabilirsiniz."
                )

            tool_result = get_shipment_status(tracking_number=tracking_number)
            if isinstance(tool_result, dict) and tool_result.get("error"):
                phone_lookup_result = get_shipment_by_phone(customer_phone)
                if isinstance(phone_lookup_result, dict) and phone_lookup_result.get("error"):
                    return build_tracking_fallback_message(tracking_number, phone_lookup_result)
                return build_tracking_fallback_message(tracking_number, phone_lookup_result)

            clear_conversation_state(customer_phone)
            return format_shipment_response(tool_result, tracking_number=tracking_number)

        if state_name == "waiting_shipment_tracking":
            tracking_number = _extract_tracking_candidate(message)
            if tracking_number:
                tool_result = get_shipment_status(tracking_number=tracking_number)
                if isinstance(tool_result, dict) and tool_result.get("error"):
                    phone_lookup_result = get_shipment_by_phone(customer_phone)
                    if isinstance(phone_lookup_result, dict) and phone_lookup_result.get("error"):
                        return build_tracking_fallback_message(tracking_number, phone_lookup_result)
                    return build_tracking_fallback_message(tracking_number, phone_lookup_result)
                clear_conversation_state(customer_phone)
                return format_shipment_response(tool_result, tracking_number=tracking_number)

            if phone_lookup_requested or no_tracking_requested:
                clear_conversation_state(customer_phone)
                phone_lookup_result = get_shipment_by_phone(customer_phone)
                return build_phone_lookup_confirmation_message(phone_lookup_result)

            return (
                "Takip numarasını paylaşabilir misiniz?\n"
                "Takip numaranız yoksa 'telefon numaramla kontrol et' yazın, telefon kaydınızdan bakayım."
            )

        if state_name == "waiting_shipment_lookup_method":
            if phone_lookup_requested or no_tracking_requested:
                clear_conversation_state(customer_phone)
                phone_lookup_result = get_shipment_by_phone(customer_phone)
                return build_phone_lookup_confirmation_message(phone_lookup_result)

            if tracking_number or tracking_lookup_requested:
                if tracking_number:
                    tool_result = get_shipment_status(tracking_number=tracking_number)
                    if isinstance(tool_result, dict) and tool_result.get("error"):
                        phone_lookup_result = get_shipment_by_phone(customer_phone)
                        return build_tracking_fallback_message(tracking_number, phone_lookup_result)
                    clear_conversation_state(customer_phone)
                    return format_shipment_response(tool_result, tracking_number=tracking_number)

                set_conversation_state(customer_phone, "waiting_shipment_tracking", {})
                return "Takip numaranızı paylaşır mısınız?"

            set_conversation_state(customer_phone, "waiting_shipment_lookup_method", {})
            return "Kargo sorgusu için 'takip numarası ile' veya 'telefon numarası ile' tercih edebilirsiniz."

        if state_name == "waiting_order_confirmation":
            if is_affirmative_message(message):
                pending_order = current_state.get("data", {}).get("pending_order", {})
                set_conversation_state(customer_phone, "waiting_payment_method", {"pending_order": pending_order})
                return (
                    "Anladım. Ödeme yöntemini seçebilirsiniz: nakit veya IBAN."
                )

            if is_negative_message(message):
                clear_conversation_state(customer_phone)
                return build_intro_message()

            return (
                "Siparişi tamamlamak için lütfen onaylayın veya onaylamadığınızı belirtin."
            )

        if state_name == "waiting_payment_method":
            if is_cash_message(message) or is_iban_message(message):
                pending = current_state.get("data", {}) or {}
                # pending may be {'pending_order': {...}} or the pending_order directly
                pending_order = pending.get("pending_order") if isinstance(pending, dict) and pending.get("pending_order") else pending

                # Post to KOBI panel
                result = post_order_to_kobi(customer_phone, pending_order)

                clear_conversation_state(customer_phone)

                if isinstance(result, dict) and result.get("siparis_id"):
                    return f"Ödeme seçimi kaydedildi. Sipariş talebiniz oluşturuldu (ID: {result.get('siparis_id')})." 
                if isinstance(result, dict) and result.get("mesaj") and not result.get("error"):
                    return f"Ödeme seçimi kaydedildi. {result.get('mesaj')}"
                return "Ödeme seçiminiz alındı fakat sipariş oluşturulurken bir sorun oldu. Lütfen daha sonra tekrar deneyin."

            if is_affirmative_message(message):
                return "Lütfen ödeme yöntemini seçin: Nakit veya IBAN"

        if is_greeting_message(message) and not tracking_number:
            return build_intro_message()

        if is_product_message(message):
            catalog = get_product_catalog()
            return format_product_catalog(catalog)

        if is_order_message(message):
            catalog = get_product_catalog()
            parsed_items = _extract_order_items_from_llm(message, llm_parse if isinstance(llm_parse, dict) else None)

            if not parsed_items:
                parsed_order = parse_order_request(message)
                if parsed_order:
                    parsed_items = [parsed_order]

            if parsed_items:
                resolved_items: List[Dict[str, Any]] = []
                unavailable_lines: List[str] = []

                for parsed_item in parsed_items:
                    matched_product = match_catalog_product(parsed_item.get("product_name", message), catalog)

                    if not matched_product:
                        unavailable_lines.append(f"- {parsed_item.get('product_name', 'ürün')}: katalogda net eşleşme bulunamadı")
                        continue

                    stock_value = _extract_stock_value(matched_product)
                    product_name = _first_present(
                        matched_product.get("name"),
                        matched_product.get("urun_adi"),
                        matched_product.get("product_name"),
                        matched_product.get("title"),
                        matched_product.get("ad"),
                    ) or parsed_item.get("product_name")

                    if stock_value is not None and stock_value <= 0:
                        unavailable_lines.append(f"- {product_name}: şu anda stokta yok")
                        continue

                    quantity = parsed_item.get("quantity")
                    if stock_value is not None and quantity is not None and stock_value < float(quantity):
                        unavailable_lines.append(
                            f"- {product_name}: yeterli stok yok (mevcut: {int(stock_value) if float(stock_value).is_integer() else stock_value})"
                        )
                        continue

                    resolved_item = {
                        **parsed_item,
                        "matched_product": matched_product,
                        "matched_product_name": product_name,
                        "product_name": product_name,
                    }
                    resolved_items.append(resolved_item)

                if unavailable_lines:
                    if resolved_items:
                        return (
                            "Bazı ürünleri onaya hazır hale getirdim, bazıları için sorun var:\n"
                            + "\n".join(unavailable_lines)
                            + "\n\nLütfen sorunlu ürünleri düzeltip tekrar yazın."
                        )

                    catalog_text = format_product_catalog(catalog)
                    return (
                        "İstediğiniz ürünleri katalogda net eşleştiremedim. Lütfen ürün adlarını biraz daha açık yazın.\n\n"
                        f"{catalog_text}"
                    )

                if resolved_items:
                    pending_order = {
                        "items": resolved_items,
                        "raw_message": message,
                    }
                    set_conversation_state(customer_phone, "waiting_order_confirmation", {"pending_order": pending_order})
                    return format_order_summary_for_items(resolved_items)

            return build_clarification_message()

        return build_clarification_message()

    except Exception as e:
        logger.error(f"❌ Process error: {e}", exc_info=True)
        return "Bir hata oluştu. Lütfen tekrar deneyin."


# ============================
# WhatsApp Webhook
# ============================

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    """WhatsApp webhook endpoint"""
    print(f"\n{'='*60}", flush=True)
    print(f"🔔 WEBHOOK {request.method} received at {datetime.datetime.now()}", flush=True)
    print(f"{'='*60}\n", flush=True)
    logger.info(f"🔔 WEBHOOK {request.method} received")
    
    if request.method == "GET":
        # Verification
        verify_token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        logger.info(f"GET /webhook - Token provided: {'Yes' if verify_token else 'No'}")
        
        # Eğer hiç token gelmemişse, bilgi sayfası göster (HTTP 200)
        if not verify_token or not challenge:
            html_response = f"""
            <html>
            <head><title>WhatsApp Bot Webhook</title></head>
            <body style="font-family: Arial;">
                <h1>✅ WhatsApp Webhook Endpoint Aktif</h1>
                <p>Bu endpoint Meta tarafından WhatsApp mesajlarını almak için kullanılır.</p>
                <hr>
                <h3>Meta Webhook Ayarlanması:</h3>
                <ul>
                    <li><strong>Webhook URL:</strong> https://embryogenic-untameable-kenia.ngrok-free.dev/webhook</li>
                    <li><strong>Verify Token:</strong> test_token</li>
                    <li><strong>Subscribe:</strong> messages, message_status</li>
                </ul>
                <hr>
                <h3>Test:</h3>
                <a href="/webhook?hub.verify_token=test_token&hub.challenge=test123">Webhook Doğrulama Linki</a>
            </body>
            </html>
            """
            return html_response, 200
        
        # Token doğrula
        if verify_token == VERIFY_TOKEN:
            logger.info("✅ Webhook verification successful!")
            return challenge, 200
        else:
            logger.warning(f"❌ Token mismatch. Got: {verify_token}, Expected: {VERIFY_TOKEN}")
            return "Invalid verify token", 403
    
    elif request.method == "POST":
        print("\n📬 WEBHOOK POST RECEIVED", flush=True)
        print(f"Raw data: {request.data}", flush=True)
        print(f"Content-Type: {request.content_type}", flush=True)
        logger.info("=" * 60)
        logger.info("📬 WEBHOOK POST RECEIVED")
        logger.info(f"Headers: {dict(request.headers)}")
        
        try:
            body = request.get_json(silent=True)
            print(f"Parsed JSON: {body}", flush=True)
            logger.info(f"Body: {json.dumps(body, ensure_ascii=False, indent=2)}")
        except Exception as e:
            print(f"JSON parse error: {e}", flush=True)
            logger.error(f"JSON parse error: {e}")
            body = {}
        
        # WhatsApp mesajı işle
        try:
            if body and body.get("object") == "whatsapp_business_account":
                logger.info("✅ WhatsApp business account payload received")
                entries = body.get("entry", [])
                
                for entry in entries:
                    changes = entry.get("changes", [])
                    
                    for change in changes:
                        value = change.get("value", {})
                        messages = value.get("messages", [])
                        statuses = value.get("statuses", [])

                        if statuses:
                            logger.info(f"📡 Found {len(statuses)} status update(s)")
                            logger.info(f"Status payload: {json.dumps(statuses, ensure_ascii=False, indent=2)}")
                        
                        if messages:
                            logger.info(f"📨 Found {len(messages)} message(s)")
                            print(f"📨 Found {len(messages)} message(s)", flush=True)
                        
                        for message in messages:
                            customer_phone = message.get("from")
                            message_type = message.get("type")
                            message_id = message.get("id")

                            if not should_process_message(message_id):
                                logger.info(f"⏭️ Duplicate message skipped. id={message_id}, from={customer_phone}")
                                print(f"⏭️ Duplicate message skipped. id={message_id}", flush=True)
                                continue
                            
                            print(f"Message type: {message_type}, From: {customer_phone}", flush=True)
                            logger.info(f"Message type: {message_type}, From: {customer_phone}")
                            
                            if message_type == "text":
                                message_text = message.get("text", {}).get("body", "")
                                
                                print(f"✉️  Message from {customer_phone}: {message_text}", flush=True)
                                logger.info(f"✉️  Message from {customer_phone}: {message_text}")

                                if WEBHOOK_DEBUG_ECHO:
                                    response_text = build_debug_reply(message_text, customer_phone)
                                else:
                                    response_text = process_customer_message(
                                        customer_phone,
                                        message_text
                                    )
                                
                                # WhatsApp'a cevap gönder
                                print(f"📤 Sending response: {response_text}", flush=True)
                                logger.info(f"📤 Sending response: {response_text}")
                                send_whatsapp_message(customer_phone, response_text)

                                current_state = get_conversation_state(customer_phone).get("state", "idle")
                                if current_state == "waiting_order_confirmation":
                                    send_whatsapp_interactive_buttons(
                                        customer_phone,
                                        "Siparişi onaylıyor musunuz?",
                                        build_order_confirmation_buttons(),
                                    )
                                elif current_state == "waiting_payment_method":
                                    send_whatsapp_interactive_buttons(
                                        customer_phone,
                                        "Ödeme yöntemini seçiniz.",
                                        build_payment_buttons(),
                                    )
                                elif current_state == "waiting_shipment_lookup_method":
                                    send_whatsapp_interactive_buttons(
                                        customer_phone,
                                        "Kargo kontrol yöntemini seçin:",
                                        build_shipment_lookup_buttons(),
                                    )
                            elif message_type == "interactive":
                                print(f"ℹ️  Interactive message received: {json.dumps(message, ensure_ascii=False)}", flush=True)
                                logger.info(f"ℹ️  Interactive message received: {json.dumps(message, ensure_ascii=False)}")

                                interactive = message.get("interactive", {})
                                button_reply = interactive.get("button_reply", {})
                                button_id = button_reply.get("id")

                                if button_id == "btn_start_products":
                                    send_whatsapp_message(customer_phone, format_product_catalog(get_product_catalog()))
                                elif button_id == "btn_start_order":
                                    send_whatsapp_message(customer_phone, build_order_help_message())
                                elif button_id == "btn_start_shipment":
                                    send_whatsapp_interactive_buttons(
                                        customer_phone,
                                        build_shipment_menu_message(),
                                        [
                                            {"id": "btn_has_tracking_code", "title": "Kargo takip numaram var"},
                                            {"id": "btn_no_tracking_code", "title": "Kargo takip numaramı bilmiyorum"},
                                        ],
                                    )
                                elif button_id == "btn_order_confirm_yes":
                                    pending_order = get_conversation_state(customer_phone).get("data", {})
                                    set_conversation_state(customer_phone, "waiting_payment_method", pending_order)
                                    send_whatsapp_interactive_buttons(
                                        customer_phone,
                                        "Ödeme yöntemini seçiniz.",
                                        build_payment_buttons(),
                                    )
                                elif button_id == "btn_order_confirm_no":
                                    clear_conversation_state(customer_phone)
                                    send_whatsapp_message(customer_phone, build_intro_message())
                                elif button_id == "btn_payment_cash":
                                    # finalize order: post to KOBI and inform customer
                                    pending = get_conversation_state(customer_phone).get("data", {}) or {}
                                    pending_order = pending.get("pending_order") if isinstance(pending, dict) and pending.get("pending_order") else pending
                                    result = post_order_to_kobi(customer_phone, pending_order)
                                    clear_conversation_state(customer_phone)
                                    if isinstance(result, dict) and result.get("siparis_id"):
                                        send_whatsapp_message(customer_phone, f"Nakit ödeme seçiminiz alındı. Sipariş talebiniz oluşturuldu (ID: {result.get('siparis_id')}).")
                                    elif isinstance(result, dict) and result.get("mesaj") and not result.get("error"):
                                        send_whatsapp_message(customer_phone, f"Nakit ödeme seçiminiz alındı. {result.get('mesaj')}")
                                    else:
                                        send_whatsapp_message(customer_phone, "Nakit ödeme seçiminiz alındı fakat sipariş oluşturulurken bir sorun oldu. Lütfen daha sonra tekrar deneyin.")
                                elif button_id == "btn_payment_iban":
                                    pending = get_conversation_state(customer_phone).get("data", {}) or {}
                                    pending_order = pending.get("pending_order") if isinstance(pending, dict) and pending.get("pending_order") else pending
                                    result = post_order_to_kobi(customer_phone, pending_order)
                                    clear_conversation_state(customer_phone)
                                    if isinstance(result, dict) and result.get("siparis_id"):
                                        send_whatsapp_message(customer_phone, f"IBAN ile ödeme seçiminiz alındı. Sipariş talebiniz oluşturuldu (ID: {result.get('siparis_id')}). Lütfen ödeme açıklamasına sipariş numarasını ekleyin.")
                                    elif isinstance(result, dict) and result.get("mesaj") and not result.get("error"):
                                        send_whatsapp_message(customer_phone, f"IBAN ile ödeme seçiminiz alındı. {result.get('mesaj')}")
                                    else:
                                        send_whatsapp_message(customer_phone, "IBAN ile ödeme seçiminiz alındı fakat sipariş oluşturulurken bir sorun oldu. Lütfen daha sonra tekrar deneyin.")
                                elif button_id == "btn_has_tracking_code":
                                    send_whatsapp_message(
                                        customer_phone,
                                        "Kargo takip numaranızı örnekteki gibi yanına yazı eklemeden yazabilir misiniz?\nÖrnek: KRG-20260512-000006",
                                    )
                                elif button_id == "btn_no_tracking_code":
                                    set_conversation_state(customer_phone, "waiting_shipment_tracking", {})
                                    send_whatsapp_message(
                                        customer_phone,
                                        "Anladım. Takip numaranız yoksa 'telefon numaramla kontrol et' yazın; telefon kaydınız üzerinden en son kargoyu kontrol edeyim.",
                                    )
                                elif button_id == "btn_shipment_lookup_tracking":
                                    set_conversation_state(customer_phone, "waiting_shipment_tracking", {})
                                    send_whatsapp_message(customer_phone, "Takip numaranızı paylaşır mısınız?")
                                elif button_id == "btn_shipment_lookup_phone":
                                    clear_conversation_state(customer_phone)
                                    shipment_result = get_shipment_by_phone(customer_phone)
                                    send_whatsapp_message(customer_phone, build_phone_lookup_confirmation_message(shipment_result))
                                else:
                                    send_whatsapp_message(customer_phone, build_intro_message())
            else:
                logger.warning(f"⚠️  Non-WhatsApp payload or empty body: {body.get('object') if body else 'empty'}")
        
        except Exception as e:
            logger.error(f"❌ Webhook error: {e}", exc_info=True)
        
        logger.info("=" * 60)
        return "ok", 200


def send_whatsapp_message(recipient_phone: str, message_text: str) -> bool:
    """
    WhatsApp mesajı gönder
    
    Args:
        recipient_phone: Alıcı telefon numarası
        message_text: Mesaj metni
    
    Returns:
        Başarılı mı
    """
    try:
        # Kontrol et
        if not WHATSAPP_API_TOKEN:
            logger.error("❌ WHATSAPP_API_TOKEN is empty!")
            print("❌ WHATSAPP_API_TOKEN is empty!", flush=True)
            return False
        
        if not WHATSAPP_PHONE_ID:
            logger.error("❌ WHATSAPP_PHONE_ID is empty!")
            print("❌ WHATSAPP_PHONE_ID is empty!", flush=True)
            return False
        
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
        
        print(f"📤 Sending to {recipient_phone}: {message_text}", flush=True)
        print(f"URL: {url}", flush=True)
        logger.info(f"📤 Sending to {recipient_phone}: {message_text}")
        logger.info(f"URL: {url}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        print(f"✅ WhatsApp API response status: {response.status_code}", flush=True)
        print(f"Response body: {response.text}", flush=True)
        logger.info(f"✅ WhatsApp API response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")

        if response.ok:
            print(f"✅ Message sent to {recipient_phone}", flush=True)
            logger.info(f"✅ Message sent to {recipient_phone}")
            return True
        else:
            print(f"❌ Failed to send message. Status: {response.status_code}, Body: {response.text}", flush=True)
            logger.error(f"❌ Failed to send message. Status: {response.status_code}, Body: {response.text}")

            # If authentication error, write unsent message to local queue for operator inspection
            if response.status_code == 401:
                logger.error("❌ WhatsApp token geçersiz veya süresi dolmuş olabilir (OAuth 190). WHATSAPP_API_TOKEN güncelleyin.")
                try:
                    with open("unsent_messages.log", "a", encoding="utf-8") as f:
                        f.write(f"{datetime.datetime.utcnow().isoformat()} | TO:{recipient_phone} | STATUS:401 | BODY:{message_text}\n")
                    print("⚠️ Mesaj unsent_messages.log dosyasına kaydedildi. Token yenilenince elle gönderebilirsiniz.", flush=True)
                except Exception as e:
                    logger.error(f"Failed to write unsent message: {e}", exc_info=True)

            return False
    
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}", flush=True)
        logger.error(f"❌ Request failed: {e}", exc_info=True)
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}", flush=True)
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return False


def post_order_to_kobi(customer_phone: str, pending_order: Dict[str, Any]) -> Dict[str, Any]:
    """Post order to KOBI panel `/api/siparis-onay/talep`.

    pending_order is expected to be the structure set in conversation state:
      {"items": [{...}], "raw_message": "..."}

    Returns parsed JSON response or {'error': '...'} on failure.
    """
    try:
        if not pending_order or not isinstance(pending_order, dict):
            return {"error": "No order data"}

        items = pending_order.get("items") or []
        urunler_payload: List[Dict[str, Any]] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            matched = it.get("matched_product") or {}
            adet = it.get("quantity") or it.get("adet") or 1
            try:
                adet = int(adet)
            except Exception:
                try:
                    adet = int(float(adet))
                except Exception:
                    adet = 1

            if isinstance(matched, dict) and matched.get("id"):
                urunler_payload.append({"urun_id": matched.get("id"), "adet": adet})
            else:
                urunler_payload.append({"custom_name": it.get("matched_product_name") or it.get("product_name") or it.get("custom_name") or "Urun", "adet": adet})

        payload = {
            "musteri_telefon": customer_phone,
            "musteri_ad": None,
            "urunler": urunler_payload if urunler_payload else None,
            "urunler_ozet": pending_order.get("raw_message") or pending_order.get("urunler_ozet") or None,
            "toplam_tutar": pending_order.get("toplam_tutar")
        }

        url = f"{KOBI_API_BASE_URL.rstrip('/')}/api/siparis-onay/talep"
        resp = requests.post(url, json=payload, timeout=8)
        try:
            data = resp.json() if resp.text else {}
        except Exception:
            data = {"status_code": resp.status_code, "text": resp.text}

        if resp.ok:
            return data
        return {"error": "Kobi API error", "status_code": resp.status_code, "body": data}
    except requests.RequestException as e:
        logger.error(f"Kobi API request failed: {e}")
        return {"error": "request_failed", "details": str(e)}
    except Exception as e:
        logger.error(f"post_order_to_kobi failed: {e}", exc_info=True)
        return {"error": "internal", "details": str(e)}


# ============================
# Health Check
# ============================

@app.route("/", methods=["GET"])
def index():
    print("INDEX ROUTE CALLED", flush=True)
    return {
        "status": "ok",
        "message": "WhatsApp KOBI Bot calisiyor.",
        "endpoints": {
            "health": "/health",
            "webhook": "/webhook"
        },
        "note": "WhatsApp mesajlari / endpoint'ine degil, /webhook endpoint'ine gelir."
    }, 200

@app.route("/test", methods=["POST"])
def test():
    print("TEST ROUTE CALLED", flush=True)
    data = request.get_json(silent=True) or {}
    print(f"TEST DATA: {data}", flush=True)
    # If test payload contains 'to' and 'message', attempt to send via WhatsApp
    to = data.get("to") or data.get("telefon") or data.get("phone")
    message = data.get("message") or data.get("mesaj") or data.get("text")
    if to and message:
        sent = send_whatsapp_message(to, message)
        return {"status": "test ok", "sent": bool(sent), "to": to, "message": message}, 200
    return {"status": "test ok", "received": data}, 200

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    # Development server
    app.run(debug=False, use_reloader=False, port=5000)
