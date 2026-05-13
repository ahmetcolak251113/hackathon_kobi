// ── CONFIG ──────────────────────────────────────────────
const API_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:8000/api"
    : window.location.origin + "/api";

// ── STATE ───────────────────────────────────────────────
let currentEndpoint = "";
let currentEditId   = null;
let currentGrafikMod = "karsilastir";  // "tek" | "karsilastir"
let currentDilim     = "aylik";

let barChartInst        = null;
let pieChartInst        = null;
let karsilastirChartInst = null;
let karsilastirPieInst  = null;

const PALETTE = [
    "rgba(49,130,206,0.8)","rgba(56,161,105,0.8)","rgba(214,158,46,0.8)",
    "rgba(229,62,62,0.8)","rgba(128,90,213,0.8)","rgba(49,196,141,0.8)",
    "rgba(237,137,54,0.8)","rgba(0,188,212,0.8)"
];
const PALETTE_SOLID = [
    "#3182ce","#38a169","#d69e2e","#e53e3e","#805ad5","#31c48d","#ed8936","#00bcd4"
];

// ── SCHEMAS ─────────────────────────────────────────────
const schemas = {
    tedarikciler:    ["ad","yetkili","telefon","email","adres","vergi_no"],
    depo_malzemeleri:["tedarikci_id","malzeme_kodu","ad","birim","stok_miktari","kritik_stok_esigi","birim_fiyati"],
    urunler:         ["urun_kodu","ad","kategori","birim","stok_miktari","kritik_stok_esigi","alis_fiyati","satis_fiyati","birim_agirlik","aciklama"],
    musteriler:      ["ad_soyad","telefon","email","teslimat_adresi","notlar"],
    kargo_takip:     ["musteri_id","kargo_no","durum","beklenen_teslimat"]
};

// ── HELPERS ─────────────────────────────────────────────
function hideAllViews() {
    ["dashboard-view","table-view","tahminler-view","ai-rapor-view","grafikler-view","siparis-onay-view"]
        .forEach(id => { const el = document.getElementById(id); if (el) el.style.display = "none"; });
}

function setActiveMenu(el) {
    document.querySelectorAll(".sidebar a").forEach(a => a.classList.remove("active"));
    if (el) el.classList.add("active");
}

function destroyChart(inst) { try { if (inst) inst.destroy(); } catch(e) {} return null; }

// ── DASHBOARD ────────────────────────────────────────────
async function loadDashboard(el) {
    setActiveMenu(el);
    hideAllViews();
    document.getElementById("dashboard-view").style.display = "block";
    try {
        const d = await fetch(`${API_URL}/ozet`).then(r => r.json());
        document.getElementById("ozet-cards").innerHTML = `
            <div class="col-6 col-md-3"><div class="stat-card blue">
                <div class="stat-value text-primary">${d.toplam_urun}</div>
                <div class="stat-label">Toplam Ürün</div>
            </div></div>
            <div class="col-6 col-md-3"><div class="stat-card red">
                <div class="stat-value text-danger">${d.kritik_stok}</div>
                <div class="stat-label">Kritik Stok (Ürün)</div>
            </div></div>
            <div class="col-6 col-md-3"><div class="stat-card yellow">
                <div class="stat-value text-warning">${d.kritik_depo}</div>
                <div class="stat-label">Kritik Depo</div>
            </div></div>
            <div class="col-6 col-md-3"><div class="stat-card green">
                <div class="stat-value text-success">${d.toplam_musteri}</div>
                <div class="stat-label">Müşteriler</div>
            </div></div>`;
    } catch(e) { console.error("Özet alınamadı", e); }
    loadKritikAksiyonlar();
    checkWeather();
}

async function checkWeather() {
    try {
        const d = await fetch(`${API_URL}/hava-durumu-uyarisi`).then(r => r.json());
        if (d.uyari) {
            document.getElementById("weather-alert-text").innerText = d.uyari;
            document.getElementById("weather-alert").classList.remove("d-none");
        }
    } catch(e) {}
}

