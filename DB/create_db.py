import sqlite3
import os
import random
from datetime import datetime, timedelta

def veritabani_olustur():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, 'SME_DB.db')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON;')
    # 1. KOBİ'ler
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS kobiler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kullanici_adi VARCHAR(50),
        isletme_adi VARCHAR(100),
        vergi_no VARCHAR(20),
        yetkili_kisi VARCHAR(100),
        telefon VARCHAR(20),
        email VARCHAR(100),
        adres TEXT,
        kayit_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # 2. Tedarikçiler
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tedarikciler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kobi_id INTEGER,
        ad VARCHAR(100),
        yetkili VARCHAR(100),
        telefon VARCHAR(20),
        email VARCHAR(100),
        adres TEXT,
        vergi_no VARCHAR(20),
        FOREIGN KEY(kobi_id) REFERENCES kobiler(id)
    )''')

    # 3. Ürünler
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS urunler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kobi_id INTEGER,
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
        son_guncelleme DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(kobi_id) REFERENCES kobiler(id)
    )''')

    # 4. Müşteriler
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS musteriler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kobi_id INTEGER,
        ad_soyad VARCHAR(100),
        telefon VARCHAR(20),
        email VARCHAR(100),
        teslimat_adresi TEXT,
        notlar TEXT,
        FOREIGN KEY(kobi_id) REFERENCES kobiler(id)
    )''')

    # 5. Siparişler
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS siparisler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kobi_id INTEGER,
        musteri_id INTEGER,
        siparis_no VARCHAR(30),
        tarih DATETIME DEFAULT CURRENT_TIMESTAMP,
        toplam_tutar DECIMAL(10,2),
        durum VARCHAR(20),
        kargo_firmasi VARCHAR(50),
        kargo_takip_no VARCHAR(50),
        teslim_tarihi DATE,
        notlar TEXT,
        FOREIGN KEY(kobi_id) REFERENCES kobiler(id),
        FOREIGN KEY(musteri_id) REFERENCES musteriler(id)
    )''')

    # 6. Sipariş Kalemleri
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS siparis_kalemleri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        siparis_id INTEGER,
        urun_id INTEGER,
        adet DECIMAL(10,2),
        birim_fiyat DECIMAL(10,2),
        ara_toplam DECIMAL(10,2),
        FOREIGN KEY(siparis_id) REFERENCES siparisler(id),
        FOREIGN KEY(urun_id) REFERENCES urunler(id)
    )''')

    # 7. Tedarik Alımları
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tedarik_alimlari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kobi_id INTEGER,
        tedarikci_id INTEGER,
        tarih DATETIME DEFAULT CURRENT_TIMESTAMP,
        fatura_no VARCHAR(50),
        toplam_tutar DECIMAL(10,2),
        FOREIGN KEY(kobi_id) REFERENCES kobiler(id),
        FOREIGN KEY(tedarikci_id) REFERENCES tedarikciler(id)
    )''')

    # 8. Alım Kalemleri
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS alim_kalemleri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alim_id INTEGER,
        urun_id INTEGER,
        miktar DECIMAL(10,2),
        birim_fiyat DECIMAL(10,2),
        FOREIGN KEY(alim_id) REFERENCES tedarik_alimlari(id),
        FOREIGN KEY(urun_id) REFERENCES urunler(id)
    )''')

    # 9. Stok Hareketleri
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stok_hareketleri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        urun_id INTEGER,
        tur VARCHAR(20),
        miktar DECIMAL(10,2),
        onceki_stok DECIMAL(10,2),
        sonraki_stok DECIMAL(10,2),
        ilgili_id INTEGER,
        tarih DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(urun_id) REFERENCES urunler(id)
    )''')

    # 10. Kargo Gecikmeleri
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS kargo_gecikmeleri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        siparis_id INTEGER,
        tespit_tarihi DATETIME DEFAULT CURRENT_TIMESTAMP,
        sebep VARCHAR(255),
        musteri_bilgilendirildi BOOLEAN,
        yoneticiye_bildirildi BOOLEAN,
        FOREIGN KEY(siparis_id) REFERENCES siparisler(id)
    )''')

    # Örnek Veri
    cursor.execute("INSERT OR IGNORE INTO kobiler (id, isletme_adi) VALUES (1, 'Kavanozcu Abi Kooperatifi')")
    cursor.execute("INSERT OR IGNORE INTO urunler (id, kobi_id, urun_kodu, ad, kategori, birim, stok_miktari, kritik_stok_esigi, satis_fiyati) VALUES (1, 1, 'KAV-01', 'Ev Yapımı Çilek Reçeli', 'Gıda', 'adet', 120, 50, 150.00)")
    cursor.execute("INSERT OR IGNORE INTO urunler (id, kobi_id, urun_kodu, ad, kategori, birim, stok_miktari, kritik_stok_esigi, satis_fiyati) VALUES (2, 1, 'ORG-05', 'Organik Domates', 'Tarım', 'kg', 30, 50, 45.00)")
    cursor.execute("INSERT OR IGNORE INTO musteriler (id, kobi_id, ad_soyad) VALUES (1, 1, 'Ahmet Yılmaz')")
    cursor.execute("INSERT OR IGNORE INTO musteriler (id, kobi_id, ad_soyad) VALUES (2, 1, 'Mehmet Demir')")
    cursor.execute("INSERT OR IGNORE INTO tedarikciler (id, kobi_id, ad) VALUES (1, 1, 'Çilek Bahçesi Tedarikçileri')")
    cursor.execute("INSERT OR IGNORE INTO tedarikciler (id, kobi_id, ad) VALUES (2, 1, 'Domates Üreticileri Birliği')")
    cursor.execute("INSERT OR IGNORE INTO siparisler (id, kobi_id, musteri_id, siparis_no, toplam_tutar, durum) VALUES (1, 1, 1, 'SIP-1001', 300.00, 'Hazırlanıyor')")
    cursor.execute("INSERT OR IGNORE INTO siparis_kalemleri (id, siparis_id, urun_id, adet, birim_fiyat, ara_toplam) VALUES (1, 1, 1, 2, 150.00, 300.00)")
    cursor.execute("INSERT OR IGNORE INTO tedarik_alimlari (id, kobi_id, tedarikci_id, fatura_no, toplam_tutar) VALUES (1, 1, 1, 'FAT-5001', 200.00)")
    cursor.execute("INSERT OR IGNORE INTO alim_kalemleri (id, alim_id, urun_id, miktar, birim_fiyat) VALUES (1, 1, 1, 10, 20.00)")
    cursor.execute("INSERT OR IGNORE INTO stok_hareketleri (id, urun_id, tur, miktar, onceki_stok, sonraki_stok, ilgili_id) VALUES (1, 1, 'Alım', 10, 120, 130, 1)")
    cursor.execute("INSERT OR IGNORE INTO stok_hareketleri (id, urun_id, tur, miktar, onceki_stok, sonraki_stok, ilgili_id) VALUES (2, 1, 'Satış', 2, 130, 128, 1)")
    cursor.execute("INSERT OR IGNORE INTO kargo_gecikmeleri (id, siparis_id, sebep, musteri_bilgilendirildi, yoneticiye_bildirildi) VALUES (1, 1, 'Yoğunluk nedeniyle kargo gecikmesi', 1, 1)")
    cursor.execute("INSERT OR IGNORE INTO kargo_gecikmeleri (id, siparis_id, sebep, musteri_bilgilendirildi, yoneticiye_bildirildi) VALUES (2, 1, 'Hava koşulları nedeniyle gecikme', 1, 1)")
    bugun = datetime.now()
    baslangic_tarihi = bugun - timedelta(days=180)

# --- 1. RASTGELE SİPARİŞ (SATIŞ) VERİLERİ ---
    for i in range(1, 200):  # 200 adet rastgele sipariş oluştur
        rastgele_gun = random.randint(0, 180)
        islem_tarihi = baslangic_tarihi + timedelta(days=rastgele_gun)
        tarih_str = islem_tarihi.strftime('%Y-%m-%d %H:%M:%S')
        
        musteri_id = random.choice([1, 2])
        urun_id = random.choice([1, 2])
        adet = random.randint(1, 10)  # 1 ile 10 arası satılsın
        birim_fiyat = 150.00 if urun_id == 1 else 45.00
        toplam_tutar = adet * birim_fiyat
        siparis_no = f"SIP-{1000 + i}"
        durum = random.choice(['Teslim Edildi', 'Teslim Edildi', 'Teslim Edildi', 'Kargoda', 'Hazırlanıyor'])
        
        # Siparişler Tablosu
        cursor.execute(f"""
            INSERT INTO siparisler (kobi_id, musteri_id, siparis_no, tarih, toplam_tutar, durum) 
            VALUES (1, {musteri_id}, '{siparis_no}', '{tarih_str}', {toplam_tutar}, '{durum}')
        """)
        
        cursor.execute("SELECT last_insert_rowid()")
        siparis_id = cursor.fetchone()[0]
        
        # Sipariş Kalemleri Tablosu
        cursor.execute(f"""
            INSERT INTO siparis_kalemleri (siparis_id, urun_id, adet, birim_fiyat, ara_toplam) 
            VALUES ({siparis_id}, {urun_id}, {adet}, {birim_fiyat}, {toplam_tutar})
        """)
        
        # Stok Hareketleri (Satış - Çıkış)
        cursor.execute(f"""
            INSERT INTO stok_hareketleri (urun_id, tur, miktar, tarih, ilgili_id) 
            VALUES ({urun_id}, 'Satış', {adet}, '{tarih_str}', {siparis_id})
        """)

    # --- 2. RASTGELE TEDARİK (ALIM) VERİLERİ ---
    for i in range(1, 40):  # 40 adet tedarik alımı
        rastgele_gun = random.randint(0, 180)
        islem_tarihi = baslangic_tarihi + timedelta(days=rastgele_gun)
        tarih_str = islem_tarihi.strftime('%Y-%m-%d %H:%M:%S')
        
        tedarikci_id = random.choice([1, 2])
        urun_id = 1 if tedarikci_id == 1 else 2
        miktar = random.randint(30, 150) # Toptan alım
        birim_fiyat = 20.00 if urun_id == 1 else 10.00
        toplam_tutar = miktar * birim_fiyat
        fatura_no = f"FAT-{5000 + i}"
        
        # Tedarik Alımları Tablosu
        cursor.execute(f"""
            INSERT INTO tedarik_alimlari (kobi_id, tedarikci_id, tarih, fatura_no, toplam_tutar) 
            VALUES (1, {tedarikci_id}, '{tarih_str}', '{fatura_no}', {toplam_tutar})
        """)
        
        cursor.execute("SELECT last_insert_rowid()")
        alim_id = cursor.fetchone()[0]
        
        # Alım Kalemleri Tablosu
        cursor.execute(f"""
            INSERT INTO alim_kalemleri (alim_id, urun_id, miktar, birim_fiyat) 
            VALUES ({alim_id}, {urun_id}, {miktar}, {birim_fiyat})
        """)
        
        # Stok Hareketleri (Alım - Giriş)
        cursor.execute(f"""
            INSERT INTO stok_hareketleri (urun_id, tur, miktar, tarih, ilgili_id) 
            VALUES ({urun_id}, 'Alım', {miktar}, '{tarih_str}', {alim_id})
        """)
    conn.commit()
    conn.close()
    print("Veritabanı başarıyla oluşturuldu!")

if __name__ == "__main__": 
    veritabani_olustur()