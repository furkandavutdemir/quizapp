import streamlit as st
import PyPDF2
import requests
import json
import soru_bankasi

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="QuizApp by GeoFurkan",
    page_icon="logo.png",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- TASARIM KODLARI (CSS) ---
st.markdown("""
<style>
/* 1. ARKA PLAN: Senin seçtiğin harita resmi */
.stApp {
    background-image: url("background.jpg"); 
    background-size: cover; /* Resmi ekrana yay */
    background-position: center;
    background-attachment: fixed;
}

/* 2. YAZI RENKLERİ: Harita açık renk olduğu için yazılar KOYU olmalı */
h1, h2, h3, h4, h5, h6, .stMarkdown, p, li, label, .caption {
    color: #222222 !important; /* Koyu antrasit gri */
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}
h1 {
    font-weight: 800; /* Başlıklar daha kalın */
    letter-spacing: -1px;
}

/* 3. KUTULAR: Okunabilirlik için hafif beyazımsı cam efekti */
[data-testid="stExpander"], [data-testid="stForm"], .stAlert {
    background-color: rgba(255, 255, 255, 0.85) !important; /* Yarı saydam beyaz */
    border: 1px solid #ccc !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1); /* Hafif gölge */
}

/* 4. MENÜ (SIDEBAR): Emojisiz, sade ve modern */
[data-testid="stSidebar"] {
    background-color: #f8f9fa !important; /* Çok açık gri, temiz görünüm */
    border-right: 1px solid #ddd;
}
/* Menüdeki radyo butonlarını özelleştirme */
.stRadio > div {
    background-color: transparent;
}
.stRadio label {
    font-size: 16px !important;
    font-weight: 600 !important;
    padding: 10px;
    border-radius: 8px;
    transition: background-color 0.3s;
}
.stRadio label:hover {
    background-color: #e9ecef; /* Üzerine gelince hafif gri */
}

/* 5. BUTONLAR: GeoFurkan Siyah/Beyaz tarzı veya koyu mavi */
.stButton>button {
    background-color: #222222 !important; /* Siyah buton */
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 12px 24px !important;
    font-weight: bold !important;
    transition: all 0.3s ease;
}
.stButton>button:hover {
    background-color: #444444 !important; /* Üzerine gelince koyu gri */
    transform: translateY(-2px);
}

/* 6. GİRİŞ KUTULARI */
.stTextInput>div>div>input, .stSelectbox>div>div>div {
    background-color: #ffffff !important;
    color: #333 !important;
    border: 1px solid #bbb !important;
}

/* Footer */
.footer {
    position: fixed; left: 0; bottom: 0; width: 100%;
    background-color: rgba(255, 255, 255, 0.9);
    color: #555;
    text-align: center; padding: 10px;
    border-top: 1px solid #ccc; z-index: 100; font-size: 12px;
}
</style>
""", unsafe_allow_html=True)

# --- GİZLİ API KEY ---
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = None 

