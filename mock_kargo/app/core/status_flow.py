from datetime import timedelta

STATUS_FLOW: list[tuple[str, str, str, timedelta]] = [
    ("created", "Kargo kaydı oluşturuldu.", "Ana Depo", timedelta(seconds=0)),
    ("preparing", "Ürünler kargoya hazırlanıyor.", "Ana Depo", timedelta(seconds=20)),
    (
        "shipped",
        "Kargo depodan çıkış yaptı.",
        "İstanbul Transfer Merkezi",
        timedelta(seconds=40),
    ),
    (
        "in_transit",
        "Kargo transfer sürecinde.",
        "Bölgesel Transfer Merkezi",
        timedelta(seconds=60),
    ),
    (
        "out_for_delivery",
        "Kargo dağıtıma çıktı.",
        "Yerel Dağıtım Şubesi",
        timedelta(seconds=100),
    ),
    (
        "delivered",
        "Kargo teslim edildi.",
        "Müşteri Adresi",
        timedelta(seconds=140),
    ),
]

DELAY_REASONS: list[str] = [
    "Yoğun yağmur nedeniyle teslimat gecikebilir.",
    "Kar yağışı nedeniyle teslimat süresi uzadı.",
    "Bölgedeki trafik yoğunluğu nedeniyle gecikme yaşanıyor.",
    "Transfer merkezindeki yoğunluk nedeniyle kargo gecikti.",
    "Adres bölgesindeki operasyonel yoğunluk nedeniyle teslimat ertelendi.",
]
