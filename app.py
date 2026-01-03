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

# --- MODERN GEOFURKAN TEMASI (CSS) ---
# Bu kısım, istediğin siyah izohips arka planı ve modern arayüzü sağlayan sihirli koddur.
st.markdown("""
<style>
/* 1. ANA ARKA PLAN: Siyah zemin üzerine gri izohips deseni */
.stApp {
    background-color: #000000; /* Zifiri siyah zemin */
    /* Aşağıdaki uzun kod, izohips desenini oluşturan gömülü SVG resmidir */
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='600' height='600' viewBox='0 0 600 600'%3E%3Cg fill='none' stroke='%23333333' stroke-width='1.2'%3E%3Cpath d='M0 600V0h600v600H0z' stroke='none'/%3E%3Cpath d='M0 0h600v600H0z' opacity='.5'/%3E%3Cpath d='M0 200q50 50 100-50t100-50 100 50 100 50 100-50 100-50V0H0v200zm0 200q50 50 100-50t100-50 100 50 100 50 100-50 100-50V200H0v200zm0 200q50 50 100-50t100-50 100 50 100 50 100-50 100-50V400H0v200z'/%3E%3Cpath d='M300 0q50 50 100 0t100 0 100 0V0h-300zm0 200q50 50 100 0t100 0 100 0V0h-300zm0 200q50 50 100 0t100 0 100 0V200h-300zm0 200q50 50 100 0t100 0 100 0V400h-300z'/%3E%3Cpath d='M0 100q50-50 100 50t100 50 100-50 100-50 100 50 100 50V0H0v100zm0 200q50-50 100 50t100 50 100-50 100-50 100 50 100 50V200H0v200zm0 200q50-50 100 50t100 50 100-50 100-50 100 50 100 50V400H0v200z'/%3E%3Cpath d='M300 100q50-50 100 0t100 0 100 0V0h-300zm0 200q50-50 100 0t100 0 100 0V0h-300zm0 200q50-50 100 0t100 0 100 0V200h-300zm0 200q50-50 100 0t100 0 100 0V400h-300z'/%3E%3C/g%3E%3C/svg%3E");
    background-attachment: fixed;
    background-size: 600px; /* Desenin sıklığı */
}

/* 2. METİN RENKLERİ: Koyu zemin üzerinde okunması için açık renkler */
h1, h2, h3, h4, h5, h6, p, label, span, div, .stMarkdown, .caption {
    color: #E0E0E0 !important; /* Açık gri/beyaz yazı rengi */
}
h1 {
    text-shadow: 2px 2px 4px #000000; /* Başlıklara gölge efekti */
}

/* 3. KUTULAR VE FORMLAR: Yarı saydam, modern cam efekti */
[data-testid="stExpander"], [data-testid="stForm"], .stAlert {
    background-color: rgba(30, 30, 30, 0.85) !important; /* Yarı saydam koyu gri */
    border: 1px solid #444 !important;
    border-radius: 15px !important;
    box-shadow: 0 4px 15px rgba(0,0,0,0.5); /* Derinlik gölgesi */
}

/* 4. BUTONLAR: Modern, yuvarlak ve renkli */
.stButton>button {
    background: linear-gradient(45deg, #00ADB5, #008C9E) !important; /* Turkuaz degrade */
    color: white !important;
    border: none !important;
    border-radius: 25px !important; /* Daha yuvarlak köşeler */
    padding: 10px 24px !important;
    font-weight: bold !important;
    transition: all 0.3s ease;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.stButton>button:hover {
     transform: translateY(-2px); /* Üzerine gelince hafif yukarı kalkar */
     box-shadow: 0 6px 20px rgba(0, 173, 181, 0.6); /* Parlama efekti */
}

/* 5. KENAR ÇUBUĞU (SIDEBAR) */
[data-testid="stSidebar"] {
    background-color: rgba(20, 20, 20, 0.95) !important; /* Çok koyu gri */
    border-right: 1px solid #333;
}

/* 6. GİRİŞ KUTULARI VE SEÇİMLER */
.stTextInput>div>div>input, .stSelectbox>div>div>div {
    background-color: #2C2C2C !important;
    color: white !important;
    border-radius: 10px !important;
    border: 1px solid #555 !important;
}

/* 7. FOOTER */
.footer {
    position: fixed; left: 0; bottom: 0; width: 100%;
    background-color: rgba(20, 20, 20, 0.95);
    color: #888;
    text-align: center; padding: 10px;
    border-top: 1px solid #333; z-index: 100;
}
.block-container {padding-top: 2rem; padding-bottom: 5rem;}
</style>
""", unsafe_allow_html=True)

