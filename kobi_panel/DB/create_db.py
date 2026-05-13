import sqlite3
import os
import random
from datetime import datetime, timedelta

# create_db.py DB klasörü içinde olduğu için, veritabanını doğrudan bulunduğu yere kuruyoruz.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, 'SME_DB.db')

def veritabani_olustur():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON;')

    # 1. Tedarikçiler
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tedarikciler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad VARCHAR(100),
        yetkili VARCHAR(100),
        telefon VARCHAR(20),
        email VARCHAR(100),
        adres TEXT,
        vergi_no VARCHAR(20)
    )''')

    # 2. Ürünler
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS urunler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        urun_kodu VARCHAR(50),
        ad VARCHAR(200),
        kategori VARCHAR(50),
        birim VARCHAR(20),
        stok_miktari DECIMAL(10,2),
        kritik_stok_esigi DECIMAL(10,2),
        alis_fiyati DECIMAL(10,2),
        satis_fiyati DECIMAL(10,2),
        birim_agirlik DECIMAL(8,2),
        aciklama TEXT,
        son_guncelleme DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # 3. Depo Malzemeleri
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS depo_malzemeleri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tedarikci_id INTEGER,
        malzeme_kodu VARCHAR(50),
        ad VARCHAR(200),
        birim VARCHAR(20),
        stok_miktari DECIMAL(10,2),
        kritik_stok_esigi DECIMAL(10,2) DEFAULT 0,
        birim_fiyati DECIMAL(10,2),
        son_guncelleme DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tedarikci_id) REFERENCES tedarikciler(id)
    )''')

    # 4. Müşteriler
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS musteriler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad_soyad VARCHAR(100),
        telefon VARCHAR(20),
        email VARCHAR(100),
        teslimat_adresi TEXT,
        notlar TEXT
    )''')

    # 5. Stok Hareketleri
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stok_hareketleri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        urun_id INTEGER,
        tur VARCHAR(20),
        miktar DECIMAL(10,2),
        onceki_stok DECIMAL(10,2),
        sonraki_stok DECIMAL(10,2),
        ilgili_id INTEGER,
        tarih DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # 6. Kargo Takip
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS kargo_takip (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        musteri_id INTEGER,
        kargo_no VARCHAR(50),
        durum VARCHAR(50),
        beklenen_teslimat DATETIME,
        son_guncelleme DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(musteri_id) REFERENCES musteriler(id)
    )''')

    # --- Örnek Statik Veriler ---
    cursor.execute("INSERT OR IGNORE INTO tedarikciler (id, ad, yetkili, telefon, email) VALUES (1, 'Cilek Bahcesi Tedarikcileri', 'Ahmet Celik', '05321111111', 'iletisim@cilekbahcesi.com')")
    cursor.execute("INSERT OR IGNORE INTO tedarikciler (id, ad, yetkili, telefon, email) VALUES (2, 'Domates Ureticileri Birligi', 'Mehmet Kara', '05322222222', 'satis@domatesbirligi.com')")
    cursor.execute("INSERT OR IGNORE INTO tedarikciler (id, ad, yetkili, telefon, email) VALUES (3, 'Toptan Ambalaj Dunyasi', 'Fatma Yildiz', '05323333333', 'info@ambalajdunyasi.com')")

    cursor.execute("INSERT OR IGNORE INTO urunler (id, urun_kodu, ad, kategori, birim, stok_miktari, kritik_stok_esigi, alis_fiyati, satis_fiyati) VALUES (1, 'KAV-01', 'Ev Yapimi Cilek Receli', 'Gida', 'adet', 30, 50, 80.00, 150.00)")
    cursor.execute("INSERT OR IGNORE INTO urunler (id, urun_kodu, ad, kategori, birim, stok_miktari, kritik_stok_esigi, alis_fiyati, satis_fiyati) VALUES (2, 'ORG-05', 'Organik Domates', 'Tarim', 'kg', 120, 50, 25.00, 45.00)")
    cursor.execute("INSERT OR IGNORE INTO urunler (id, urun_kodu, ad, kategori, birim, stok_miktari, kritik_stok_esigi, alis_fiyati, satis_fiyati) VALUES (3, 'SOS-03', 'Domates Sosu (Kavanoz)', 'Gida', 'adet', 80, 30, 40.00, 90.00)")

    cursor.execute("INSERT OR IGNORE INTO depo_malzemeleri (id, tedarikci_id, malzeme_kodu, ad, birim, stok_miktari, kritik_stok_esigi, birim_fiyati) VALUES (1, 3, 'AMB-01', 'Cam Kavanoz 500ml', 'adet', 450, 100, 5.50)")
    cursor.execute("INSERT OR IGNORE INTO depo_malzemeleri (id, tedarikci_id, malzeme_kodu, ad, birim, stok_miktari, kritik_stok_esigi, birim_fiyati) VALUES (2, 3, 'AMB-02', 'Metal Kapak (Siyah)', 'adet', 500, 150, 1.25)")

    cursor.execute("INSERT OR IGNORE INTO musteriler (id, ad_soyad, telefon) VALUES (1, 'Ahmet Yilmaz', '05551234567')")
    cursor.execute("INSERT OR IGNORE INTO musteriler (id, ad_soyad, telefon) VALUES (2, 'Mehmet Demir', '05329876543')")

    cursor.execute("INSERT OR IGNORE INTO kargo_takip (musteri_id, kargo_no, durum, beklenen_teslimat) VALUES (1, 'TR84736291', 'Subede Bekliyor', '2024-05-15')")
    cursor.execute("INSERT OR IGNORE INTO kargo_takip (musteri_id, kargo_no, durum, beklenen_teslimat) VALUES (2, 'TR91827364', 'Gecikme', '2024-05-12')")

    # Rastgele Stok Hareketleri
    bugun = datetime.now()
    baslangic_tarihi = bugun - timedelta(days=180)
    for i in range(1, 200):
        rastgele_gun = random.randint(0, 180)
        islem_tarihi = baslangic_tarihi + timedelta(days=rastgele_gun)
        tarih_str = islem_tarihi.strftime('%Y-%m-%d %H:%M:%S')
        urun_id = random.choice([1, 2, 3])
        adet = random.randint(1, 10)
        cursor.execute(
            f"INSERT INTO stok_hareketleri (urun_id, tur, miktar, onceki_stok, sonraki_stok, ilgili_id, tarih) "
            f"VALUES ({urun_id}, 'Satis', {adet}, 0, 0, 0, '{tarih_str}')"
        )

    conn.commit()
    conn.close()
    print(f"Veritabanı başarıyla oluşturuldu! Yol: {DB_PATH}")

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Eski veritabanı silindi.")
    veritabani_olustur()