async function loadKritikAksiyonlar() {
    const container = document.getElementById("kritik-aksiyonlar-listesi");
    try {
        const data = await fetch(`${API_URL}/analiz/kritik-aksiyonlar`).then(r => r.json());
        if (!data.length) {
            container.innerHTML = '<div class="aksiyon-row text-success">Aksiyon gerektiren durum yok.</div>';
            return;
        }
        container.innerHTML = data.map(a => {
            const itemId = a.urun_id || a.kargo_id || 0;
            return `<div class="aksiyon-row">
                <span class="text-${a.tip === "danger" ? "danger" : "warning"}">${a.mesaj}</span>
                <button class="btn btn-sm btn-outline-secondary" onclick="runAksiyon('${a.kategori}',${itemId})">
                    ${a.aksiyon}
                </button>
            </div>`;
        }).join("");
    } catch(e) {
        container.innerHTML = '<div class="aksiyon-row text-danger">Veriler yüklenemedi.</div>';
    }
}

async function runAksiyon(kategori, id) {
    const textarea = document.getElementById("aksiyon-sonuc-text");
    textarea.value = "Yapay zeka analiz ediyor, lütfen bekleyiniz...";
    new bootstrap.Modal(document.getElementById("aksiyonModal")).show();
    const ep = kategori === "urun"  ? `/aksiyon/tedarik-taslak/${id}`
             : kategori === "depo"  ? `/aksiyon/depo-tedarik-taslak/${id}`
             :                        `/aksiyon/kargo-ozur/${id}`;
    try {
        const d = await fetch(API_URL + ep).then(r => r.json());
        textarea.value = d.taslak || JSON.stringify(d);
    } catch(e) { textarea.value = "Hata oluştu: " + e.message; }
}

// ── TAHMİNLER ────────────────────────────────────────────
async function loadTahminler(el) {
    setActiveMenu(el);
    hideAllViews();
    document.getElementById("tahminler-view").style.display = "block";
    try {
        const data = await fetch(`${API_URL}/tahmin/genel`).then(r => r.json());
        document.getElementById("genel-tahmin-container").innerHTML =
            `<div class="alert alert-${data.trend === "Pozitif" ? "success" : "danger"}">
                Trend: <strong>${data.trend}</strong> &nbsp;|&nbsp; Değişim: <strong>%${data.degisim_orani}</strong>
            </div>`;
    } catch(e) {}
    try {
        const urunler = await fetch(`${API_URL}/tahmin/urunler`).then(r => r.json());
        document.getElementById("urun-tahmin-container").innerHTML = urunler.map(u =>
            `<div class="col-md-4 mb-3"><div class="chart-card">
                <div class="fw-bold">${u.urun_adi}</div>
                <div class="${u.tahmin_verisi?.trend === "Pozitif" ? "text-success" : "text-danger"}">
                    ${u.tahmin_verisi?.trend || "Veri Yok"}
                </div>
            </div></div>`).join("");
    } catch(e) {}
}

// ── AI RAPOR ─────────────────────────────────────────────
async function loadAIRapor(el) {
    setActiveMenu(el);
    hideAllViews();
    document.getElementById("ai-rapor-view").style.display = "block";
    fetchAIRapor();
}

async function fetchAIRapor() {
    document.getElementById("ai-rapor-content").innerHTML = "Rapor hazırlanıyor...";
    try {
        const d = await fetch(`${API_URL}/ai-rapor`).then(r => r.json());
        document.getElementById("ai-rapor-content").innerHTML = marked.parse(d.rapor);
    } catch(e) {
        document.getElementById("ai-rapor-content").innerHTML = "Rapor oluşturulamadı.";
    }
}

// ── GRAFİKLER ────────────────────────────────────────────
async function loadGrafikler(el) {
    setActiveMenu(el);
    hideAllViews();
    document.getElementById("grafikler-view").style.display = "block";
    // Önce ürünleri yükle, sonra UI'ı senkronize et, sonra grafikleri çiz
    await populateUrunSelect();
    applyGrafikModUI(currentGrafikMod);
    applyDilimUI(currentDilim);
    refreshGrafikler();
}

