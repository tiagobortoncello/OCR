import streamlit as st
import base64
import requests

st.set_page_config(page_title="OCR Gemini API", layout="centered")
st.title("📄 OCR com Gemini API")

api_key = st.text_input("Insira sua API Key do Gemini", type="password")
uploaded_file = st.file_uploader("Carregue imagem ou PDF", type=["png","jpg","jpeg","pdf"])

if uploaded_file and api_key:
    if st.button("🔍 Extrair Texto via Gemini API"):
        with st.spinner("Enviando arquivo para a API Gemini..."):
            try:
                # Ler arquivo em bytes e converter para Base64
                file_bytes = uploaded_file.read()
                encoded_file = base64.b64encode(file_bytes).decode("utf-8")

                # Determinar formato do arquivo
                if uploaded_file.type == "application/pdf":
                    file_format = "PDF"
                else:
                    file_format = "IMAGE"

                # Montar payload correto para a API Gemini
                payload = {
                    "prompt": "Extrair todo o texto contido neste arquivo, mantendo a estrutura e separando páginas, se houver.",
                    "contents": [
                        {
                            "type": "FILE",
                            "format": file_format,
                            "data": encoded_file
                        }
                    ]
                }

                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"

                response = requests.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    # Dependendo do retorno da API, pode ser necessário ajustar o caminho para o texto
                    # Geralmente: data['candidates'][0]['content'] ou algo similar
                    text = ""
                    if "candidates" in data and len(data["candidates"]) > 0:
                        text = data["candidates"][0].get("content", "")
                    else:
                        text = str(data)

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
