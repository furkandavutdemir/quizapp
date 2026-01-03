import streamlit as st
import PyPDF2
import requests
import json
# Yeni oluşturduğumuz soru bankası dosyasını içeri alıyoruz
import soru_bankasi

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="QuizApp by GeoFurkan",
    page_icon="logo.png",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- CSS VE TASARIM ---
st.markdown("""
<style>
.footer {position: fixed; left: 0; bottom: 0; width: 100%; background-color: #f0f2f6; color: #555; text-align: center; padding: 10px; border-top: 1px solid #e0e0e0; z-index: 100;}
.stButton>button {width: 100%; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

# --- FONKSİYONLAR ---
def pdf_oku(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages: text += page.extract_text()
    return text

def temizle_json(metin):
    return metin.replace("```json", "").replace("```", "").strip()

def sorulari_uret_otomatik(text, api_key):
    # Model bulma ve istek atma kısmı (Önceki kodun aynısı)
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
    Metin: {text[:5000]}"""
    
    try:
        resp = requests.post(url, headers={'Content-Type': 'application/json'}, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        if resp.status_code == 200:
            return json.loads(temizle_json(resp.json()['candidates'][0]['content']['parts'][0]['text']))
    except: pass
    return []

# --- ARAYÜZ BAŞLIYOR ---

# Header
c1, c2 = st.columns([1, 4])
with c1:
    try: st.image("logo.png", width=100)
    except: st.markdown("# 📚")
with c2:
    st.title("QuizApp")
    st.caption("GeoFurkan Eğitim Platformu")
st.divider()

# --- SOL MENÜ (NAVİGASYON) ---
st.sidebar.header("📌 Menü")
secim = st.sidebar.radio("Ne yapmak istersin?", ["📄 PDF'den Soru Üret", "📚 Hazır Soru Kütüphanesi"])

# --- MOD 1: PDF Soru Üretici ---
if secim == "📄 PDF'den Soru Üret":
    st.subheader("Yapay Zeka ile Soru Üret")
    with st.expander("⚙️ Ayarlar", expanded=True):
        api_key = st.text_input("Google API Key", type="password")
        uploaded_file = st.file_uploader("PDF Yükle", type="pdf")
    
    if 'pdf_sorular' not in st.session_state: st.session_state['pdf_sorular'] = None

    if uploaded_file and api_key and st.button("Soruları Oluştur", type="primary"):
        with st.spinner("Sorular hazırlanıyor..."):
            text = pdf_oku(uploaded_file)
            st.session_state['pdf_sorular'] = sorulari_uret_otomatik(text, api_key)
            st.rerun()

    # Testi Göster
    if st.session_state['pdf_sorular']:
        sorular = st.session_state['pdf_sorular']
        with st.form("pdf_form"):
            cevaplar = {}
            for i, q in enumerate(sorular):
                st.write(f"**{i+1}. {q['soru']}**")
                cevaplar[i] = st.radio("Cevap", q['secenekler'], key=f"pdf_{i}", label_visibility="collapsed")
                st.write("---")
            
            if st.form_submit_button("Sonuçları Gör"):
                dogru = 0
                for i, q in enumerate(sorular):
                    if cevaplar.get(i) == q['dogru_cevap']:
                        dogru += 1
                        st.success(f"Soru {i+1}: Doğru! ({q['dogru_cevap']})")
                    else:
                        st.error(f"Soru {i+1}: Yanlış. (Siz: {cevaplar.get(i)} | Doğru: {q['dogru_cevap']})")
                st.metric("Puan", f"{int(dogru/len(sorular)*100)}")

# --- MOD 2: Hazır Soru Kütüphanesi ---
elif secim == "📚 Hazır Soru Kütüphanesi":
    st.subheader("Konu Tarama Testleri")
    
    # 1. Ders Seçimi
    dersler = list(soru_bankasi.kutuphane.keys())
    secilen_ders = st.selectbox("Ders Seçiniz:", dersler)
    
    # 2. Konu Seçimi
    konular = list(soru_bankasi.kutuphane[secilen_ders].keys())
    secilen_konu = st.selectbox("Konu Seçiniz:", konular)
    
    # 3. Soruları Çek
    hazir_sorular = soru_bankasi.kutuphane[secilen_ders][secilen_konu]
    
    st.info(f"📢 **{secilen_ders}** dersi **{secilen_konu}** konusunda toplam **{len(hazir_sorular)}** soru var.")
    
    # Testi Başlat Butonu
    if 'lib_started' not in st.session_state: st.session_state['lib_started'] = False
    
    if st.button("Testi Başlat") or st.session_state['lib_started']:
        st.session_state['lib_started'] = True
        st.divider()
        
        with st.form("lib_form"):
            lib_cevaplar = {}
            for i, q in enumerate(hazir_sorular):
                st.markdown(f"##### {i+1}. {q['soru']}")
                lib_cevaplar[i] = st.radio("Cevabınız:", q['secenekler'], key=f"lib_{i}", label_visibility="collapsed")
                st.write("") # Boşluk
            
            st.write("---")
            if st.form_submit_button("Testi Bitir ve Kontrol Et"):
                d_sayisi = 0
                y_sayisi = 0
                st.write("### 📊 Test Sonucu")
                
                for i, q in enumerate(hazir_sorular):
                    secilen = lib_cevaplar.get(i)
                    dogru_sik = q['dogru_cevap']
                    
                    if secilen == dogru_sik:
                        d_sayisi += 1
                        st.success(f"**{i+1}. Soru:** ✅ Doğru")
                    else:
                        y_sayisi += 1
                        st.error(f"**{i+1}. Soru:** ❌ Yanlış (Doğru Cevap: {dogru_sik})")
                
                skor = int((d_sayisi / len(hazir_sorular)) * 100)
                c1, c2, c3 = st.columns(3)
                c1.metric("Doğru", d_sayisi)
                c2.metric("Yanlış", y_sayisi)
                c3.metric("PUAN", skor)
                
                if skor >= 70: st.balloons()

# Footer
st.markdown('<div class="footer">Made with ❤️ by <b>GeoFurkan</b></div>', unsafe_allow_html=True)