async function populateUrunSelect() {
    const sel = document.getElementById("grafik-urun");
    try {
        const urunler = await fetch(`${API_URL}/urunler`).then(r => r.json());
        if (urunler && urunler.length) {
            sel.innerHTML = urunler.map(u => `<option value="${u.id}">${u.ad}</option>`).join("");
        } else {
            sel.innerHTML = '<option value="">Ürün bulunamadı</option>';
        }
    } catch(e) {
        sel.innerHTML = '<option value="">Yüklenemedi</option>';
    }
}

// Sadece UI durumunu günceller, grafikleri yeniden çizmez
function applyGrafikModUI(mod) {
    const btnTek  = document.getElementById("btn-tek");
    const btnKar  = document.getElementById("btn-karsilastir");
    const tekDiv  = document.getElementById("grafik-tek-mod");
    const karDiv  = document.getElementById("grafik-karsilastir-mod");
    const urunWrap = document.getElementById("urun-secici-wrap");
    const urunSel  = document.getElementById("grafik-urun");
    if (!btnTek || !btnKar) return;
    btnTek.classList.toggle("active", mod === "tek");
    btnKar.classList.toggle("active", mod === "karsilastir");
    if (tekDiv) tekDiv.style.display  = mod === "tek"         ? "block" : "none";
    if (karDiv) karDiv.style.display  = mod === "karsilastir" ? "block" : "none";
    if (urunWrap) urunWrap.style.opacity = mod === "karsilastir" ? "0.4" : "1";
    if (urunSel)  urunSel.disabled       = mod === "karsilastir";
}

// Sadece pill UI'ını günceller
function applyDilimUI(dilim) {
    document.querySelectorAll(".time-pill").forEach(p => {
        p.classList.toggle("active", p.dataset.dilim === dilim);
    });
}

// Zaman pill seçimi — inline onclick handler'dan çağrılır
function setZamanDilimi(btn, dilim) {
    currentDilim = dilim;
    applyDilimUI(dilim);
    refreshGrafikler();
}

// Mod değiştir
function setGrafikMod(mod) {
    currentGrafikMod = mod;
    applyGrafikModUI(mod);
    refreshGrafikler();
}

function onUrunSecildi() {
    if (currentGrafikMod === "tek") { updateBarGrafik(); }
}

function refreshGrafikler() {
    if (currentGrafikMod === "tek") {
        updateBarGrafik();
        updatePastaGrafik("pieChart");
    } else {
        updateKarsilastirmaGrafik();
        updatePastaGrafik("karsilastirPieChart");
    }
}

// ── BAR GRAFİK (tek ürün) ────────────────────────────────
async function updateBarGrafik() {
    const dilim  = currentDilim;
    const urunEl = document.getElementById("grafik-urun");
    const urun_id = urunEl.value;
    if (!urun_id) return;
    const urunAdi  = urunEl.options[urunEl.selectedIndex]?.text || "";
    const dilimMap = { gunluk:"Günlük", haftalik:"Haftalık", aylik:"Aylık", yillik:"Yıllık", tumzamanlar:"Tüm Zamanlar" };

    try {
        const data = await fetch(`${API_URL}/grafik/zaman-serisi?dilim=${dilim}&urun_id=${urun_id}`).then(r => r.json());
        const b = document.getElementById("trend-baslik");
        const s = document.getElementById("trend-alt");
        if (b) b.textContent = `${urunAdi} — Satış Trendi`;
        if (s) s.textContent = `${dilimMap[dilim] || dilim} periyoduna göre satış miktarı (Bar Grafik)`;

        barChartInst = destroyChart(barChartInst);
        const ctx = document.getElementById("barChart").getContext("2d");
        barChartInst = new Chart(ctx, {
            type: "bar",
            data: {
                labels: data.etiketler,
                datasets: [{
                    label: `${urunAdi} Satış`,
                    data: data.veriler,
                    backgroundColor: data.etiketler.map((_, i) => PALETTE[i % PALETTE.length]),
                    borderColor:     data.etiketler.map((_, i) => PALETTE_SOLID[i % PALETTE_SOLID.length]),
                    borderWidth: 2,
                    borderRadius: 6,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true },
                    tooltip: { mode: "index", intersect: false }
                },
                scales: {
                    y: { beginAtZero: true, grid: { color: "rgba(0,0,0,0.05)" } },
                    x: { grid: { display: false } }
                }
            }
        });
    } catch(e) { console.error("Bar grafik hatası", e); }
}

