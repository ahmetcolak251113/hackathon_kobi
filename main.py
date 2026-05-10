from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
from Statistics.prophet_statistics import get_overall_revenue_forecast, get_all_products_forecast
import sqlite3
import os

# ─── UYGULAMA ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="KOBİ Akıllı Yönetim Sistemi API",
    description="Küçük ve orta ölçekli işletmeler için stok, sipariş, müşteri ve tedarikçi yönetim API'si.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── VERİTABANI ───────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    """Veritabanı bağlantısı açar ve döndürür."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "DB", "SME_DB.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def tablo_getir(tablo: str, extra_where: str = "", extra_join: str = "") -> list[dict]:
    """Belirtilen tablodan tüm kayıtları çeker."""
    conn = get_db()
    query = f"SELECT * FROM {tablo} {extra_join} {extra_where} ORDER BY id DESC"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def kayit_getir(tablo: str, record_id: int) -> dict:
    """Belirtilen tabloda id'ye göre tek kayıt döndürür. Bulunamazsa 404 fırlatır."""
    conn = get_db()
    row = conn.execute(f"SELECT * FROM {tablo} WHERE id=?", (record_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"{tablo} içinde id={record_id} bulunamadı.")
    return dict(row)


def kayit_ekle(tablo: str, data: dict) -> int:
    """Tabloya yeni kayıt ekler, eklenen kaydın id'sini döndürür."""
    data = {k: v for k, v in data.items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="Eklenecek veri boş olamaz.")
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    conn = get_db()
    cur = conn.cursor()
    cur.execute(f"INSERT INTO {tablo} ({cols}) VALUES ({placeholders})", list(data.values()))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def kayit_guncelle(tablo: str, record_id: int, data: dict) -> None:
    """Tabloda belirtilen id'li kaydı günceller."""
    data = {k: v for k, v in data.items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="Güncellenecek veri boş olamaz.")
    set_clause = ", ".join([f"{k}=?" for k in data.keys()])
    conn = get_db()
    affected = conn.execute(
        f"UPDATE {tablo} SET {set_clause} WHERE id=?",
        list(data.values()) + [record_id]
    ).rowcount
    conn.commit()
    conn.close()
    if affected == 0:
        raise HTTPException(status_code=404, detail=f"{tablo} içinde id={record_id} bulunamadı.")


def kayit_sil(tablo: str, record_id: int) -> None:
    """Tabloda belirtilen id'li kaydı siler."""
    conn = get_db()
    affected = conn.execute(f"DELETE FROM {tablo} WHERE id=?", (record_id,)).rowcount
    conn.commit()
    conn.close()
    if affected == 0:
        raise HTTPException(status_code=404, detail=f"{tablo} içinde id={record_id} bulunamadı.")


# ─── MODELLER ─────────────────────────────────────────────────────────────────

class KobiModel(BaseModel):
    kullanici_adi: Optional[str] = None
    isletme_adi: Optional[str] = None
    vergi_no: Optional[str] = None
    yetkili_kisi: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None
    adres: Optional[str] = None


class TedarikciModel(BaseModel):
    kobi_id: Optional[int] = 1
    ad: Optional[str] = None
    yetkili: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None
    adres: Optional[str] = None
    vergi_no: Optional[str] = None


class UrunModel(BaseModel):
    kobi_id: Optional[int] = 1
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


class MusteriModel(BaseModel):
    kobi_id: Optional[int] = 1
    ad_soyad: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None
    teslimat_adresi: Optional[str] = None
    notlar: Optional[str] = None


class SiparisModel(BaseModel):
    kobi_id: Optional[int] = 1
    musteri_id: Optional[int] = None
    siparis_no: Optional[str] = None
    toplam_tutar: Optional[float] = None
    durum: Optional[str] = None
    kargo_firmasi: Optional[str] = None
    kargo_takip_no: Optional[str] = None
    teslim_tarihi: Optional[str] = None
    notlar: Optional[str] = None


class SiparisKalemiModel(BaseModel):
    siparis_id: Optional[int] = None
    urun_id: Optional[int] = None
    adet: Optional[float] = None
    birim_fiyat: Optional[float] = None
    ara_toplam: Optional[float] = None


class TedarikAlimModel(BaseModel):
    kobi_id: Optional[int] = 1
    tedarikci_id: Optional[int] = None
    fatura_no: Optional[str] = None
    toplam_tutar: Optional[float] = None


class AlimKalemiModel(BaseModel):
    alim_id: Optional[int] = None
    urun_id: Optional[int] = None
    miktar: Optional[float] = None
    birim_fiyat: Optional[float] = None


class StokHareketiModel(BaseModel):
    urun_id: Optional[int] = None
    tur: Optional[str] = None
    miktar: Optional[float] = None
    onceki_stok: Optional[float] = None
    sonraki_stok: Optional[float] = None
    ilgili_id: Optional[int] = None


class KargoGecikmesiModel(BaseModel):
    siparis_id: Optional[int] = None
    sebep: Optional[str] = None
    musteri_bilgilendirildi: Optional[bool] = False
    yoneticiye_bildirildi: Optional[bool] = False


class HizliSatisModel(BaseModel):
    urun_id: int
    adet: float


# ─── ÖZET ─────────────────────────────────────────────────────────────────────

@app.get("/api/ozet", summary="İşletme özet istatistikleri", tags=["Özet"])
def ozet():
    """Ürün, sipariş, müşteri, tedarikçi ve kritik stok sayılarını döndürür."""
    conn = get_db()
    result = {
        "toplam_urun": conn.execute("SELECT COUNT(*) FROM urunler").fetchone()[0],
        "kritik_stok": conn.execute(
            "SELECT COUNT(*) FROM urunler WHERE stok_miktari <= kritik_stok_esigi"
        ).fetchone()[0],
        "toplam_siparis": conn.execute("SELECT COUNT(*) FROM siparisler").fetchone()[0],
        "toplam_musteri": conn.execute("SELECT COUNT(*) FROM musteriler").fetchone()[0],
        "toplam_tedarikci": conn.execute("SELECT COUNT(*) FROM tedarikciler").fetchone()[0],
        "toplam_alim": conn.execute("SELECT COUNT(*) FROM tedarik_alimlari").fetchone()[0],
    }
    conn.close()
    return result


# ─── KOBILER ──────────────────────────────────────────────────────────────────

@app.get("/api/kobiler", summary="Tüm KOBİ'leri listele", tags=["KOBİ"])
def kobiler_getir():
    return tablo_getir("kobiler")

@app.get("/api/kobiler/{id}", summary="Tek KOBİ getir", tags=["KOBİ"])
def kobi_getir(id: int):
    return kayit_getir("kobiler", id)

@app.post("/api/kobiler", status_code=201, summary="KOBİ ekle", tags=["KOBİ"])
def kobi_ekle(m: KobiModel):
    nid = kayit_ekle("kobiler", m.dict())
    return {"id": nid, "mesaj": "KOBİ eklendi"}

@app.put("/api/kobiler/{id}", summary="KOBİ güncelle", tags=["KOBİ"])
def kobi_guncelle(id: int, m: KobiModel):
    kayit_guncelle("kobiler", id, m.dict())
    return {"mesaj": "KOBİ güncellendi"}

@app.delete("/api/kobiler/{id}", summary="KOBİ sil", tags=["KOBİ"])
def kobi_sil(id: int):
    kayit_sil("kobiler", id)
    return {"mesaj": "KOBİ silindi"}


# ─── TEDARİKÇİLER ─────────────────────────────────────────────────────────────

@app.get("/api/tedarikciler", summary="Tüm tedarikçileri listele", tags=["Tedarikçiler"])
def tedarikciler_getir():
    return tablo_getir("tedarikciler")

@app.get("/api/tedarikciler/{id}", summary="Tek tedarikçi getir", tags=["Tedarikçiler"])
def tedarikci_getir(id: int):
    return kayit_getir("tedarikciler", id)

@app.post("/api/tedarikciler", status_code=201, summary="Tedarikçi ekle", tags=["Tedarikçiler"])
def tedarikci_ekle(m: TedarikciModel):
    nid = kayit_ekle("tedarikciler", m.dict())
    return {"id": nid, "mesaj": "Tedarikçi eklendi"}

@app.put("/api/tedarikciler/{id}", summary="Tedarikçi güncelle", tags=["Tedarikçiler"])
def tedarikci_guncelle(id: int, m: TedarikciModel):
    kayit_guncelle("tedarikciler", id, m.dict())
    return {"mesaj": "Tedarikçi güncellendi"}

@app.delete("/api/tedarikciler/{id}", summary="Tedarikçi sil", tags=["Tedarikçiler"])
def tedarikci_sil(id: int):
    kayit_sil("tedarikciler", id)
    return {"mesaj": "Tedarikçi silindi"}


# ─── ÜRÜNLER ──────────────────────────────────────────────────────────────────

@app.get("/api/urunler", summary="Tüm ürünleri listele", tags=["Ürünler"])
def urunler_getir():
    return tablo_getir("urunler")

@app.get("/api/urunler/kritik", summary="Kritik stok altındaki ürünler", tags=["Ürünler"])
def kritik_stok_urunler():
    """Stok miktarı kritik eşik değerinin altında veya eşit olan ürünleri döndürür."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM urunler WHERE stok_miktari <= kritik_stok_esigi ORDER BY stok_miktari ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/urunler/{id}", summary="Tek ürün getir", tags=["Ürünler"])
def urun_getir(id: int):
    return kayit_getir("urunler", id)

@app.post("/api/urunler", status_code=201, summary="Ürün ekle", tags=["Ürünler"])
def urun_ekle(m: UrunModel):
    nid = kayit_ekle("urunler", m.dict())
    return {"id": nid, "mesaj": "Ürün eklendi"}

@app.put("/api/urunler/{id}", summary="Ürün güncelle", tags=["Ürünler"])
def urun_guncelle(id: int, m: UrunModel):
    kayit_guncelle("urunler", id, m.dict())
    return {"mesaj": "Ürün güncellendi"}

@app.delete("/api/urunler/{id}", summary="Ürün sil", tags=["Ürünler"])
def urun_sil(id: int):
    kayit_sil("urunler", id)
    return {"mesaj": "Ürün silindi"}


# ─── MÜŞTERİLER ───────────────────────────────────────────────────────────────

@app.get("/api/musteriler", summary="Tüm müşterileri listele", tags=["Müşteriler"])
def musteriler_getir():
    return tablo_getir("musteriler")

@app.get("/api/musteriler/{id}", summary="Tek müşteri getir", tags=["Müşteriler"])
def musteri_getir(id: int):
    return kayit_getir("musteriler", id)

@app.post("/api/musteriler", status_code=201, summary="Müşteri ekle", tags=["Müşteriler"])
def musteri_ekle(m: MusteriModel):
    nid = kayit_ekle("musteriler", m.dict())
    return {"id": nid, "mesaj": "Müşteri eklendi"}

@app.put("/api/musteriler/{id}", summary="Müşteri güncelle", tags=["Müşteriler"])
def musteri_guncelle(id: int, m: MusteriModel):
    kayit_guncelle("musteriler", id, m.dict())
    return {"mesaj": "Müşteri güncellendi"}

@app.delete("/api/musteriler/{id}", summary="Müşteri sil", tags=["Müşteriler"])
def musteri_sil(id: int):
    kayit_sil("musteriler", id)
    return {"mesaj": "Müşteri silindi"}


# ─── SİPARİŞLER ───────────────────────────────────────────────────────────────

@app.get("/api/siparisler", summary="Tüm siparişleri listele", tags=["Siparişler"])
def siparisler_getir():
    return tablo_getir("siparisler")

@app.get("/api/siparisler/{id}", summary="Tek sipariş getir", tags=["Siparişler"])
def siparis_getir(id: int):
    return kayit_getir("siparisler", id)

@app.get("/api/siparisler/{id}/kalemler", summary="Siparişe ait kalemleri getir", tags=["Siparişler"])
def siparis_kalemleri_by_siparis(id: int):
    """Belirtilen siparişe ait tüm sipariş kalemlerini döndürür."""
    conn = get_db()
    rows = conn.execute(
        "SELECT sk.*, u.ad as urun_adi, u.urun_kodu FROM siparis_kalemleri sk "
        "LEFT JOIN urunler u ON sk.urun_id = u.id "
        "WHERE sk.siparis_id=?", (id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/siparisler", status_code=201, summary="Sipariş ekle", tags=["Siparişler"])
def siparis_ekle(m: SiparisModel):
    nid = kayit_ekle("siparisler", m.dict())
    return {"id": nid, "mesaj": "Sipariş eklendi"}

@app.put("/api/siparisler/{id}", summary="Sipariş güncelle", tags=["Siparişler"])
def siparis_guncelle(id: int, m: SiparisModel):
    kayit_guncelle("siparisler", id, m.dict())
    return {"mesaj": "Sipariş güncellendi"}

@app.delete("/api/siparisler/{id}", summary="Sipariş sil", tags=["Siparişler"])
def siparis_sil(id: int):
    kayit_sil("siparisler", id)
    return {"mesaj": "Sipariş silindi"}


# ─── SİPARİŞ KALEMLERİ ────────────────────────────────────────────────────────

@app.get("/api/siparis_kalemleri", summary="Tüm sipariş kalemlerini listele", tags=["Sipariş Kalemleri"])
def siparis_kalemleri_getir():
    return tablo_getir("siparis_kalemleri")

@app.get("/api/siparis_kalemleri/{id}", summary="Tek sipariş kalemi getir", tags=["Sipariş Kalemleri"])
def siparis_kalemi_getir(id: int):
    return kayit_getir("siparis_kalemleri", id)

@app.post("/api/siparis_kalemleri", status_code=201, summary="Sipariş kalemi ekle", tags=["Sipariş Kalemleri"])
def siparis_kalemi_ekle(m: SiparisKalemiModel):
    nid = kayit_ekle("siparis_kalemleri", m.dict())
    return {"id": nid, "mesaj": "Sipariş kalemi eklendi"}

@app.put("/api/siparis_kalemleri/{id}", summary="Sipariş kalemi güncelle", tags=["Sipariş Kalemleri"])
def siparis_kalemi_guncelle(id: int, m: SiparisKalemiModel):
    kayit_guncelle("siparis_kalemleri", id, m.dict())
    return {"mesaj": "Sipariş kalemi güncellendi"}

@app.delete("/api/siparis_kalemleri/{id}", summary="Sipariş kalemi sil", tags=["Sipariş Kalemleri"])
def siparis_kalemi_sil(id: int):
    kayit_sil("siparis_kalemleri", id)
    return {"mesaj": "Sipariş kalemi silindi"}


# ─── TEDARİK ALIMLARI ─────────────────────────────────────────────────────────

@app.get("/api/tedarik_alimlari", summary="Tüm tedarik alımlarını listele", tags=["Tedarik Alımları"])
def tedarik_alimlari_getir():
    return tablo_getir("tedarik_alimlari")

@app.get("/api/tedarik_alimlari/{id}", summary="Tek tedarik alımı getir", tags=["Tedarik Alımları"])
def tedarik_alimi_getir(id: int):
    return kayit_getir("tedarik_alimlari", id)

@app.get("/api/tedarik_alimlari/{id}/kalemler", summary="Alıma ait kalemleri getir", tags=["Tedarik Alımları"])
def alim_kalemleri_by_alim(id: int):
    """Belirtilen tedarik alımına ait tüm alım kalemlerini döndürür."""
    conn = get_db()
    rows = conn.execute(
        "SELECT ak.*, u.ad as urun_adi, u.urun_kodu FROM alim_kalemleri ak "
        "LEFT JOIN urunler u ON ak.urun_id = u.id "
        "WHERE ak.alim_id=?", (id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/tedarik_alimlari", status_code=201, summary="Tedarik alımı ekle", tags=["Tedarik Alımları"])
def tedarik_alimi_ekle(m: TedarikAlimModel):
    nid = kayit_ekle("tedarik_alimlari", m.dict())
    return {"id": nid, "mesaj": "Tedarik alımı eklendi"}

@app.put("/api/tedarik_alimlari/{id}", summary="Tedarik alımı güncelle", tags=["Tedarik Alımları"])
def tedarik_alimi_guncelle(id: int, m: TedarikAlimModel):
    kayit_guncelle("tedarik_alimlari", id, m.dict())
    return {"mesaj": "Tedarik alımı güncellendi"}

@app.delete("/api/tedarik_alimlari/{id}", summary="Tedarik alımı sil", tags=["Tedarik Alımları"])
def tedarik_alimi_sil(id: int):
    kayit_sil("tedarik_alimlari", id)
    return {"mesaj": "Tedarik alımı silindi"}


# ─── ALIM KALEMLERİ ───────────────────────────────────────────────────────────

@app.get("/api/alim_kalemleri", summary="Tüm alım kalemlerini listele", tags=["Alım Kalemleri"])
def alim_kalemleri_getir():
    return tablo_getir("alim_kalemleri")

@app.get("/api/alim_kalemleri/{id}", summary="Tek alım kalemi getir", tags=["Alım Kalemleri"])
def alim_kalemi_getir(id: int):
    return kayit_getir("alim_kalemleri", id)

@app.post("/api/alim_kalemleri", status_code=201, summary="Alım kalemi ekle", tags=["Alım Kalemleri"])
def alim_kalemi_ekle(m: AlimKalemiModel):
    nid = kayit_ekle("alim_kalemleri", m.dict())
    return {"id": nid, "mesaj": "Alım kalemi eklendi"}

@app.put("/api/alim_kalemleri/{id}", summary="Alım kalemi güncelle", tags=["Alım Kalemleri"])
def alim_kalemi_guncelle(id: int, m: AlimKalemiModel):
    kayit_guncelle("alim_kalemleri", id, m.dict())
    return {"mesaj": "Alım kalemi güncellendi"}

@app.delete("/api/alim_kalemleri/{id}", summary="Alım kalemi sil", tags=["Alım Kalemleri"])
def alim_kalemi_sil(id: int):
    kayit_sil("alim_kalemleri", id)
    return {"mesaj": "Alım kalemi silindi"}


# ─── STOK HAREKETLERİ ─────────────────────────────────────────────────────────

@app.get("/api/stok_hareketleri", summary="Tüm stok hareketlerini listele", tags=["Stok Hareketleri"])
def stok_hareketleri_getir():
    return tablo_getir("stok_hareketleri")

@app.get("/api/stok_hareketleri/urun/{urun_id}", summary="Ürüne ait stok hareketleri", tags=["Stok Hareketleri"])
def stok_hareketleri_by_urun(urun_id: int):
    """Belirtilen ürüne ait tüm stok hareketlerini döndürür."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM stok_hareketleri WHERE urun_id=? ORDER BY id DESC", (urun_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/stok_hareketleri/{id}", summary="Tek stok hareketi getir", tags=["Stok Hareketleri"])
def stok_hareketi_getir(id: int):
    return kayit_getir("stok_hareketleri", id)

@app.post("/api/stok_hareketleri", status_code=201, summary="Stok hareketi ekle", tags=["Stok Hareketleri"])
def stok_hareketi_ekle(m: StokHareketiModel):
    nid = kayit_ekle("stok_hareketleri", m.dict())
    return {"id": nid, "mesaj": "Stok hareketi eklendi"}

@app.put("/api/stok_hareketleri/{id}", summary="Stok hareketi güncelle", tags=["Stok Hareketleri"])
def stok_hareketi_guncelle(id: int, m: StokHareketiModel):
    kayit_guncelle("stok_hareketleri", id, m.dict())
    return {"mesaj": "Stok hareketi güncellendi"}

@app.delete("/api/stok_hareketleri/{id}", summary="Stok hareketi sil", tags=["Stok Hareketleri"])
def stok_hareketi_sil(id: int):
    kayit_sil("stok_hareketleri", id)
    return {"mesaj": "Stok hareketi silindi"}


# ─── KARGO GECİKMELERİ ────────────────────────────────────────────────────────

@app.get("/api/kargo_gecikmeleri", summary="Tüm kargo gecikmelerini listele", tags=["Kargo Gecikmeleri"])
def kargo_gecikmeleri_getir():
    return tablo_getir("kargo_gecikmeleri")

@app.get("/api/kargo_gecikmeleri/{id}", summary="Tek kargo gecikmesi getir", tags=["Kargo Gecikmeleri"])
def kargo_gecikmesi_getir(id: int):
    return kayit_getir("kargo_gecikmeleri", id)

@app.post("/api/kargo_gecikmeleri", status_code=201, summary="Kargo gecikmesi ekle", tags=["Kargo Gecikmeleri"])
def kargo_gecikmesi_ekle(m: KargoGecikmesiModel):
    nid = kayit_ekle("kargo_gecikmeleri", m.dict())
    return {"id": nid, "mesaj": "Kargo gecikmesi eklendi"}

@app.put("/api/kargo_gecikmeleri/{id}", summary="Kargo gecikmesi güncelle", tags=["Kargo Gecikmeleri"])
def kargo_gecikmesi_guncelle(id: int, m: KargoGecikmesiModel):
    kayit_guncelle("kargo_gecikmeleri", id, m.dict())
    return {"mesaj": "Kargo gecikmesi güncellendi"}

@app.delete("/api/kargo_gecikmeleri/{id}", summary="Kargo gecikmesi sil", tags=["Kargo Gecikmeleri"])
def kargo_gecikmesi_sil(id: int):
    kayit_sil("kargo_gecikmeleri", id)
    return {"mesaj": "Kargo gecikmesi silindi"}


# ─── HIZLI SATIŞ (ELDEN SATIŞ) ────────────────────────────────────────────────

@app.post("/api/hizli_satis", summary="Fiziksel mağaza / elden satış - stok düş", tags=["Özel İşlemler"])
def hizli_satis(m: HizliSatisModel):
    """
    Fiziksel mağaza satışı için tek adımda:
    1. Ürünün mevcut stokunu kontrol eder.
    2. Yeterli stok varsa stok miktarını düşürür.
    3. Stok hareketi kaydı oluşturur.
    Yetersiz stok durumunda 400 hatası döndürür.
    """
    conn = get_db()
    urun = conn.execute("SELECT * FROM urunler WHERE id=?", (m.urun_id,)).fetchone()

    if urun is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Ürün bulunamadı: id={m.urun_id}")

    urun = dict(urun)
    mevcut_stok = urun["stok_miktari"]

    if m.adet <= 0:
        conn.close()
        raise HTTPException(status_code=400, detail="Satış adedi 0'dan büyük olmalıdır.")

    if mevcut_stok < m.adet:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Yetersiz stok. Mevcut: {mevcut_stok}, İstenen: {m.adet}"
        )

    yeni_stok = mevcut_stok - m.adet

    # Stok güncelle
    conn.execute(
        "UPDATE urunler SET stok_miktari=? WHERE id=?",
        (yeni_stok, m.urun_id)
    )

    # Stok hareketi kaydet
    conn.execute(
        "INSERT INTO stok_hareketleri (urun_id, tur, miktar, onceki_stok, sonraki_stok) "
        "VALUES (?, ?, ?, ?, ?)",
        (m.urun_id, "ÇIKIŞ", m.adet, mevcut_stok, yeni_stok)
    )

    conn.commit()
    conn.close()

    kritik_uyari = yeni_stok <= urun["kritik_stok_esigi"]

    return {
        "mesaj": f"{urun['ad']} ürününden {m.adet} adet satıldı.",
        "urun_id": m.urun_id,
        "onceki_stok": mevcut_stok,
        "yeni_stok": yeni_stok,
        "kritik_stok_uyarisi": kritik_uyari,
    }


# ─── STOK ARTIR (TEDARİK GİRİŞİ) ─────────────────────────────────────────────

@app.post("/api/stok_artir", summary="Manuel stok artırma (tedarik girişi)", tags=["Özel İşlemler"])
def stok_artir(urun_id: int, miktar: float):
    """
    Belirtilen ürünün stok miktarını artırır ve stok hareketi kaydı oluşturur.
    Tedarik alımı dışında manuel stok düzeltmeleri için kullanılır.
    """
    if miktar <= 0:
        raise HTTPException(status_code=400, detail="Miktar 0'dan büyük olmalıdır.")

    conn = get_db()
    urun = conn.execute("SELECT * FROM urunler WHERE id=?", (urun_id,)).fetchone()

    if urun is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Ürün bulunamadı: id={urun_id}")

    urun = dict(urun)
    mevcut_stok = urun["stok_miktari"]
    yeni_stok = mevcut_stok + miktar

    conn.execute("UPDATE urunler SET stok_miktari=? WHERE id=?", (yeni_stok, urun_id))
    conn.execute(
        "INSERT INTO stok_hareketleri (urun_id, tur, miktar, onceki_stok, sonraki_stok) "
        "VALUES (?, ?, ?, ?, ?)",
        (urun_id, "GİRİŞ", miktar, mevcut_stok, yeni_stok)
    )
    conn.commit()
    conn.close()

    return {
        "mesaj": f"{urun['ad']} ürününe {miktar} adet eklendi.",
        "urun_id": urun_id,
        "onceki_stok": mevcut_stok,
        "yeni_stok": yeni_stok,
    }

# --- YAPAY ZEKA TAHMİNLERİ ---

@app.get("/api/tahmin/genel", summary="Genel Ciro Tahmini", tags=["Tahmin"])
def genel_tahmin_getir(gun_sayisi: int = 14):
    """Prophet modeli ile gelecek X günün genel ciro trendini döndürür."""
    sonuc = get_overall_revenue_forecast(days=gun_sayisi)
    return sonuc

@app.get("/api/tahmin/urunler", summary="Ürün Bazlı Satış Tahminleri", tags=["Tahmin"])
def urun_tahmin_getir(gun_sayisi: int = 14):
    """Tüm ürünler için gelecek X günlük satış trendi ve miktar tahminlerini döndürür."""
    sonuc = get_all_products_forecast(days=gun_sayisi)
    return sonuc


# ─── FRONTEND (HTML) ──────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    """
    HTML arayüzünü döndürür. index.html dosyası proje kök dizininde bulunmalıdır.
    Dosya bulunamazsa basit bir yönlendirme sayfası gösterilir.
    """
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return HTMLResponse(
        content="""
        <html><body style="font-family:sans-serif;padding:40px;background:#f8f9fa">
        <h2>KOBİ Yönetim Sistemi API</h2>
        <p>API çalışıyor. Dokümantasyon için:
        <a href="/docs">/docs</a> (Swagger) veya
        <a href="/redoc">/redoc</a> (ReDoc)</p>
        <p>index.html bulunamadı. Lütfen proje kök dizinine yerleştirin.</p>
        </body></html>
        """,
        status_code=200
    )