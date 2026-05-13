import sys, os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional
import sqlite3
import os
import requests
import datetime
import re
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from Statistics.prophet_statistics import (
    get_overall_revenue_forecast,
    get_all_products_forecast,
    get_product_sales_forecast,
    get_all_products_statistics
)
from Statistics.report import (
    generate_business_report,
    generate_supplier_order_draft,
    generate_depot_order_draft,
    generate_shipping_apology
)

app = FastAPI(title="KOBI Akilli Yonetim Sistemi API", version="2.0.0")

# CORS Güvenlik Ayarı: Canlıda sadece kendi domaininize izin verin.
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# --- STATIK DOSYALARI SUNMA ---
@app.get("/")
def serve_index():
    # Kök dizine istek geldiğinde index.html'i döndür
    index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "index.html bulunamadi"}

@app.get("/app.js")
def serve_app_js():
    js_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.js")
    if os.path.exists(js_path):
        return FileResponse(js_path)
    return {"error": "app.js bulunamadi"}

# --- VERITABANI BAGLANTISI ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "DB", "SME_DB.db")

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _parse_order_text_to_items(raw_text: str, conn: sqlite3.Connection) -> list[dict]:
    """Try to parse a free-text order summary into structured items.

    Strategy: split by commas/newlines/' ve ', extract leading quantity if present,
    then try to match product by name with a simple SQL LIKE on `urunler.ad`.
    Returns a list of dicts: either {'urun_id': id, 'adet': qty} or {'custom_name': name, 'adet': qty}
    """
    if not raw_text:
        return []

    segments = [s.strip() for s in re.split(r"[,;\n]|\s+ve\s+", raw_text, flags=re.IGNORECASE) if s.strip()]
    items = []

    for seg in segments:
        # Try to capture quantity at start e.g. '2 kilo domates' or '2 domates'
        m = re.search(r"(?P<quantity>\d+(?:[\.,]\d+)?)\s*(?P<unit>kilo|kg|adet|tane|kavanoz|paket|sise|şişe|sise|kutu)?\s*(?P<name>.+)", seg, flags=re.IGNORECASE)
        if m:
            raw_qty = m.group('quantity')
            try:
                qty = float(raw_qty.replace(',', '.'))
                qty = int(qty) if qty.is_integer() else qty
            except Exception:
                qty = 1
            name = m.group('name').strip()
        else:
            # fallback: no leading quantity, assume 1 and full segment as name
            qty = 1
            name = seg

        # Normalize name for matching
        name_norm = name.lower()
        # Try to find a product whose name contains the name_norm tokens
        prod_row = None
        try:
            # first try exact match
            row = conn.execute("SELECT id, ad FROM urunler WHERE lower(ad)=? LIMIT 1", (name_norm,)).fetchone()
            if row:
                prod_row = row
            else:
                # try LIKE matching on the entire segment
                row = conn.execute("SELECT id, ad FROM urunler WHERE lower(ad) LIKE ? LIMIT 1", (f"%{name_norm}%",)).fetchone()
                if row:
                    prod_row = row
                else:
                    # try token by token
                    tokens = [t for t in re.split(r"\s+", name_norm) if len(t) > 2]
                    for tok in tokens:
                        row = conn.execute("SELECT id, ad FROM urunler WHERE lower(ad) LIKE ? LIMIT 1", (f"%{tok}%",)).fetchone()
                        if row:
                            prod_row = row
                            break
        except Exception:
            prod_row = None

        if prod_row:
            items.append({"urun_id": prod_row["id"], "adet": qty})
        else:
            items.append({"custom_name": name, "adet": qty})

    return items


def _find_product_by_name(conn: sqlite3.Connection, query_text: str) -> Optional[sqlite3.Row]:
    """Best-effort product lookup for free-text or custom_name items."""
    normalized = (query_text or "").strip().lower()
    if not normalized:
        return None

    exact = conn.execute("SELECT * FROM urunler WHERE lower(ad)=? LIMIT 1", (normalized,)).fetchone()
    if exact:
        return exact

    like = conn.execute("SELECT * FROM urunler WHERE lower(ad) LIKE ? LIMIT 1", (f"%{normalized}%",)).fetchone()
    if like:
        return like

    tokens = [token for token in re.split(r"\s+", normalized) if len(token) > 2]
    for token in tokens:
        row = conn.execute("SELECT * FROM urunler WHERE lower(ad) LIKE ? LIMIT 1", (f"%{token}%",)).fetchone()
        if row:
            return row

    return None