// ── KARŞILAŞTIRMALI BAR ───────────────────────────────────
async function updateKarsilastirmaGrafik() {
    const dilim = currentDilim;
    try {
        const data = await fetch(`${API_URL}/grafik/karsilastirma?dilim=${dilim}`).then(r => r.json());
        karsilastirChartInst = destroyChart(karsilastirChartInst);
        const ctx = document.getElementById("karsilastirChart").getContext("2d");
        karsilastirChartInst = new Chart(ctx, {
            type: "bar",
            data: {
                labels: data.etiketler,
                datasets: data.urunler.map((u, i) => ({
                    label: u.ad,
                    data: u.veriler,
                    backgroundColor: PALETTE[i % PALETTE.length],
                    borderColor:     PALETTE_SOLID[i % PALETTE_SOLID.length],
                    borderWidth: 2,
                    borderRadius: 4,
                    borderSkipped: false
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: {
                    legend: { display: true, position: "top" },
                    tooltip: { mode: "index" }
                },
                scales: {
                    y: { beginAtZero: true, grid: { color: "rgba(0,0,0,0.05)" } },
                    x: { grid: { display: false } }
                }
            }
        });
    } catch(e) { console.error("Karşılaştırma grafik hatası", e); }
}

// ── PASTA / DAİRE GRAFİK ─────────────────────────────────
// canvasId: hangi canvas'a çizileceği (görünür olan)
async function updatePastaGrafik(canvasId) {
    const dilim = currentDilim;
    try {
        const data = await fetch(`${API_URL}/grafik/pasta?dilim=${dilim}`).then(r => r.json());

        // Veri yoksa çizme
        if (!data.etiketler || data.etiketler.length === 0) return;

        // Callback fonksiyonu ayrı tutulur — JSON'a serialize EDİLMEZ
        const tooltipCallback = ctx => {
            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
            const pct   = total ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
            return ` ${ctx.label}: ${ctx.parsed} adet (%${pct})`;
        };

        const makePieConfig = () => ({
            type: "doughnut",
            data: {
                labels: [...data.etiketler],
                datasets: [{
                    data: [...data.veriler],
                    backgroundColor: PALETTE_SOLID,
                    borderWidth: 2,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 400 },
                plugins: {
                    legend: { position: "bottom", labels: { font: { size: 11 }, padding: 14 } },
                    tooltip: { callbacks: { label: tooltipCallback } }
                },
                cutout: "52%"
            }
        });

        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        // Sadece istenen canvas'a çiz; her seferinde temizle
        if (canvasId === "pieChart") {
            pieChartInst = destroyChart(pieChartInst);
            pieChartInst = new Chart(canvas.getContext("2d"), makePieConfig());
        } else {
            karsilastirPieInst = destroyChart(karsilastirPieInst);
            karsilastirPieInst = new Chart(canvas.getContext("2d"), makePieConfig());
        }
    } catch(e) { console.error("Pasta grafik hatası:", e); }
}

// ── TABLO ────────────────────────────────────────────────
async function loadTable(endpoint, title, el) {
    setActiveMenu(el);
    hideAllViews();
    document.getElementById("table-view").style.display = "block";
    document.getElementById("table-title").innerText = title;
    currentEndpoint = endpoint;
    try {
        const data = await fetch(`${API_URL}/${endpoint}`).then(r => r.json());
        const thead = document.getElementById("data-thead");
        const tbody = document.getElementById("data-tbody");
        if (!data.length) {
            thead.innerHTML = "";
            tbody.innerHTML = '<tr><td class="p-4 text-muted">Kayıt yok.</td></tr>';
            return;
        }
        thead.innerHTML = "<tr>" + Object.keys(data[0]).map(k => `<th>${k}</th>`).join("") + "<th>İşlemler</th></tr>";
        tbody.innerHTML = data.map(row => {
            let html = "<tr>" + Object.keys(row).map(k => `<td>${row[k] !== null ? row[k] : "-"}</td>`).join("");
            html += `<td>
                <button class="btn btn-sm btn-primary me-1" onclick='openCrudModal(${row.id}, ${JSON.stringify(row)})'>Düzenle</button>
                <button class="btn btn-sm btn-danger me-1" onclick="deleteData(${row.id})">Sil</button>`;
            if (endpoint === "urunler") {
                html += `<button class="btn btn-sm btn-warning me-1" onclick="openStokModal(${row.id},'dus')">- Stok</button>
                         <button class="btn btn-sm btn-success"       onclick="openStokModal(${row.id},'artir')">+ Stok</button>`;
            }
            return html + "</td></tr>";
        }).join("");
    } catch(e) { console.error("Tablo verisi alınamadı", e); }
}

function openCrudModal(id = null, row = null) {
    currentEditId = id;
    document.getElementById("crudModalTitle").innerText = id ? "Düzenle" : "Ekle";
    document.getElementById("crud-form").innerHTML = "<div class='row'>" +
        schemas[currentEndpoint].map(f => {
            const type = ["id","miktar","fiyat","esigi","stok","agirlik"].some(x => f.includes(x)) ? "number" : "text";
            return `<div class="col-md-6 mb-3">
                <label class="form-label fw-semibold small">${f}</label>
                <input type="${type}" class="form-control" id="inp-${f}" value="${row ? (row[f] ?? "") : ""}">
            </div>`;
        }).join("") + "</div>";
    new bootstrap.Modal(document.getElementById("crudModal")).show();
}

async function saveData() {
    let payload = {};
    schemas[currentEndpoint].forEach(f => {
        const el = document.getElementById(`inp-${f}`);
        payload[f] = el.value !== "" ? (el.type === "number" ? parseFloat(el.value) : el.value) : null;
    });
    try {
        const url  = `${API_URL}/${currentEndpoint}${currentEditId ? "/" + currentEditId : ""}`;
        const res  = await fetch(url, {
            method: currentEditId ? "PUT" : "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            bootstrap.Modal.getInstance(document.getElementById("crudModal")).hide();
            loadTable(currentEndpoint, document.getElementById("table-title").innerText);
        } else {
            alert("Hata: Veri formatını kontrol edin.");
        }
    } catch(e) { console.error("Kaydetme başarısız", e); }
}

async function deleteData(id) {
    if (!confirm("Bu kayıt silinsin mi?")) return;
    try {
        await fetch(`${API_URL}/${currentEndpoint}/${id}`, { method: "DELETE" });
        loadTable(currentEndpoint, document.getElementById("table-title").innerText);
    } catch(e) { console.error("Silme başarısız", e); }
}

function openStokModal(id, tip) {
    document.getElementById("stok-urun-id").value   = id;
    document.getElementById("stok-islem-tipi").value = tip;
    document.getElementById("stokModalTitle").innerText = tip === "dus" ? "Elden Satış (Stok Düş)" : "Alım (Stok Artır)";
    document.getElementById("stok-adet").value = 1;
    new bootstrap.Modal(document.getElementById("stokModal")).show();
}

async function executeStok() {
    const id   = document.getElementById("stok-urun-id").value;
    const adet = document.getElementById("stok-adet").value;
    const tip  = document.getElementById("stok-islem-tipi").value;
    const url  = tip === "dus"
        ? `${API_URL}/hizli_satis`
        : `${API_URL}/stok_artir?urun_id=${id}&miktar=${adet}`;
    const opts = tip === "dus"
        ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ urun_id: parseInt(id), adet: parseFloat(adet) }) }
        : { method: "POST" };
    try {
        const res = await fetch(url, opts);
        if (res.ok) {
            bootstrap.Modal.getInstance(document.getElementById("stokModal")).hide();
            loadTable(currentEndpoint, document.getElementById("table-title").innerText);
        } else {
            const d = await res.json();
            alert("Hata: " + (d.detail || "Bilinmeyen hata"));
        }
    } catch(e) { console.error("Stok güncelleme başarısız", e); }
}

// ── SİPARİŞ ONAY ─────────────────────────────────────────
async function loadSiparisOnay(el) {
    if (el) setActiveMenu(el);
    hideAllViews();
    document.getElementById("siparis-onay-view").style.display = "block";
    await refreshSiparisOnaylar();
}

async function refreshSiparisOnaylar() {
    const container = document.getElementById("siparis-onay-listesi");
    container.innerHTML = '<div class="text-muted p-3">Yükleniyor...</div>';
    try {
        const data = await fetch(`${API_URL}/siparis-onay/bekleyenler`).then(r => r.json());
        const badge = document.getElementById("siparis-badge");
        if (data.length > 0) { badge.textContent = data.length; badge.classList.remove("d-none"); }
        else { badge.classList.add("d-none"); }

        if (!data.length) {
            container.innerHTML = '<div class="alert alert-success m-3">Onay bekleyen sipariş bulunmuyor.</div>';
            return;
        }
        container.innerHTML = data.map(s => `
            <div class="siparis-card" id="siparis-${s.id}">
                <div class="card-body p-4">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <h6 class="fw-bold mb-1">${s.musteri_telefon} &mdash; <span class="text-muted">${s.musteri_ad || ""}</span></h6>
                            <p class="mb-1 small"><strong>Sipariş:</strong> ${s.urunler_ozet || "—"}</p>
                            <p class="mb-1 small"><strong>Tutar:</strong> ${s.toplam_tutar ? s.toplam_tutar + " TL" : "—"}</p>
                            <p class="mb-0 small text-muted">${s.talep_tarihi || ""}</p>
                        </div>
                        <span class="badge bg-warning text-dark">Bekliyor</span>
                    </div>
                    <div class="mt-3 d-flex gap-2">
                        <button class="btn btn-success btn-sm" onclick="siparisKarar(${s.id},'onayla')">Onayla & Kargo Başlat</button>
                        <button class="btn btn-danger  btn-sm" onclick="siparisKarar(${s.id},'reddet')">Reddet & Müşteriyi Bildir</button>
                    </div>
                </div>
            </div>`).join("");
    } catch(e) {
        container.innerHTML = '<div class="alert alert-danger m-3">Siparişler yüklenemedi.</div>';
    }
}

async function siparisKarar(siparisId, karar) {
    const card = document.getElementById(`siparis-${siparisId}`);
    if (card) card.innerHTML = `<div class="card-body p-4 text-muted">İşleniyor...</div>`;
    try {
        const res  = await fetch(`${API_URL}/siparis-onay/${siparisId}/${karar}`, { method: "POST" });
        const data = await res.json();
        if (res.ok) {
            const msg = karar === "onayla"
                ? `Sipariş onaylandı! Kargo No: <strong>${data.kargo_no || ""}</strong> — Tahmini teslimat: ${data.beklenen_teslimat || ""}`
                : "Sipariş reddedildi, müşteri bilgilendirildi.";
            if (card) card.innerHTML = `<div class="card-body p-4"><div class="alert alert-${karar==="onayla"?"success":"warning"} mb-0">${msg}</div></div>`;
        } else {
            if (card) card.innerHTML = `<div class="card-body p-4"><div class="alert alert-danger mb-0">Hata: ${data.detail || "Bilinmeyen hata"}</div></div>`;
        }
    } catch(e) {
        if (card) card.innerHTML = `<div class="card-body p-4"><div class="alert alert-danger mb-0">Bağlantı hatası.</div></div>`;
    }
}

async function checkSiparisBadge() {
    try {
        const data  = await fetch(`${API_URL}/siparis-onay/bekleyenler`).then(r => r.json());
        const badge = document.getElementById("siparis-badge");
        if (data.length > 0) { badge.textContent = data.length; badge.classList.remove("d-none"); }
        else { badge.classList.add("d-none"); }
    } catch(e) {}
}

// ── INIT ─────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    loadDashboard(document.getElementById("menu-dashboard"));
    checkSiparisBadge();
    setInterval(checkSiparisBadge, 30000);
});