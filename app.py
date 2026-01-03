import streamlit as st
import PyPDF2
import requests
import json

# --- SAYFA AYARLARI VE STİL ---
st.set_page_config(
    page_title="QuizApp by GeoFurkan",
    page_icon="logo.png", # Tarayıcı sekmesinde de logo görünür
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Özel CSS ile Alt Bilgi (Footer) Tasarımı
st.markdown("""
<style>
.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: #f0f2f6;
    color: #555;
    text-align: center;
    padding: 10px;
    font-size: 14px;
    border-top: 1px solid #e0e0e0;
    z-index: 100;
}
.stButton>button {
    width: 100%;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# --- FONKSİYONLAR ---

def pdf_oku(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def temizle_json(metin):
    metin = metin.replace("```json", "").replace("```", "").strip()
    return metin

def en_uygun_modeli_bul(api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            modeller = response.json().get('models', [])
            uygunlar = [m['name'] for m in modeller if 'generateContent' in m.get('supportedGenerationMethods', [])]
            if not uygunlar: return None
            secilen = next((m for m in uygunlar if 'flash' in m), 
                           next((m for m in uygunlar if 'pro' in m), uygunlar[0]))
            return secilen.replace("models/", "")
        return None
    except:
        return None

def sorulari_uret_otomatik(text, api_key):
    model_adi = en_uygun_modeli_bul(api_key)
    if not model_adi:
        st.error("🚨 Uygun bir AI modeli bulunamadı. API Key'i kontrol et.")
        return []
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_adi}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    prompt = f"""
    Sen uzman bir sınav hazırlayıcısın. Aşağıdaki metni analiz et ve tam 5 adet kaliteli çoktan seçmeli soru hazırla.
    Cevabı SADECE şu JSON formatında ver (başka hiçbir metin ekleme):
    [
        {{
            "soru": "Soru metni buraya...",
            "secenekler": ["A) ...", "B) ...", "C) ...", "D) ..."],
            "dogru_cevap": "A) ..."
        }}
    ]
    Metin: {text[:5000]}
    """
    
    try:
        response = requests.post(url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        if response.status_code == 200:
            ham_metin = response.json()['candidates'][0]['content']['parts'][0]['text']
            return json.loads(temizle_json(ham_metin))
    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
    return []

# --- ARAYÜZ ---

# 1. Header (Logo ve Başlık)
col_logo, col_title = st.columns([1, 4])

with col_logo:
    # LOGO BURAYA EKLENDİ
    try:
        st.image("logo.png", width=120)
    except:
        st.markdown("# 📚") # Eğer logo dosyası yoksa emoji koyar

with col_title:
    st.title("QuizApp")
    st.caption("Yapay Zeka Destekli Soru Üretme Asistanı | GeoFurkan iyi çalışmalar diler.")

st.divider()

# 2. Giriş Alanı
with st.expander("⚙️ Kurulum ve Dosya Yükleme", expanded=True):
    col_api, col_upload = st.columns(2)
    
    with col_api:
        # Şifre kutusunu kaldırdık!
        # Kod, anahtarı gizli kasadan (secrets) çekmeye çalışacak.
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]
            st.success("✅ Sistem Hazır (GeoFurkan Key Aktif)")
        else:
            # Eğer kasada anahtar bulamazsa (kendi bilgisayarında test ederken) elle girmeni ister
            api_key = st.text_input("🔑 Google API Anahtarı", type="password")
        
        # YARDIM KUTUSU BURAYA EKLENDİ
        with st.expander("❓ Anahtarı ücretsiz nasıl alırım?"):
            st.markdown("""
            1. **[Buraya tıklayarak Google AI Studio](https://aistudio.google.com/app/apikey)** sayfasına git.
            2. **"Create API Key"** butonuna bas.
            3. Oluşan kodu kopyala ve kutuya yapıştır.
            *Tamamen ücretsizdir.*
            """)

        if not api_key:
             st.info("👆 Devam etmek için lütfen API anahtarını gir.")

    with col_upload:
        uploaded_file = st.file_uploader("📄 PDF Ders Notunu Buraya Sürükle", type="pdf")
        if uploaded_file:
            st.success(f"✅ '{uploaded_file.name}' yüklendi!")

# Session State
if 'sorular' not in st.session_state: st.session_state['sorular'] = None

# 3. Buton
st.write("")
if uploaded_file and api_key:
    if st.button("🚀 Soruları Oluştur ve Testi Başlat", type="primary"):
        with st.spinner("🧠 Yapay zeka metni okuyor ve soruları hazırlıyor... Biraz sabır."):
            text = pdf_oku(uploaded_file)
            st.session_state['sorular'] = sorulari_uret_otomatik(text, api_key)

# 4. Test Alanı
if st.session_state['sorular']:
    st.divider()
    st.subheader("📝 Test Zamanı")
    
    with st.form("quiz_form"):
        soru_listesi = st.session_state['sorular']
        kullanici_cevaplari = {}
        
        for i, soru in enumerate(soru_listesi):
            st.markdown(f"##### {i+1}. {soru['soru']}")
            kullanici_cevaplari[i] = st.radio(
                "Cevabınız:", 
                soru['secenekler'], 
                key=f"q_{i}",
                label_visibility="collapsed"
            )
            st.write("---")
            
        if st.form_submit_button("✅ Testi Bitir ve Sonuçları Gör"):
            st.balloons()
            dogru_sayisi = 0
            st.write("### 📊 Sonuçlarınız")
            for i, soru in enumerate(soru_listesi):
                secilen = kullanici_cevaplari.get(i)
                dogru = soru['dogru_cevap']
                if secilen == dogru:
                    dogru_sayisi += 1
                    st.success(f"**Soru {i+1}:** Doğru! ({secilen})")
                else:
                    st.error(f"**Soru {i+1}:** Yanlış. (Sizin Cevabınız: {secilen} | Doğru Cevap: {dogru})")
            
            puan = int((dogru_sayisi / len(soru_listesi)) * 100)
            st.metric(label="Toplam Puan", value=f"{puan} / 100")

# 5. Footer
st.markdown("""
<div class="footer">
   <b>GeoFurkan</b> | QuizApp
</div>
""", unsafe_allow_html=True)
