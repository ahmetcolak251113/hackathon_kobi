import os
import sqlite3
import pandas as pd
from prophet import Prophet

# Dosya Statistics klasöründe. Bir üst dizine çıkıp DB'ye gireceğiz.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(BASE_DIR, 'DB', 'SME_DB.db')

def fetch_data(query, params=()):
    with sqlite3.connect(DB_PATH, timeout=30.0) as conn:
        return pd.read_sql_query(query, conn, params=params)

def train_and_predict(df, periods=30):
    if df.empty or len(df) < 5:
        return {"error": "Modeli egitmek icin yeterli veri yok."}

    model = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
    model.fit(df)

    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)
    result_df = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)

    start_val = result_df['yhat'].iloc[0]
    end_val = result_df['yhat'].iloc[-1]
    trend = "Pozitif" if end_val > start_val else "Negatif"

    return {
        "trend": trend,
        "baslangic_tahmini": round(start_val, 2),
        "bitis_tahmini": round(end_val, 2),
        "degisim_orani": round(((end_val - start_val) / start_val) * 100, 2) if start_val > 0 else 0,
        "detayli_tahmin": result_df.to_dict('records')
    }

def get_overall_revenue_forecast(days=30):
    query = """
        SELECT DATE(sh.tarih) as ds, SUM(sh.miktar * u.satis_fiyati) as y
        FROM stok_hareketleri sh
        JOIN urunler u ON sh.urun_id = u.id
        WHERE sh.tur = 'Satis'
        GROUP BY DATE(sh.tarih)
        ORDER BY ds ASC
    """
    df = fetch_data(query)
    return train_and_predict(df, periods=days)

def get_product_sales_forecast(urun_id, days=30):
    query = """
        SELECT DATE(tarih) as ds, SUM(miktar) as y
        FROM stok_hareketleri
        WHERE urun_id = ? AND tur = 'Satis'
        GROUP BY DATE(tarih)
        ORDER BY ds ASC
    """
    df = fetch_data(query, params=(urun_id,))
    return train_and_predict(df, periods=days)

def get_all_products_forecast(days=30):
    query_urunler = "SELECT id, urun_kodu, ad FROM urunler"
    urunler_df = fetch_data(query_urunler)
    sonuclar = []
    for index, row in urunler_df.iterrows():
        tahmin = get_product_sales_forecast(urun_id=row['id'], days=days)
        sonuclar.append({"urun_id": row['id'], "urun_kodu": row['urun_kodu'], "urun_adi": row['ad'], "tahmin_verisi": tahmin})
    return sonuclar

def get_product_sales_statistics(urun_id):
    query = """
        SELECT DATE(tarih) as gun, SUM(miktar) as gunluk_satis, COUNT(*) as islem_sayisi
        FROM stok_hareketleri WHERE urun_id = ? AND tur = 'Satis' GROUP BY DATE(tarih) ORDER BY gun ASC
    """
    df = fetch_data(query, params=(urun_id,))
    if df.empty: return {"error": "Veri yok."}
    return {
        "toplam_satis": float(df['gunluk_satis'].sum()),
        "ortalama_gunluk_satis": round(float(df['gunluk_satis'].mean()), 2),
        "aktif_satis_gunu": int(len(df))
    }

def get_all_products_statistics():
    query_urunler = "SELECT id, urun_kodu, ad FROM urunler"
    urunler_df = fetch_data(query_urunler)
    sonuclar = []
    for index, row in urunler_df.iterrows():
        stats = get_product_sales_statistics(urun_id=row['id'])
        sonuclar.append({"urun_id": row['id'], "urun_adi": row['ad'], "istatistik": stats})
    return sonuclar