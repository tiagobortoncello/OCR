import streamlit as st
import requests

st.set_page_config(page_title="OCR Gemini API", layout="centered")
st.title("📄 OCR com Gemini API")

api_key = st.text_input("Insira sua API Key do Gemini", type="password")
uploaded_file = st.file_uploader("Carregue imagem ou PDF", type=["png","jpg","jpeg","pdf"])

if uploaded_file and api_key:
    if st.button("🔍 Extrair Texto via Gemini API"):
        with st.spinner("Enviando arquivo para a API Gemini..."):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"
            
            files = {"file": (uploaded_file.name, uploaded_file.read())}
            payload = {
                "prompt": "Extrair todo o texto contido neste arquivo, mantendo a estrutura e separando páginas, se houver."
            }
            
            try:
                response = requests.post(url, files=files, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    # Ajuste aqui dependendo de como a API retorna o texto
                    text = data.get("text", "") or str(data)
                    
                    st.subheader("📑 Texto extraído:")
                    st.text_area("Resultado", text, height=400)
                    
                    st.download_button(
                        label="📥 Baixar texto",
                        data=text,
                        file_name="ocr_resultado.txt",
                        mime="text/plain"
                    )
                else:
                    st.error(f"Erro na API: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"Erro ao conectar com a API: {e}")
