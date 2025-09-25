import streamlit as st
from PIL import Image
import easyocr
import requests
from io import BytesIO
from pdf2image import convert_from_bytes
import os

# Configurações
MODEL_NAME = "Qwen/Qwen2-0.5B-Instruct"
HF_TOKEN = st.secrets.get("HF_API_TOKEN", "")

if not HF_TOKEN:
    st.error("❌ Chave de API do Hugging Face não configurada. Adicione HF_API_TOKEN nos Secrets do Streamlit Cloud.")
    st.stop()

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en', 'pt'])  # Adicione outros idiomas se quiser

def query_qwen(prompt):
    API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 512,
            "temperature": 0.6,
            "return_full_text": False,
            "do_sample": True
        }
    }
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()[0]["generated_text"]
    else:
        st.error(f"Erro na API: {response.status_code} – {response.text}")
        return None

def extract_text_from_image(image):
    """Extrai texto de um objeto PIL.Image"""
    img_bytes = BytesIO()
    image.save(img_bytes, format='PNG')
    reader = load_ocr()
    results = reader.readtext(img_bytes.getvalue())
    return " ".join([res[1] for res in results])

def extract_text_from_pdf(pdf_bytes):
    """Converte PDF em imagens e aplica OCR em cada página"""
    try:
        # Converte PDF em lista de imagens (uma por página)
        images = convert_from_bytes(pdf_bytes, dpi=150)  # dpi=150 é bom equilíbrio
        all_text = []
        for i, image in enumerate(images):
            with st.spinner(f"🔍 Processando página {i+1} do PDF..."):
                text = extract_text_from_image(image)
                if text.strip():
                    all_text.append(f"[Página {i+1}]\n{text}")
        return "\n\n".join(all_text)
    except Exception as e:
        st.error(f"Erro ao processar PDF: {str(e)}")
        return ""

# Interface
st.set_page_config(page_title="OCR + Qwen (Imagem e PDF)", layout="centered")
st.title("📄 OCR + Qwen-0.5B")
st.write("Envie uma **imagem** (PNG/JPG) ou um **PDF**. O app extrai o texto e envia para o Qwen analisar.")

uploaded = st.file_uploader(
    "Escolha um arquivo",
    type=["png", "jpg", "jpeg", "pdf"]
)

if uploaded:
    file_type = uploaded.type
    extracted_text = ""

    if file_type == "application/pdf":
        st.info("📄 Arquivo PDF detectado. Convertendo páginas em imagens...")
        pdf_bytes = uploaded.read()
        extracted_text = extract_text_from_pdf(pdf_bytes)
    else:
        # Imagem
        image = Image.open(uploaded)
        st.image(image, caption="Imagem carregada", use_column_width=True)
        extracted_text = extract_text_from_image(image)

    if extracted_text.strip():
        st.subheader("Texto extraído:")
        st.text_area("OCR", extracted_text, height=200)

        instruction = st.text_input(
            "O que você quer que o Qwen faça com esse texto?",
            "Resuma o texto abaixo em uma frase curta."
        )

        if st.button("Enviar para o Qwen"):
            full_prompt = f"{instruction}\n\nTexto:\n{extracted_text}"
            with st.spinner("🧠 Processando com Qwen-0.5B..."):
                resposta = query_qwen(full_prompt)
                if resposta:
                    st.subheader("Resposta do Qwen:")
                    st.write(resposta)
    else:
        st.warning("⚠️ Nenhum texto foi encontrado no arquivo.")
