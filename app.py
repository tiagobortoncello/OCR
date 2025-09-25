import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter
import easyocr
import requests
from io import BytesIO
import fitz  # PyMuPDF

# Configurações
MODEL_NAME = "Qwen/Qwen2-0.5B-Instruct"
HF_TOKEN = st.secrets.get("HF_API_TOKEN", "")

if not HF_TOKEN:
    st.error("❌ Chave de API do Hugging Face não configurada. Adicione 'HF_API_TOKEN' nos Secrets do Streamlit Cloud.")
    st.stop()

@st.cache_resource
def load_ocr():
    # Carrega EasyOCR com suporte a português (e inglês, útil em textos antigos)
    return easyocr.Reader(['pt', 'en'], gpu=False)

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

def preprocess_image_for_ocr(pil_image):
    """Melhora a imagem para OCR: escala de cinza, contraste, binarização."""
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    gray = pil_image.convert('L')
    enhancer = ImageEnhance.Contrast(gray)
    contrasted = enhancer.enhance(2.0)
    # Binarização com limiar ajustado para textos antigos
    threshold = 140
    bw = contrasted.point(lambda x: 0 if x < threshold else 255, '1')
    # Redução leve de ruído
    bw = bw.filter(ImageFilter.MedianFilter(size=3))
    return bw

def extract_text_from_image_pil(pil_image):
    """Extrai texto de imagem com pré-processamento + EasyOCR."""
    processed = preprocess_image_for_ocr(pil_image)
    img_bytes = BytesIO()
    processed.save(img_bytes, format='PNG')
    reader = load_ocr()
    results = reader.readtext(
        img_bytes.getvalue(),
        detail=0,
        paragraph=True,
        min_size=10,
        contrast_ths=0.1,
        adjust_contrast=0.7
    )
    return " ".join(results)

def extract_text_from_scanned_pdf(pdf_bytes):
    """Converte PDF escaneado em imagens e aplica OCR com pré-processamento."""
    try:
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        full_text = []
        for page_num in range(pdf_document.page_count):
            page = pdf_document.load_page(page_num)
            mat = fitz.Matrix(2.0, 2.0)  # Aumenta resolução para melhor OCR
            pix = page.get_pixmap(matrix=mat, dpi=200)
            img_data = pix.tobytes("png")
            pil_img = Image.open(BytesIO(img_data))
            with st.spinner(f"🔍 Processando página {page_num + 1}..."):
                text = extract_text_from_image_pil(pil_img)
                if text.strip():
                    full_text.append(f"[Página {page_num + 1}]\n{text}")
        pdf_document.close()
        return "\n\n".join(full_text)
    except Exception as e:
        st.error(f"Erro ao processar PDF escaneado: {str(e)}")
        return ""

# Interface do app
st.set_page_config(page_title="OCR para Documentos Antigos + Qwen", layout="centered")
st.title("📜 OCR para Jornais Antigos & PDFs Escaneados")
st.write("""
Envie **imagens (PNG/JPG)** ou **PDFs escaneados** (ex: jornais, livros antigos, documentos manuscritos).  
O app usa pré-processamento avançado para melhorar a leitura de textos antigos.
""")

uploaded = st.file_uploader(
    "Escolha um arquivo",
    type=["png", "jpg", "jpeg", "pdf"]
)

if uploaded:
    file_type = uploaded.type
    extracted_text = ""

    if file_type == "application/pdf":
        st.info("📄 Processando PDF escaneado... (pode demorar um pouco)")
        pdf_bytes = uploaded.read()
        extracted_text = extract_text_from_scanned_pdf(pdf_bytes)
    else:
        image = Image.open(uploaded)
        st.image(image, caption="Imagem carregada", use_column_width=True)
        with st.spinner("🔍 Extraindo texto com OCR melhorado..."):
            extracted_text = extract_text_from_image_pil(image)

    if extracted_text.strip():
        st.subheader("Texto extraído:")
        st.text_area("Texto OCR", extracted_text, height=250)

        instruction = st.text_input(
            "O que você quer que o Qwen faça com esse texto?",
            "Corrija erros de OCR e reescreva o texto de forma clara e legível."
        )

        if st.button("Enviar para o Qwen"):
            full_prompt = f"{instruction}\n\nTexto com possíveis erros de OCR:\n{extracted_text}"
            with st.spinner("🧠 Processando com Qwen-0.5B..."):
                resposta = query_qwen(full_prompt)
                if resposta:
                    st.subheader("Resposta do Qwen:")
                    st.write(resposta)
    else:
        st.warning("⚠️ Nenhum texto foi encontrado. Tente com uma imagem mais nítida ou com melhor contraste.")