# --- FONKSİYONLAR ---
def pdf_oku(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages: text += page.extract_text()
    return text

def temizle_json(metin):
    return metin.replace("```json", "").replace("```", "").strip()

def sorulari_uret_otomatik(text, api_key):
    if not api_key: return []
    url_model = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        r = requests.get(url_model, timeout=10)
        if r.status_code == 200:
            uygunlar = [m['name'] for m in r.json().get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
            if not uygunlar: return []
            model = next((m for m in uygunlar if 'flash' in m), uygunlar[0]).replace("models/", "")
        else: return []
    except: return []

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    prompt = f"""Sen uzman bir sınav hazırlayıcısın. Metni analiz et, 5 adet çoktan seçmeli soru hazırla.
    Cevap formatı SADECE JSON olsun: [{{ "soru": "...", "secenekler": ["A)..."], "dogru_cevap": "A)..." }}]
    Metin: {text[:6000]}"""
    
    try:
        resp = requests.post(url, headers={'Content-Type': 'application/json'}, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=45)
        if resp.status_code == 200:
            return json.loads(temizle_json(resp.json()['candidates'][0]['content']['parts'][0]['text']))
    except: pass
    return []

# --- ARAYÜZ ---

# Header
col_logo, col_title = st.columns([1, 4])
with col_logo:
    try: st.image("logo.png", width=120)
    except: st.markdown("### 🏔️")
with col_title:
    st.title("QuizApp")
    st.caption("GeoFurkan Eğitim Platformu")

st.divider()

# --- MENÜ (Sadeleştirildi) ---
st.sidebar.title("NAVİGASYON")
# Emojiler kaldırıldı, sade metin kullanıldı
secim = st.sidebar.radio("Bölüm Seçiniz:", ["PDF Soru Modülü", "Soru Kütüphanesi"])

# --- MOD 1: PDF ---
if secim == "PDF Soru Modülü":
    st.subheader("PDF Soru Üretici")
    
    # Kutu tasarımını CSS ile güzelleştirdik
    uploaded_file = st.file_uploader("Ders notunu yükle (PDF)", type="pdf")
    
    if 'pdf_sorular' not in st.session_state: st.session_state['pdf_sorular'] = None

    if uploaded_file and st.button("Analiz Et ve Soru Üret", type="primary"):
        if not api_key:
             st.error("Sistem Hatası: API Anahtarı bulunamadı.")
        else:
            with st.spinner("Harita taranıyor, sorular çıkarılıyor..."):
                text = pdf_oku(uploaded_file)
                st.session_state['pdf_sorular'] = sorulari_uret_otomatik(text, api_key)
                st.rerun()

    if st.session_state['pdf_sorular']:
        with st.form("pdf_test"):
            cevaplar = {}
            for i, q in enumerate(st.session_state['pdf_sorular']):
                st.markdown(f"**{i+1}. {q['soru']}**")
                cevaplar[i] = st.radio("Seçiminiz:", q['secenekler'], key=f"p_{i}", label_visibility="collapsed")
                st.write("---")
            
            if st.form_submit_button("Testi Tamamla"):
                dogru = 0
                st.write("### Sonuç Analizi")
                for i, q in enumerate(st.session_state['pdf_sorular']):
                    if cevaplar.get(i) == q['dogru_cevap']:
                        dogru += 1
                        st.success(f"**{i+1}.** Doğru ✅")
                    else:
                        st.error(f"**{i+1}.** Yanlış ❌ (Doğru: {q['dogru_cevap']})")
                st.metric("Başarı Puanı", int(dogru/len(st.session_state['pdf_sorular'])*100))

# --- MOD 2: Kütüphane ---
elif secim == "Soru Kütüphanesi":
    st.subheader("Hazır Testler")
    try:
        dersler = list(soru_bankasi.kutuphane.keys())
        secilen_ders = st.selectbox("Ders", dersler)
        konular = list(soru_bankasi.kutuphane[secilen_ders].keys())
        secilen_konu = st.selectbox("Konu", konular)
        sorular = soru_bankasi.kutuphane[secilen_ders][secilen_konu]
        
        st.info(f"📍 **{secilen_konu}** testi seçildi. Toplam {len(sorular)} soru.")
        
        with st.form("lib_test"):
            lib_cevaplar = {}
            for i, q in enumerate(sorular):
                st.markdown(f"**{i+1}. {q['soru']}**")
                lib_cevaplar[i] = st.radio("Seçiminiz:", q['secenekler'], key=f"l_{i}", label_visibility="collapsed")
                st.write("")
            
            if st.form_submit_button("Testi Tamamla"):
                dogru = 0
                st.write("### Sonuç Analizi")
                for i, q in enumerate(sorular):
                    if lib_cevaplar.get(i) == q['dogru_cevap']:
                        dogru += 1
                        st.success(f"**{i+1}.** Doğru ✅")
                    else:
                        st.error(f"**{i+1}.** Yanlış ❌ (Doğru: {q['dogru_cevap']})")
                
                skor = int(dogru/len(sorular)*100)
                st.metric("Başarı Puanı", skor)
                if skor >= 70: st.balloons()
                
    except Exception as e:
        st.warning("Kütüphane verisi yüklenemedi.")

# Footer
st.markdown('<div class="footer">GeoFurkan © 2024 | QuizApp v3.0</div>', unsafe_allow_html=True)
