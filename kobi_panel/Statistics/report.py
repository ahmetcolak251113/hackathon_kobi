import os
import google.generativeai as genai
from dotenv import load_dotenv

# .env dosyasını doğru klasörden yükle (HACKHATON/Hackathon_project/.env)
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(env_path)

# Gemini API yapılandırması
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def get_gemini_response(prompt: str, fallback: str) -> str:
    """Gemini API'sine istek atar, hata olursa fallback döner."""
    if not api_key:
        return fallback + "\n\n(Not: GEMINI_API_KEY bulunamadığı için taslak metin kullanıldı.)"
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API Hatası: {e}")
        return fallback + "\n\n(Not: AI servisine ulaşılamadığı için taslak metin kullanıldı.)"

def generate_business_report(days):
    """Genel işletme analizi için LLM (Yapay Zeka) raporu."""
    prompt = (
        f"Sen bir işletme yönetim asistanısın. KOBİ sahibi için son {days} günün verilerini baz alan kısa, "
        "motive edici ve profesyonel bir durum özet raporu yazar mısın? Rapor Markdown formatında olsun, "
        "satış trendi, risk analizleri (stok vb.) ve kargo durumlarını içersin."
    )
    fallback = (
        f"### {days} Günlük Yapay Zeka İşletme Raporu\n\n"
        f"* **Satış Trendi:** Sistem verilerine göre genel satışlarınız olumlu yönde ilerliyor.\n"
        f"* **Risk Analizi:** Bazı ürünler kritik stok sınırında, tedarik sürecini başlatmanız tavsiye edilir.\n"
        f"* **Kargo Durumu:** Kargo ağında lokal gecikmeler yaşanıyor."
    )
    return get_gemini_response(prompt, fallback)

def generate_supplier_order_draft(tedarikci, urun, adet, tel):
    """Kritik ürünü tedarikçiden istemek için oluşturulan LLM WhatsApp taslağı."""
    prompt = (
        f"Ben bir KOBİ sahibiyim. Tedarikçim olan '{tedarikci}' firmasına WhatsApp üzerinden bir sipariş "
        f"mesajı atacagım. '{urun}' ürününden acil {adet} adet sipariş geçmek istiyorum ve teslimat takvimini "
        f"soracağım. İletişim numaram: {tel}. Lütfen profesyonel ve kısa bir WhatsApp mesajı taslağı yazar mısın?"
    )
    fallback = (
        f"Merhaba {tedarikci} yetkilisi,\n\n"
        f"Yapay zeka asistanımız '{urun}' ürünümüzün kritik stok seviyesine indiğini tespit etti. "
        f"İşleyişin aksamaması için acil olarak {adet} adet sipariş geçmek istiyoruz. "
        f"Teslimat takvimi hakkında dönüş yapabilir misiniz?\n\nİletişim: {tel}"
    )
    return get_gemini_response(prompt, fallback)

def generate_depot_order_draft(tedarikci, malzeme, adet, tel):
    """Kritik depo malzemesi için oluşturulan LLM tedarik taslağı."""
    prompt = (
        f"Ben bir depo yöneticisiyim. Tedarikçim '{tedarikci}' firmasına depomuzda tükenmek üzere olan "
        f"'{malzeme}' malzemesinden acil {adet} adet sipariş edeceğimi belirten bir WhatsApp mesajı hazırla. "
        f"Onay ve proforma fatura beklediğimi ekle. İletişim numaram: {tel}."
    )
    fallback = (
        f"Merhabalar {tedarikci},\n\n"
        f"Depomuzda '{malzeme}' malzemesi tükenmek üzere. Üretimin devamı için {adet} adet "
        f"hammadde talebimiz bulunmaktadır. Onay ve proforma fatura bekliyoruz.\n\nİletişim: {tel}"
    )
    return get_gemini_response(prompt, fallback)

def generate_shipping_apology(musteri, kargo_no, durum):
    """Kargosu geciken müşteriye AI asistanı tarafından hazırlanan özür taslağı."""
    prompt = (
        f"Ben bir işletme sahibiyim. Müşterimiz '{musteri}'ye ait '{kargo_no}' numaralı kargonun "
        f"'{durum}' sebebiyle geciktiğini belirten, nazik ve çözüm odaklı bir özür SMS/WhatsApp mesajı yazar mısın? "
        "Süreci anlık takip ettiğimizi de belirt."
    )
    fallback = (
        f"Sayın {musteri},\n\n"
        f"{kargo_no} numaralı siparişinizin teslimatında kargo firması kaynaklı '{durum}' "
        f"sebebiyle bir gecikme yaşandığını fark ettik. Yapay zeka asistanımız süreci anlık takip ediyor. "
        f"Yaşanan bu aksaklıktan dolayı özür diler, sürecin en kısa sürede çözüleceğini bildirmek isteriz."
    )
    return get_gemini_response(prompt, fallback)