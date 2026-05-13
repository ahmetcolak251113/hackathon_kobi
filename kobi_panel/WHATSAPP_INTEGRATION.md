WhatsApp Bot -> KOBİ Panel Integration

1) Example structured POST payload (preferred):

POST /api/siparis-onay/talep
Content-Type: application/json

{
  "musteri_telefon": "+905551112233",
  "musteri_ad": "Ahmet Yılmaz",
  "urunler": [
    {"urun_id": 1, "adet": 2},
    {"custom_name": "El Yapımı Sabun", "adet": 1}
  ],
  "toplam_tutar": 250.0,
  "notlar": "Hızlı teslimat istiyor"
}

2) Fallback simple payload (only text summary):

{
  "musteri_telefon": "+905551112233",
  "musteri_ad": "Ahmet Yılmaz",
  "urunler_ozet": "2 x Kavanoz, 1 x Sabun",
  "toplam_tutar": 250.0
}

Notes:
- Prefer `urunler` structured list so KOBİ panel can decrement stock and create detailed cargo items.
- KOBİ panel will call the Mock Cargo API at `MOCK_CARGO_URL` (default http://127.0.0.1:3000) to create a shipment and will send the returned `tracking_code` to the customer via WhatsApp.
- If stock is insufficient for any structured `urun_id`, the API returns HTTP 400 and the panel will not approve the order.