# --- YARDIMCI FONKSIYONLAR ---
def tablo_getir(tablo: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(f"SELECT * FROM {tablo} ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def kayit_ekle(tablo: str, data: dict) -> int:
    data = {k: v for k, v in data.items() if v is not None}
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"INSERT INTO {tablo} ({', '.join(data.keys())}) VALUES ({', '.join(['?'] * len(data))})", list(data.values()))
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

def kayit_guncelle(tablo: str, record_id: int, data: dict) -> None:
    data = {k: v for k, v in data.items() if v is not None}
    set_clause = ", ".join([f"{k}=?" for k in data.keys()])
    conn = get_db()
    conn.execute(f"UPDATE {tablo} SET {set_clause} WHERE id=?", list(data.values()) + [record_id])
    conn.commit()
    conn.close()

def kayit_sil(tablo: str, record_id: int) -> None:
    conn = get_db()
    try:
        conn.execute(f"DELETE FROM {tablo} WHERE id=?", (record_id,))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Bu kayit baska verilerle bagintili oldugu icin silinemez.")
    finally:
        conn.close()

# --- PYDANTIC MODELLERI ---
class TedarikciModel(BaseModel):
    ad: Optional[str] = None
    yetkili: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None
    adres: Optional[str] = None
    vergi_no: Optional[str] = None

class UrunModel(BaseModel):
    urun_kodu: Optional[str] = None
    ad: Optional[str] = None
    kategori: Optional[str] = None
    birim: Optional[str] = None
    stok_miktari: Optional[float] = 0
    kritik_stok_esigi: Optional[float] = 0
    alis_fiyati: Optional[float] = None
    satis_fiyati: Optional[float] = None
    birim_agirlik: Optional[float] = None
    aciklama: Optional[str] = None

class DepoMalzemesiModel(BaseModel):
    tedarikci_id: Optional[int] = None
    malzeme_kodu: Optional[str] = None
    ad: Optional[str] = None
    birim: Optional[str] = None
    stok_miktari: Optional[float] = 0
    kritik_stok_esigi: Optional[float] = 0
    birim_fiyati: Optional[float] = None

class MusteriModel(BaseModel):
    ad_soyad: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None
    teslimat_adresi: Optional[str] = None
    notlar: Optional[str] = None

class KargoTakipModel(BaseModel):
    musteri_id: Optional[int] = None
    kargo_no: Optional[str] = None
    durum: Optional[str] = None
    beklenen_teslimat: Optional[str] = None

class HizliSatisModel(BaseModel):
    urun_id: int
    adet: float

class SiparisTalebiModel(BaseModel):
    musteri_telefon: str
    musteri_ad: Optional[str] = None
    # Yeni: yapısal urun listesi (whatsapp bot bu formatta post etmeli)
    # örnek: [{"urun_id": 1, "adet": 2}, {"custom_name": "Sabun", "adet": 1}]
    urunler: Optional[list[dict]] = None
    urunler_ozet: Optional[str] = None
    toplam_tutar: Optional[float] = None
    notlar: Optional[str] = None

# --- API ENDPOINTLERI (Ozet & Analiz) ---
@app.get("/api/ozet")
def ozet():
    conn = get_db()
    res = {
        "toplam_urun": conn.execute("SELECT COUNT(*) FROM urunler").fetchone()[0],
        "kritik_stok": conn.execute("SELECT COUNT(*) FROM urunler WHERE stok_miktari <= kritik_stok_esigi").fetchone()[0],
        "kritik_depo": conn.execute("SELECT COUNT(*) FROM depo_malzemeleri WHERE stok_miktari <= kritik_stok_esigi").fetchone()[0],
        "toplam_musteri": conn.execute("SELECT COUNT(*) FROM musteriler").fetchone()[0],
        "toplam_tedarikci": conn.execute("SELECT COUNT(*) FROM tedarikciler").fetchone()[0],
    }
    conn.close()
    return res

@app.get("/api/analiz/kritik-aksiyonlar")
def kritik_aksiyonlar():
    conn = get_db()
    aksiyonlar = []
    
    for u in conn.execute("SELECT * FROM urunler").fetchall():
        if u['stok_miktari'] <= u['kritik_stok_esigi']:
            aksiyonlar.append({"tip": "danger", "kategori": "urun", "mesaj": f"Urun '{u['ad']}' stok uyarisi ({u['stok_miktari']} kaldi).", "aksiyon": "Tedarikci Mesaji", "urun_id": u['id']})
    
    for m in conn.execute("SELECT * FROM depo_malzemeleri").fetchall():
        if m['stok_miktari'] <= (m['kritik_stok_esigi'] or 0):
            aksiyonlar.append({"tip": "danger", "kategori": "depo", "mesaj": f"Hammadde '{m['ad']}' tukeniyor.", "aksiyon": "Siparis Mesaji", "urun_id": m['id']})
            
    for k in conn.execute("SELECT k.*, m.ad_soyad FROM kargo_takip k JOIN musteriler m ON k.musteri_id = m.id WHERE k.durum IN ('Gecikme', 'Subede Bekliyor')").fetchall():
        aksiyonlar.append({"tip": "warning", "kategori": "kargo", "mesaj": f"{k['ad_soyad']} siparisi: {k['durum']}.", "aksiyon": "Ozur Mesaji", "kargo_id": k['id']})
        
    conn.close()
    return aksiyonlar

@app.get("/api/hava-durumu-uyarisi")
def hava_durumu():
    return {"uyari": "Yapay Zeka Analizi: Bolgenizdeki yogun yagis kargo rotalarinda ortalama 1 gun gecikme riski olusturuyor."}

# --- YAPAY ZEKA AKSİYON TASLAKLARI ---
@app.get("/api/aksiyon/tedarik-taslak/{urun_id}")
def tedarik_taslak(urun_id: int):
    conn = get_db()
    urun = conn.execute("SELECT * FROM urunler WHERE id=?", (urun_id,)).fetchone()
    tedarikci = conn.execute("SELECT * FROM tedarikciler LIMIT 1").fetchone()
    conn.close()
    if not urun: raise HTTPException(status_code=404, detail="Urun bulunamadi.")
    taslak = generate_supplier_order_draft(tedarikci['ad'] if tedarikci else "Tedarikci", urun['ad'], 50, tedarikci['telefon'] if tedarikci else "")
    return {"taslak": taslak}

@app.get("/api/aksiyon/depo-tedarik-taslak/{malzeme_id}")
def depo_tedarik_taslak(malzeme_id: int):
    conn = get_db()
    malzeme = conn.execute("SELECT * FROM depo_malzemeleri WHERE id=?", (malzeme_id,)).fetchone()
    tedarikci = conn.execute("SELECT * FROM tedarikciler WHERE id=?", (malzeme['tedarikci_id'],)).fetchone() if malzeme and malzeme['tedarikci_id'] else None
    conn.close()
    if not malzeme: raise HTTPException(status_code=404)
    taslak = generate_depot_order_draft(tedarikci['ad'] if tedarikci else "Tedarikci", malzeme['ad'], 100, tedarikci['telefon'] if tedarikci else "")
    return {"taslak": taslak}

@app.get("/api/aksiyon/kargo-ozur/{kargo_id}")
def kargo_ozur(kargo_id: int):
    conn = get_db()
    kargo = conn.execute("SELECT k.*, m.ad_soyad FROM kargo_takip k JOIN musteriler m ON k.musteri_id = m.id WHERE k.id=?", (kargo_id,)).fetchone()
    conn.close()
    if not kargo: raise HTTPException(status_code=404)
    return {"taslak": generate_shipping_apology(kargo['ad_soyad'], kargo['kargo_no'], kargo['durum'])}

# --- YAPAY ZEKA TAHMINLERI ---
@app.get("/api/tahmin/genel")
def genel_tahmin_getir(gun_sayisi: int = 14): return get_overall_revenue_forecast(days=gun_sayisi)

@app.get("/api/tahmin/urunler")
def urun_tahmin_getir(gun_sayisi: int = 14): return get_all_products_forecast(days=gun_sayisi)

@app.get("/api/ai-rapor")
def ai_rapor_getir(gun_sayisi: int = 14): return {"rapor": generate_business_report(days=gun_sayisi)}

# --- GRAFIK VERILERI ---
@app.get("/api/grafik/zaman-serisi")
def grafik_zaman_serisi(dilim: str = 'aylik', urun_id: int = 1):
    conn = get_db()
    if dilim == 'tumzamanlar':
        format_str = "%Y-%m"
        query = f"SELECT strftime('{format_str}', tarih) as zaman, SUM(miktar) as toplam FROM stok_hareketleri WHERE tur = 'Satis' AND urun_id = ? GROUP BY zaman ORDER BY zaman ASC"
        rows = conn.execute(query, (urun_id,)).fetchall()
    else:
        format_map  = {"gunluk": "%Y-%m-%d", "haftalik": "%Y-%W", "aylik": "%Y-%m", "yillik": "%Y"}
        days_map    = {"gunluk": 1, "haftalik": 7, "aylik": 30, "yillik": 365}
        format_str  = format_map.get(dilim, "%Y-%m")
        days        = days_map.get(dilim, 30)
        query = (
            f"SELECT strftime('{format_str}', tarih) as zaman, SUM(miktar) as toplam "
            f"FROM stok_hareketleri "
            f"WHERE tur = 'Satis' AND urun_id = ? AND tarih >= date('now', '-{days} days') "
            f"GROUP BY zaman ORDER BY zaman ASC"
        )
        rows = conn.execute(query, (urun_id,)).fetchall()
    conn.close()
    return {"etiketler": [r["zaman"] for r in rows], "veriler": [r["toplam"] for r in rows]}


@app.get("/api/grafik/pasta")
def grafik_pasta(dilim: str = 'aylik'):
    conn = get_db()
    days = {"gunluk": 1, "haftalik": 7, "aylik": 30, "yillik": 365}.get(dilim, 30)
    if dilim == 'tumzamanlar':
        query = "SELECT u.ad, SUM(sh.miktar) as toplam FROM stok_hareketleri sh JOIN urunler u ON sh.urun_id = u.id WHERE sh.tur = 'Satis' GROUP BY u.ad"
        rows = conn.execute(query).fetchall()
    else:
        query = f"SELECT u.ad, SUM(sh.miktar) as toplam FROM stok_hareketleri sh JOIN urunler u ON sh.urun_id = u.id WHERE sh.tur = 'Satis' AND sh.tarih >= date('now', '-{days} days') GROUP BY u.ad"
        rows = conn.execute(query).fetchall()
    conn.close()
    return {"etiketler": [r["ad"] for r in rows], "veriler": [r["toplam"] for r in rows]}

@app.get("/api/grafik/karsilastirma")
def grafik_karsilastirma(dilim: str = 'aylik'):
    """Tüm ürünlerin aynı zaman ekseninde satış verisini döndürür (karşılaştırmalı grafik için)"""
    conn = get_db()

    if dilim == 'tumzamanlar':
        format_str = "%Y-%m"
        tarih_filtresi = ""
    else:
        format_str = {"gunluk": "%Y-%m-%d", "haftalik": "%Y-%W", "aylik": "%Y-%m", "yillik": "%Y"}.get(dilim, "%Y-%m")
        days = {"gunluk": 1, "haftalik": 7, "aylik": 30, "yillik": 365}.get(dilim, 30)
        tarih_filtresi = f"AND sh.tarih >= date('now', '-{days} days')"

    # Tüm zaman etiketlerini bul
    zaman_q = f"""
        SELECT DISTINCT strftime('{format_str}', sh.tarih) as zaman
        FROM stok_hareketleri sh
        WHERE sh.tur = 'Satis' {tarih_filtresi}
        ORDER BY zaman ASC
    """
    zaman_rows = conn.execute(zaman_q).fetchall()
    etiketler = [r["zaman"] for r in zaman_rows]

    # Her ürün için veri çek
    urunler_q = "SELECT id, ad FROM urunler ORDER BY id ASC"
    urunler = conn.execute(urunler_q).fetchall()

    result_urunler = []
    for u in urunler:
        veri_q = f"""
            SELECT strftime('{format_str}', sh.tarih) as zaman, SUM(sh.miktar) as toplam
            FROM stok_hareketleri sh
            WHERE sh.tur = 'Satis' AND sh.urun_id = ? {tarih_filtresi}
            GROUP BY zaman ORDER BY zaman ASC
        """
        rows = conn.execute(veri_q, (u["id"],)).fetchall()
        veri_map = {r["zaman"]: r["toplam"] for r in rows}
        # Eksik zaman dilimlerini 0 ile doldur
        veriler = [veri_map.get(et, 0) for et in etiketler]
        # Sadece en az bir satışı olan ürünleri ekle
        if any(v > 0 for v in veriler):
            result_urunler.append({"ad": u["ad"], "veriler": veriler})

    conn.close()
    return {"etiketler": etiketler, "urunler": result_urunler}

# --- STOK ISLEMLERI ---
@app.post("/api/hizli_satis")
def hizli_satis(m: HizliSatisModel):
    conn = get_db()
    urun = conn.execute("SELECT * FROM urunler WHERE id=?", (m.urun_id,)).fetchone()
    if not urun: raise HTTPException(404, "Urun bulunamadi.")
    if m.adet <= 0 or urun["stok_miktari"] < m.adet: raise HTTPException(400, "Gecersiz adet veya yetersiz stok.")
    yeni_stok = urun["stok_miktari"] - m.adet
    conn.execute("UPDATE urunler SET stok_miktari=? WHERE id=?", (yeni_stok, m.urun_id))
    conn.execute("INSERT INTO stok_hareketleri (urun_id, tur, miktar, onceki_stok, sonraki_stok) VALUES (?,?,?,?,?)", (m.urun_id, "Satis", m.adet, urun["stok_miktari"], yeni_stok))
    conn.commit()
    conn.close()
    return {"mesaj": "Satis Basarili", "yeni_stok": yeni_stok}

@app.post("/api/stok_artir")
def stok_artir(urun_id: int, miktar: float):
    conn = get_db()
    urun = conn.execute("SELECT * FROM urunler WHERE id=?", (urun_id,)).fetchone()
    yeni_stok = urun["stok_miktari"] + miktar
    conn.execute("UPDATE urunler SET stok_miktari=? WHERE id=?", (yeni_stok, urun_id))
    conn.execute("INSERT INTO stok_hareketleri (urun_id, tur, miktar, onceki_stok, sonraki_stok) VALUES (?,?,?,?,?)", (urun_id, "Alim", miktar, urun["stok_miktari"], yeni_stok))
    conn.commit()
    conn.close()
    return {"mesaj": "Stok Artirildi"}

# --- Ozel CRUD endpointleri (Tablo bazli ekle/guncelle/sil) ---
@app.post("/api/tedarikciler")
def t_ekle(m: TedarikciModel): return {"id": kayit_ekle("tedarikciler", m.dict())}
@app.put("/api/tedarikciler/{id}")
def t_guncelle(id: int, m: TedarikciModel): kayit_guncelle("tedarikciler", id, m.dict()); return {"mesaj": "OK"}
@app.delete("/api/tedarikciler/{id}")
def t_sil(id: int): kayit_sil("tedarikciler", id); return {"mesaj": "OK"}

@app.post("/api/urunler")
def u_ekle(m: UrunModel): return {"id": kayit_ekle("urunler", m.dict())}
@app.put("/api/urunler/{id}")
def u_guncelle(id: int, m: UrunModel): kayit_guncelle("urunler", id, m.dict()); return {"mesaj": "OK"}
@app.delete("/api/urunler/{id}")
def u_sil(id: int): kayit_sil("urunler", id); return {"mesaj": "OK"}

@app.post("/api/depo_malzemeleri")
def d_ekle(m: DepoMalzemesiModel): return {"id": kayit_ekle("depo_malzemeleri", m.dict())}
@app.put("/api/depo_malzemeleri/{id}")
def d_guncelle(id: int, m: DepoMalzemesiModel): kayit_guncelle("depo_malzemeleri", id, m.dict()); return {"mesaj": "OK"}
@app.delete("/api/depo_malzemeleri/{id}")
def d_sil(id: int): kayit_sil("depo_malzemeleri", id); return {"mesaj": "OK"}

@app.post("/api/musteriler")
def mus_ekle(m: MusteriModel): return {"id": kayit_ekle("musteriler", m.dict())}
@app.put("/api/musteriler/{id}")
def mus_guncelle(id: int, m: MusteriModel): kayit_guncelle("musteriler", id, m.dict()); return {"mesaj": "OK"}
@app.delete("/api/musteriler/{id}")
def mus_sil(id: int): kayit_sil("musteriler", id); return {"mesaj": "OK"}

@app.post("/api/kargo_takip")
def k_ekle(m: KargoTakipModel): return {"id": kayit_ekle("kargo_takip", m.dict())}
@app.put("/api/kargo_takip/{id}")
def k_guncelle(id: int, m: KargoTakipModel): kayit_guncelle("kargo_takip", id, m.dict()); return {"mesaj": "OK"}
@app.delete("/api/kargo_takip/{id}")
def k_sil(id: int): kayit_sil("kargo_takip", id); return {"mesaj": "OK"}

# --- CRUD Joker Endpointi (EN SONDA OLMALIDIR) ---
@app.get("/api/{tablo}")
def genel_getir(tablo: str): 
    return tablo_getir(tablo)

# --- FRONTEND EŞLEŞMESİ (HTML ve JS Dosyalarinin Sunulmasi) ---
@app.get("/app.js", include_in_schema=False)
def serve_js():
    js_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.js")
    if os.path.exists(js_path):
        return FileResponse(js_path)
    raise HTTPException(status_code=404, detail="app.js dosyasi bulunamadi. Lutfen main.py ile ayni dizinde oldugundan emin olun.")

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    return FileResponse(html_path) if os.path.exists(html_path) else HTMLResponse(content="index.html bulunamadi.", status_code=200)


# ========================================================
# SİPARİŞ ONAY SİSTEMİ (WhatsApp entegrasyonu)
# ========================================================

# WhatsApp ayarları (isteğe bağlı, .env ile override edilebilir)
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
KOBI_WHATSAPP_BOT_URL = os.getenv("KOBI_WHATSAPP_BOT_URL", "http://127.0.0.1:5000")
MOCK_CARGO_URL = os.getenv("MOCK_CARGO_URL", "http://127.0.0.1:3000")

def _send_whatsapp(telefon: str, mesaj: str):
    """İç yardımcı: WhatsApp mesajı gönder"""
    if not WHATSAPP_API_TOKEN or not WHATSAPP_PHONE_ID:
        return False
    try:
        url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": telefon,
            "type": "text",
            "text": {"body": mesaj}
        }
        headers = {
            "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
            "Content-Type": "application/json"
        }
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        return r.ok
    except Exception:
        return False