# --- GİZLİ API KEY KONTROLÜ ---
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    # Yerelde çalışırken hata vermemesi için geçici bir çözüm,
    # ama deploy ettiğinde secrets çalışacak.
    api_key = None 
    # st.error("API Key Secrets içinde bulunamadı.") # Görüntü kirliliği olmasın diye kapattım

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

# --- ARAYÜZ BAŞLIYOR ---

# Header
col_logo, col_title = st.columns([1, 4])
with col_logo:
    try: st.image("logo.png", width=110)
    except: st.markdown("# 📚")
with col_title:
    st.title("QuizApp")
    st.caption("GeoFurkan Eğitim Platformu")
st.divider()

# --- MENÜ ---
st.sidebar.title("📌 Menü")
secim = st.sidebar.radio("Seçim Yapınız:", ["📄 PDF ile Soru Üret", "📚 Hazır Soru Kütüphanesi"])

# --- MOD 1: PDF ---
if secim == "📄 PDF ile Soru Üret":
    st.subheader("Yapay Zeka Soru Üretici")
    st.info("Ders notunu (PDF) yükle, yapay zeka senin için test hazırlasın.")
    
    uploaded_file = st.file_uploader("Dosyayı buraya sürükle", type="pdf")
    
    if 'pdf_sorular' not in st.session_state: st.session_state['pdf_sorular'] = None

    if uploaded_file and st.button("Soruları Oluştur 🚀", type="primary"):
        if not api_key:
             st.error("Sistem Hatası: API Anahtarı (Secrets) bulunamadı.")
        else:
            with st.spinner("Yapay zeka soruları hazırlıyor..."):
                text = pdf_oku(uploaded_file)
                st.session_state['pdf_sorular'] = sorulari_uret_otomatik(text, api_key)
                st.rerun()

    if st.session_state['pdf_sorular']:
        with st.form("pdf_test"):
            cevaplar = {}
            for i, q in enumerate(st.session_state['pdf_sorular']):
                st.markdown(f"**{i+1}. {q['soru']}**")
                cevaplar[i] = st.radio("Cevap:", q['secenekler'], key=f"p_{i}", label_visibility="collapsed")
                st.write("---")
            
            if st.form_submit_button("Testi Bitir"):
                dogru = 0
                st.write("### 📊 Sonuçlar")
                for i, q in enumerate(st.session_state['pdf_sorular']):
                    if cevaplar.get(i) == q['dogru_cevap']:
                        dogru += 1
                        st.success(f"**{i+1}.** Doğru ✅")
                    else:
                        st.error(f"**{i+1}.** Yanlış ❌ (Doğru: {q['dogru_cevap']})")
                st.metric("Puan", int(dogru/len(st.session_state['pdf_sorular'])*100))

# --- MOD 2: Kütüphane ---
elif secim == "📚 Hazır Soru Kütüphanesi":
    st.subheader("Konu Tarama Testleri")
    try:
        dersler = list(soru_bankasi.kutuphane.keys())
        secilen_ders = st.selectbox("Ders Seç:", dersler)
        konular = list(soru_bankasi.kutuphane[secilen_ders].keys())
        secilen_konu = st.selectbox("Konu Seç:", konular)
        sorular = soru_bankasi.kutuphane[secilen_ders][secilen_konu]
        
        st.write(f"📝 **{secilen_konu}** testi başlıyor! ({len(sorular)} Soru)")
        st.divider()
        
        with st.form("lib_test"):
            lib_cevaplar = {}
            for i, q in enumerate(sorular):
                st.markdown(f"**{i+1}. {q['soru']}**")
                lib_cevaplar[i] = st.radio("Cevap:", q['secenekler'], key=f"l_{i}", label_visibility="collapsed")
                st.write("")
            
            if st.form_submit_button("Testi Bitir"):
                dogru = 0
                st.write("### 📊 Sonuçlar")
                for i, q in enumerate(sorular):
                    if lib_cevaplar.get(i) == q['dogru_cevap']:
                        dogru += 1
                        st.success(f"**{i+1}.** Doğru ✅")
                    else:
                        st.error(f"**{i+1}.** Yanlış ❌ (Doğru: {q['dogru_cevap']})")
                
                skor = int(dogru/len(sorular)*100)
                st.metric("Toplam Puan", skor)
                if skor >= 70: st.balloons()
                
    except Exception as e:
        st.warning("Henüz soru kütüphanesi oluşturulmamış.")
        # st.write(e)

# Footer
st.markdown('<div class="footer">Made with ❤️ by <b>GeoFurkan</b></div>', unsafe_allow_html=True)
