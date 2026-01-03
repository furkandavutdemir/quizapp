import streamlit as st
import PyPDF2
import requests
import json

# --- SAYFA AYARLARI VE STİL (Tasarım buradan başlar) ---
st.set_page_config(
    page_title="QuizApp by GeoFurkan",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="collapsed" # Kenar çubuğunu başlangıçta kapalı tut
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
}
.stButton>button {
    width: 100%; # Butonları tam genişlik yap
    border-radius: 10px; # Kenarları yuvarlat
}
</style>
""", unsafe_allow_html=True)

# --- FONKSİYONLAR (Burası uygulamanın beyni, dokunmuyoruz) ---

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
    """API anahtarının izin verdiği en hızlı modeli otomatik bulur."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            modeller = response.json().get('models', [])
            uygunlar = [m['name'] for m in modeller if 'generateContent' in m.get('supportedGenerationMethods', [])]
            if not uygunlar: return None
            # Flash modeli öncelikli, yoksa Pro, yoksa ilk bulduğunu al
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
            "secenekler": ["A) Seçenek 1", "B) Seçenek 2", "C) Seçenek 3", "D) Seçenek 4"],
            "dogru_cevap": "A) Seçenek 1"
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

# --- MODERN ARAYÜZ TASARIMI ---

# 1. Üst Kısım (Header): Logo ve Başlık
col_logo, col_title = st.columns([1, 4]) # Ekranı 1'e 4 oranında ikiye böl

with col_logo:
    # --- LOGO AYARI ---
    # Eğer 'logo.png' adında bir resmin varsa alttaki satırın başındaki # işaretini kaldır.
    # st.image("logo.png", width=100) 
    st.markdown("# 📚") # Logo yoksa bu emoji görünür

with col_title:
    st.title("QuizApp")
    st.caption("Yapay Zeka Destekli Soru Üretme Asistanı.| GEOFURKAN iyi çalışmalar diler.")

st.divider() # İnce bir çizgi çek

# 2. Giriş Alanı (Daha derli toplu görünüm için Expander kullandık)
with st.expander("⚙️ Kurulum ve Dosya Yükleme", expanded=True):
    col_api, col_upload = st.columns(2) # İki sütun yan yana
    
    with col_api:
        api_key = st.text_input("🔑 Google API Anahtarı", type="password", help="aistudio.google.com adresinden alınan anahtar.")
        if not api_key:
             st.info("👆 Devam etmek için lütfen API anahtarını gir.")

    with col_upload:
        uploaded_file = st.file_uploader("📄 PDF Ders Notunu Buraya Sürükle", type="pdf")
        if uploaded_file:
            st.success(f"✅ '{uploaded_file.name}' yüklendi!")

# Session State (Verileri hafızada tutmak için)
if 'sorular' not in st.session_state: st.session_state['sorular'] = None

# 3. Soru Üretme Butonu
st.write("") # Biraz boşluk
if uploaded_file and api_key:
    # primary tipi butonu renkli yapar
    if st.button("🚀 Soruları Oluştur ve Testi Başlat", type="primary"):
        with st.spinner("🧠 Yapay zeka metni okuyor ve soruları hazırlıyor... Biraz sabır."):
            text = pdf_oku(uploaded_file)
            st.session_state['sorular'] = sorulari_uret_otomatik(text, api_key)

# 4. Test Alanı (Sorular varsa burası görünür)
if st.session_state['sorular']:
    st.divider()
    st.subheader("📝 Test Zamanı")
    
    with st.form("quiz_form"):
        soru_listesi = st.session_state['sorular']
        kullanici_cevaplari = {}
        
        for i, soru in enumerate(soru_listesi):
            st.markdown(f"##### {i+1}. {soru['soru']}") # Soruları biraz daha belirgin yap
            kullanici_cevaplari[i] = st.radio(
                "Cevabınız:", 
                soru['secenekler'], 
                key=f"q_{i}",
                label_visibility="collapsed" # "Cevabınız" yazısını gizle, daha temiz görünsün
            )
            st.write("---") # Sorular arasına çizgi
            
        if st.form_submit_button("✅ Testi Bitir ve Sonuçları Gör"):
            st.balloons() # Başarı efekti (Balonlar uçar!)
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

# 5. GeoFurkan İmzası (Sabit Alt Bilgi - Footer)
st.markdown("""
<div class="footer">
   <b>GeoFurkan</b> | QuizApp
</div>
""", unsafe_allow_html=True)