def _ensure_siparis_onay_table():
    """siparis_onay tablosu yoksa oluştur"""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS siparis_onay (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            musteri_telefon TEXT NOT NULL,
            musteri_ad TEXT,
            urunler_ozet TEXT,
            urunler_json TEXT,
            toplam_tutar REAL,
            notlar TEXT,
            durum TEXT DEFAULT 'bekliyor',
            talep_tarihi TEXT DEFAULT (datetime('now','localtime')),
            karar_tarihi TEXT
        )
    """)
    conn.commit()
    # Ensure column exists for older DBs: add urunler_json if missing
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info('siparis_onay')").fetchall()]
        if 'urunler_json' not in cols:
            conn.execute("ALTER TABLE siparis_onay ADD COLUMN urunler_json TEXT")
            conn.commit()
    except Exception:
        pass
    conn.close()

_ensure_siparis_onay_table()

@app.post("/api/siparis-onay/talep")
def siparis_talep_olustur(m: SiparisTalebiModel):
    """WhatsApp bot'undan gelen sipariş talebini kaydeder"""
    conn = get_db()
    _ensure_siparis_onay_table()
    cur = conn.cursor()
    # Kaydederken hem yapısal ürünleri hem de okunabilir özet metni sakla
    readable_ozet = None
    if m.urunler and isinstance(m.urunler, list):
        # build human readable summary from structured items
        lines = []
        for it in m.urunler:
            if isinstance(it, dict) and it.get('urun_id'):
                prod = conn.execute("SELECT ad FROM urunler WHERE id=?", (it['urun_id'],)).fetchone()
                name = prod['ad'] if prod else f"Urun:{it['urun_id']}"
                adet = it.get('adet') or it.get('adet') or 1
                lines.append(f"- {name}: {adet}")
            elif isinstance(it, dict) and (it.get('custom_name') or it.get('name')):
                name = it.get('custom_name') or it.get('name')
                adet = it.get('adet') or 1
                lines.append(f"- {name}: {adet}")
            else:
                lines.append(str(it))
        readable_ozet = "\n".join(lines)
    else:
        # prefer explicit urunler_ozet if provided
        readable_ozet = m.urunler_ozet or None

    # store both readable summary and structured json when available
    urunler_json = None
    try:
        if m.urunler and isinstance(m.urunler, list):
            urunler_json = json.dumps(m.urunler, ensure_ascii=False)
    except Exception:
        urunler_json = None

    cur.execute("""
        INSERT INTO siparis_onay (musteri_telefon, musteri_ad, urunler_ozet, urunler_json, toplam_tutar, notlar)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (m.musteri_telefon, m.musteri_ad, readable_ozet or (str(m.urunler) if m.urunler else None), urunler_json, m.toplam_tutar, m.notlar))
    conn.commit()
    siparis_id = cur.lastrowid
    conn.close()
    return {"mesaj": "Sipariş talebi alındı, KOBİ onayı bekleniyor.", "siparis_id": siparis_id}

@app.get("/api/siparis-onay/bekleyenler")
def bekleyen_siparisler():
    """KOBİ panelinde gösterilecek bekleyen siparişleri döndür"""
    _ensure_siparis_onay_table()
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM siparis_onay WHERE durum = 'bekliyor' ORDER BY talep_tarihi DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/siparis-onay/{siparis_id}/onayla")
def siparis_onayla(siparis_id: int):
    """Siparişi onayla: kargo kaydı oluştur + müşteriye WhatsApp bildir"""
    _ensure_siparis_onay_table()
    conn = get_db()
    siparis = conn.execute("SELECT * FROM siparis_onay WHERE id=?", (siparis_id,)).fetchone()
    if not siparis:
        conn.close()
        raise HTTPException(status_code=404, detail="Sipariş bulunamadı.")
    if siparis["durum"] != "bekliyor":
        conn.close()
        raise HTTPException(status_code=400, detail="Sipariş zaten işleme alınmış.")
    
    # Müşteriyi veritabanında bul veya oluştur
    musteri = conn.execute("SELECT id FROM musteriler WHERE telefon=?", (siparis["musteri_telefon"],)).fetchone()
    if not musteri:
        conn.execute("INSERT INTO musteriler (ad_soyad, telefon) VALUES (?, ?)",
                     (siparis["musteri_ad"] or siparis["musteri_telefon"], siparis["musteri_telefon"]))
        conn.commit()
        musteri = conn.execute("SELECT id FROM musteriler WHERE telefon=?", (siparis["musteri_telefon"],)).fetchone()
    
    musteri_id = musteri["id"]
    import random, string
    kargo_no = "KBT" + "".join(random.choices(string.digits, k=8))
    beklenen = (datetime.datetime.now() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    
    # Ürünleri kargoya hazırla: eğer siparişte yapısal ürün listesi varsa stoktan düş ve kargo itemleri oluştur
    items_for_cargo = []
    try:
        # Prefer structured JSON if available, otherwise fall back to parsing urunler_ozet
        siparis_urunler = []
        raw_json = siparis.get('urunler_json')
        if raw_json:
            try:
                siparis_urunler = json.loads(raw_json)
            except Exception:
                siparis_urunler = []

        if not siparis_urunler:
            raw = siparis.get('urunler_ozet')
            # If urunler_ozet looks like a serialized list, try to literal_eval it
            if raw and raw.strip().startswith('['):
                import ast
                try:
                    siparis_urunler = ast.literal_eval(raw)
                except Exception:
                    siparis_urunler = []

            # If still no structured list found, try to parse free-text into items
            if not siparis_urunler:
                parsed = _parse_order_text_to_items(raw or '', conn)
                siparis_urunler = parsed

        for it in siparis_urunler:
            if not isinstance(it, dict):
                continue
            adet_raw = it.get('adet', it.get('quantity', 1))
            try:
                adet = float(adet_raw)
            except Exception:
                adet = 1.0

            if adet <= 0:
                adet = 1.0

            prod = None
            if it.get('urun_id'):
                prod = conn.execute("SELECT * FROM urunler WHERE id=?", (it['urun_id'],)).fetchone()
                if not prod:
                    conn.close()
                    raise HTTPException(status_code=400, detail=f"Urun id {it['urun_id']} bulunamadi.")
            else:
                query_name = it.get('matched_product_name') or it.get('custom_name') or it.get('name') or it.get('product_name')
                prod = _find_product_by_name(conn, str(query_name or ""))

            if prod:
                product_id = prod['id']
                print(f"[SIPARIS_ONAY] Processing product id={product_id} qty={adet} current_stock={prod['stok_miktari']}")
                if prod['stok_miktari'] < adet:
                    conn.close()
                    raise HTTPException(status_code=400, detail=f"Yetersiz stok: {prod['ad']}")
                yeni_stok = prod['stok_miktari'] - adet
                conn.execute("UPDATE urunler SET stok_miktari=? WHERE id=?", (yeni_stok, product_id))
                conn.execute(
                    "INSERT INTO stok_hareketleri (urun_id, tur, miktar, onceki_stok, sonraki_stok) VALUES (?,?,?,?,?)",
                    (product_id, "Satis", adet, prod['stok_miktari'], yeni_stok),
                )
                conn.commit()
                print(f"[SIPARIS_ONAY] Updated product id={product_id} new_stock={yeni_stok}")
                items_for_cargo.append({"product_id": int(product_id), "quantity": int(adet)})
                continue

            # No match found: keep as custom cargo item, but stock cannot be decremented
            name = it.get('custom_name') or it.get('name') or it.get('product_name') or 'Urun'
            items_for_cargo.append({"custom_product_name": name, "quantity": int(adet)})

        if not items_for_cargo:
            logger.warning(f"[SIPARIS_ONAY] No structured cargo items parsed for siparis_id={siparis_id}. raw={siparis.get('urunler_json') or siparis.get('urunler_ozet')}")

        # Kargo kaydı oluştur
        conn.execute("""
            INSERT INTO kargo_takip (musteri_id, kargo_no, durum, beklenen_teslimat)
            VALUES (?, ?, 'Hazırlanıyor', ?)
        """, (musteri_id, kargo_no, beklenen))
        conn.commit()
    except HTTPException:
        raise
    except Exception:
        # on error, still create a minimal kargo entry and continue
        conn.execute("""
            INSERT INTO kargo_takip (musteri_id, kargo_no, durum, beklenen_teslimat)
            VALUES (?, ?, 'Hazırlanıyor', ?)
        """, (musteri_id, kargo_no, beklenen))
        conn.commit()
    
    # Sipariş durumunu güncelle
    conn.execute("""
        UPDATE siparis_onay SET durum='onaylandi', karar_tarihi=datetime('now','localtime') WHERE id=?
    """, (siparis_id,))
    conn.commit()
    conn.close()
    
    # Call Mock Cargo API to create a shipment and include items
    try:
        cargo_payload = {
            "customer_name": siparis.get('musteri_ad') or siparis.get('musteri_telefon'),
            "customer_phone": siparis.get('musteri_telefon'),
            "delivery_address": siparis.get('notlar') or "",
            "items": items_for_cargo if items_for_cargo else [{"custom_product_name": siparis.get('urunler_ozet') or 'Siparis', "quantity": 1}]
        }
        cargo_url_candidates = [
            f"{MOCK_CARGO_URL.rstrip('/')}/shipmets",
            f"{MOCK_CARGO_URL.rstrip('/')}/shipments",
        ]
        cargo_resp = None
        for cargo_url in cargo_url_candidates:
            try:
                cargo_resp = requests.post(cargo_url, json=cargo_payload, timeout=8)
                if cargo_resp.ok:
                    break
            except Exception as exc:
                logger.warning(f"Mock Cargo request failed for {cargo_url}: {exc}")
                cargo_resp = None
        if cargo_resp is not None and cargo_resp.ok:
            cargo_json = cargo_resp.json()
            tracking_code = cargo_json.get('tracking_code') or cargo_json.get('tracking_code')
        else:
            logger.error(f"Mock Cargo did not return success. last_response={getattr(cargo_resp, 'text', None)}")
            tracking_code = None
    except Exception:
        tracking_code = None

    # Müşteriye WhatsApp bildir (takip kodunu döndür)
    if not tracking_code:
        tracking_code = kargo_no

    mesaj = (
        f"Merhaba! Siparişiniz onaylandı ve kargo süreci başlatıldı.\n"
        f"Kargo Takip No: {tracking_code}\n"
        f"Tahmini Teslimat: {beklenen}\n"
        f"Siparişinizi '{tracking_code}' numarası ile takip edebilirsiniz."
    )
    sent = _send_whatsapp(siparis["musteri_telefon"], mesaj)
    if not sent:
        # fallback: try calling internal WhatsApp bot test endpoint to forward message
        try:
            bot_url = KOBI_WHATSAPP_BOT_URL.rstrip('/') + '/test'
            requests.post(bot_url, json={"to": siparis["musteri_telefon"], "message": mesaj}, timeout=5)
        except Exception:
            pass
    
    return {"mesaj": "Sipariş onaylandı, kargo oluşturuldu.", "kargo_no": kargo_no, "beklenen_teslimat": beklenen}

@app.post("/api/siparis-onay/{siparis_id}/reddet")
def siparis_reddet(siparis_id: int):
    """Siparişi reddet + müşteriye WhatsApp iptal bildirimi gönder"""
    _ensure_siparis_onay_table()
    conn = get_db()
    siparis = conn.execute("SELECT * FROM siparis_onay WHERE id=?", (siparis_id,)).fetchone()
    if not siparis:
        conn.close()
        raise HTTPException(status_code=404, detail="Sipariş bulunamadı.")
    if siparis["durum"] != "bekliyor":
        conn.close()
        raise HTTPException(status_code=400, detail="Sipariş zaten işleme alınmış.")
    
    conn.execute("""
        UPDATE siparis_onay SET durum='reddedildi', karar_tarihi=datetime('now','localtime') WHERE id=?
    """, (siparis_id,))
    conn.commit()
    conn.close()
    
    # Müşteriye WhatsApp iptal bildirimi
    mesaj = (
        f"Merhaba, üzgünüz.\n"
        f"Siparişiniz işleme alınamadı ve iptal edildi.\n"
        f"Daha fazla bilgi için bize ulaşabilirsiniz."
    )
    sent = _send_whatsapp(siparis["musteri_telefon"], mesaj)
    if not sent:
        # fallback: try calling internal WhatsApp bot test endpoint to forward message
        try:
            bot_url = KOBI_WHATSAPP_BOT_URL.rstrip('/') + '/test'
            requests.post(bot_url, json={"to": siparis["musteri_telefon"], "message": mesaj}, timeout=5)
        except Exception:
            pass
            
    return {"mesaj": "Sipariş reddedildi, müşteri bilgilendirildi."}