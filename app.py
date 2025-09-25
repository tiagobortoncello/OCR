import streamlit as st
from PIL import Image
import easyocr
import requests
from io import BytesIO
import fitz  # PyMuPDF

# Configurações
MODEL_NAME = "Qwen/Qwen2-0.5B-Instruct"
HF_TOKEN = st.secrets.get("HF_API_TOKEN", "")

if not HF_TOKEN:
    st.error("❌ Chave de API do Hugging Face não configurada. Adicione HF_API_TOKEN nos Secrets.")
    st.stop()

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en', 'pt'])  # Adicione 'es', 'fr' etc. se precisar

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

def extract_text_from_image_pil(pil_image):
    """Extrai texto de uma imagem PIL usando EasyOCR"""
    img_bytes = BytesIO()
    pil_image.save(img_bytes, format='PNG')
    reader = load_ocr()
    results = reader.readtext(img_bytes.getvalue())
    return " ".join([res[1] for res in results])

def extract_text_from_scanned_pdf(pdf_bytes):
    """Converte PDF escaneado em imagens e aplica OCR em cada página"""
    try:
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        full_text = []
        for page_num in range(pdf_document.page_count):
            page = pdf_document.load_page(page_num)
            # Renderiza a página como imagem (matriz de pixels)
            mat = fitz.Matrix(1.5, 1.5)  # Aumenta resolução para melhor OCR
            pix = page.get_pixmap(matrix=mat, dpi=150)
            # Converte para PIL Image
            img_data = pix.tobytes("png")
            pil_img = Image.open(BytesIO(img_data))
            # Aplica OCR
            with st.spinner(f"🔍 Processando página {page_num + 1}..."):
                text = extract_text_from_image_pil(pil_img)
                if text.strip():
                    full_text.append(f"[Página {page_num + 1}]\n{text}")
        pdf_document.close()
        return "\n\n".join(full_text)
    except Exception as e:
        st.error(f"Erro ao processar PDF escaneado: {str(e)}")
        return ""

# Interface
st.set_page_config(page_title="OCR + Qwen (PDF Escaneado OK!)", layout="centered")
st.title("📄 OCR para PDF Escaneado + Qwen")
st.write("Envie **imagens (PNG/JPG)** ou **PDFs escaneados** (com texto em imagem).")

uploaded = st.file_uploader(
    "Escolha um arquivo",
    type=["png", "jpg", "jpeg", "pdf"]
)

if uploaded:
    file_type = uploaded.type
    extracted_text = ""

    if file_type == "application/pdf":
        st.info("📄 Detectado PDF. Convertendo páginas em imagens para OCR...")
        pdf_bytes = uploaded.read()
        extracted_text = extract_text_from_scanned_pdf(pdf_bytes)
    else:
        # Imagem
        image = Image.open(uploaded)
        st.image(image, caption="Imagem carregada", use_column_width=True)
        extracted_text = extract_text_from_image_pil(image)

    if extracted_text.strip():
        st.subheader("Texto extraído:")
        st.text_area("Texto OCR", extracted_text, height=200)

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
