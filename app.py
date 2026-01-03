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

# --- KARARLI SİYAH GRİD TASARIM (CSS) ---
st.markdown("""
<style>
/* 1. ARKA PLAN: Saf Siyah ve Matematiksel Grid (Resim dosyası gerektirmez) */
.stApp {
    background-color: #000000;
    background-image: 
        linear-gradient(rgba(50, 50, 50, 0.5) 1px, transparent 1px),
        linear-gradient(90deg, rgba(50, 50, 50, 0.5) 1px, transparent 1px);
    background-size: 40px 40px; /* Karelerin boyutu */
}

/* 2. TÜM YAZILAR: Net Beyaz */
h1, h2, h3, h4, h5, h6, p, li, label, .stMarkdown, .caption {
    color: #FFFFFF !important;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
.caption {
    color: #BBBBBB !important; /* Alt başlık hafif gri */
}

/* 3. KUTULAR VE FORMLAR: Koyu Gri Zemin (Okunabilirlik için) */
[data-testid="stExpander"], [data-testid="stForm"], .stAlert {
    background-color: #111111 !important; /* Form zemini koyu gri */
    border: 1px solid #444444 !important; /* Kenarlıklar gri */
    border-radius: 8px !important;
}

/* 4. GİRİŞ KUTULARI (Inputlar) */
.stTextInput>div>div>input, .stSelectbox>div>div>div {
    background-color: #222222 !important;
    color: white !important;
    border: 1px solid #555 !important;
}

/* 5. MENÜ (Sidebar): Ana ekrandan ayrılması için koyu gri */
[data-testid="stSidebar"] {
    background-color: #0a0a0a !important;
    border-right: 1px solid #333;
}

/* 6. BUTONLAR: Sade ve Şık */
.stButton>button {
    background-color: #ffffff !important;
    color: #000000 !important;
    border: none !important;
    font-weight: bold !important;
    border-radius: 5px !important;
    transition: all 0.2s;
}
.stButton>button:hover {
    background-color: #cccccc !important; /* Üzerine gelince grileşir */
}

/* Footer */
.footer {
    position: fixed; left: 0; bottom: 0; width: 100%;
    background-color: #0a0a0a;
    color: #888;
    text-align: center; padding: 10px;
    border-top: 1px solid #333; z-index: 100;
}
</style>
""", unsafe_allow_html=True)

# --- GİZLİ API KEY KONTROLÜ ---
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
    try: st.image("logo.png", width=110)
    except: st.markdown("### 📚")
with col_title:
    st.title("QuizApp")
    st.caption("GeoFurkan Eğitim Platformu | v3.1 Stable")

st.divider()

# --- MENÜ ---
st.sidebar.markdown("### 🧭 NAVİGASYON")
secim = st.sidebar.radio("Mod Seçiniz:", ["PDF Soru Üretici", "Soru Kütüphanesi"])

# --- MOD 1: PDF ---
if secim == "PDF Soru Üretici":
    st.subheader("📄 PDF Analiz ve Test")
    
    uploaded_file = st.file_uploader("Ders notunu yükle (PDF)", type="pdf")
    
    if 'pdf_sorular' not in st.session_state: st.session_state['pdf_sorular'] = None

    if uploaded_file and st.button("Analiz Et ve Başla", type="primary"):
        if not api_key:
             st.error("Sistem Hatası: API Anahtarı bulunamadı (Secrets).")
        else:
            with st.spinner("Sistem çalışıyor..."):
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
            
            if st.form_submit_button("Testi Bitir"):
                dogru = 0
                st.write("### 📊 Analiz Sonucu")
                for i, q in enumerate(st.session_state['pdf_sorular']):
                    if cevaplar.get(i) == q['dogru_cevap']:
                        dogru += 1
                        st.success(f"**{i+1}.** Doğru ✅")
                    else:
                        st.error(f"**{i+1}.** Yanlış ❌ (Doğru: {q['dogru_cevap']})")
                st.metric("Puan", int(dogru/len(st.session_state['pdf_sorular'])*100))

# --- MOD 2: Kütüphane ---
elif secim == "Soru Kütüphanesi":
    st.subheader("📚 Hazır Testler")
    try:
        dersler = list(soru_bankasi.kutuphane.keys())
        secilen_ders = st.selectbox("Ders", dersler)
        konular = list(soru_bankasi.kutuphane[secilen_ders].keys())
        secilen_konu = st.selectbox("Konu", konular)
        sorular = soru_bankasi.kutuphane[secilen_ders][secilen_konu]
        
        st.info(f"Test Yüklendi: **{secilen_konu}** ({len(sorular)} Soru)")
        
        with st.form("lib_test"):
            lib_cevaplar = {}
            for i, q in enumerate(sorular):
                st.markdown(f"**{i+1}. {q['soru']}**")
                lib_cevaplar[i] = st.radio("Seçiminiz:", q['secenekler'], key=f"l_{i}", label_visibility="collapsed")
                st.write("")
            
            if st.form_submit_button("Testi Bitir"):
                dogru = 0
                st.write("### 📊 Analiz Sonucu")
                for i, q in enumerate(sorular):
                    if lib_cevaplar.get(i) == q['dogru_cevap']:
                        dogru += 1
                        st.success(f"**{i+1}.** Doğru ✅")
                    else:
                        st.error(f"**{i+1}.** Yanlış ❌ (Doğru: {q['dogru_cevap']})")
                
                skor = int(dogru/len(sorular)*100)
                st.metric("Puan", skor)
                if skor >= 70: st.balloons()
                
    except Exception as e:
        st.warning("Veritabanı bağlantısı kurulamadı.")

# Footer
st.markdown('<div class="footer">GeoFurkan © 2026</div>', unsafe_allow_html=True)

