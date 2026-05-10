import os
import sqlite3
import pandas as pd
from prophet import Prophet

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(BASE_DIR, 'DB', 'SME_DB.db')

def fetch_data(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn, params=params)

def train_and_predict(df, periods=30):
    if df.empty or len(df) < 5:
        return {"error": "Modeli eğitmek için yeterli veri yok."}

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
        SELECT DATE(tarih) as ds, SUM(toplam_tutar) as y
        FROM siparisler
        WHERE durum != 'İptal'
        GROUP BY DATE(tarih)
        ORDER BY ds ASC
    """
    df = fetch_data(query)
    return train_and_predict(df, periods=days)

def get_product_sales_forecast(urun_id, days=30):
    query = """
        SELECT DATE(s.tarih) as ds, SUM(sk.adet) as y
        FROM siparisler s
        JOIN siparis_kalemleri sk ON s.id = sk.siparis_id
        WHERE sk.urun_id = ? AND s.durum != 'İptal'
        GROUP BY DATE(s.tarih)
        ORDER BY ds ASC
    """
    df = fetch_data(query, params=(urun_id,))
    return train_and_predict(df, periods=days)

def get_all_products_forecast(days=30):
    query_urunler = "SELECT id, urun_kodu, ad FROM urunler"
    urunler_df = fetch_data(query_urunler)
    sonuclar = []
    
    for index, row in urunler_df.iterrows():
        urun_id = row['id']
        urun_kodu = row['urun_kodu']
        urun_adi = row['ad']
        tahmin = get_product_sales_forecast(urun_id=urun_id, days=days)
        sonuclar.append({
            "urun_id": urun_id,
            "urun_kodu": urun_kodu,
            "urun_adi": urun_adi,
            "tahmin_verisi": tahmin
        })
        
    return sonuclar



if __name__ == "__main__":
    print("=" * 50)
    print("GENEL CİRO TAHMİNİ ÇALIŞTIRILIYOR...")
    print("=" * 50)
    genel_tahmin = get_overall_revenue_forecast(days=14)
    print(f"Genel Trend: {genel_tahmin.get('trend')}")
    print(f"Değişim: %{genel_tahmin.get('degisim_orani')}\n")

    print("=" * 50)
    print("TÜM ÜRÜNLER İÇİN SATIŞ TAHMİNLERİ HESAPLANIYOR...")
    print("=" * 50)

    tum_urunler_raporu = get_all_products_forecast(days=14)
    
    for urun in tum_urunler_raporu:
        print(f"Ürün: [{urun['urun_kodu']}] {urun['urun_adi']}")
        tahmin = urun['tahmin_verisi']
        if "error" in tahmin:
            print(f"Uyarı: {tahmin['error']}\n")
        else:
            print(f"Trend: {tahmin.get('trend')}")
            print(f"Değişim: %{tahmin.get('degisim_orani')}")
            print(f"Başlangıç: {tahmin.get('baslangic_tahmini')} adet/gün -> Bitiş: {tahmin.get('bitis_tahmini')} adet/gün\n")