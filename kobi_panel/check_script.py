import sqlite3, requests, json, os
BASE='http://127.0.0.1:8000'
DB='Hackathon_project/DB/SME_DB.db'
conn=sqlite3.connect(DB)
conn.row_factory=sqlite3.Row
print('Last 5 siparis_onay:')
for r in conn.execute('SELECT id,musteri_telefon,urunler_ozet,urunler_json,durum FROM siparis_onay ORDER BY id DESC LIMIT 5').fetchall():
    print(dict(r))

print('\nLast 10 stok_hareketleri:')
for r in conn.execute('SELECT id,urun_id,tur,miktar,onceki_stok,sonraki_stok,tarih FROM stok_hareketleri ORDER BY id DESC LIMIT 10').fetchall():
    print(dict(r))

pending = conn.execute("SELECT id FROM siparis_onay WHERE durum='bekliyor' ORDER BY id DESC LIMIT 1").fetchone()
if pending:
    sid = pending['id']
    print(f'\nApproving pending {sid}')
    try:
        resp = requests.post(f'{BASE}/api/siparis-onay/{sid}/onayla', timeout=10)
        print('approve status', resp.status_code, resp.text)
    except Exception as e:
        print(f"Request failed: {e}")
else:
    print('\nNo pending orders to approve')
conn.close()
