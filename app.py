import streamlit as st
import easyocr
from PIL import Image
import requests
from io import BytesIO

# Configurações
MODEL_NAME = "Qwen/Qwen2-0.5B-Instruct"
HF_TOKEN = st.secrets["HF_API_TOKEN"]

# Carrega o leitor OCR uma vez (cache)
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en', 'pt'])  # Adicione mais idiomas se quiser: 'es', 'fr', etc.

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

# Interface do app
st.set_page_config(page_title="OCR + Qwen Gratuito", layout="centered")
st.title("📄 OCR + Qwen-0.5B (Gratuito!)")
st.write("Envie uma imagem com texto. O app extrai o texto e envia para o Qwen analisar.")

uploaded = st.file_uploader("Escolha uma imagem", type=["png", "jpg", "jpeg"])

if uploaded:
    image = Image.open(uploaded)
    st.image(image, caption="Imagem carregada", use_column_width=True)

    with st.spinner("🔍 Extraindo texto da imagem..."):
        reader = load_ocr()
        img_bytes = BytesIO()
        image.save(img_bytes, format='PNG')
        result = reader.readtext(img_bytes.getvalue())
        text = " ".join([line[1] for line in result])

    if text.strip():
        st.subheader("Texto extraído:")
        st.text_area("OCR", text, height=120)

        instruction = st.text_input(
            "O que você quer que o Qwen faça com esse texto?",
            "Resuma o texto abaixo em uma frase curta."
        )

        if st.button("Enviar para o Qwen"):
            full_prompt = f"{instruction}\n\nTexto:\n{text}"
            with st.spinner("🧠 Processando com Qwen-0.5B..."):
                resposta = query_qwen(full_prompt)
                if resposta:
                    st.subheader("Resposta do Qwen:")
                    st.write(resposta)
    else:
        st.warning("⚠️ Nenhum texto foi encontrado na imagem.")
