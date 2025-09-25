import streamlit as st
from PIL import Image
import requests
from io import BytesIO
import fitz  # PyMuPDF

# Configurações
MODEL_NAME = "Qwen/Qwen2-0.5B-Instruct"
HF_TOKEN = st.secrets.get("HF_API_TOKEN", "")

if not HF_TOKEN:
    st.error("❌ HF_API_TOKEN não configurado.")
    st.stop()

def get_ocr_reader():
    import easyocr
    return easyocr.Reader(['pt', 'en'], gpu=False, verbose=False)

def query_qwen(prompt):
    API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 512, "temperature": 0.6}
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()[0]["generated_text"]
        else:
            st.error(f"Erro na API: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Timeout ou erro de rede: {str(e)}")
        return None

def ocr_with_columns(pil_img, num_columns=2):
    """
    Divide a imagem em colunas verticais e aplica OCR em cada uma (da esquerda para direita).
    """
    reader = get_ocr_reader()
    width, height = pil_img.size
    column_width = width // num_columns

    full_text = []
    for i in range(num_columns):
        left = i * column_width
        right = (i + 1) * column_width if i < num_columns - 1 else width
        column_img = pil_img.crop((left, 0, right, height))

        # Converte para bytes
        img_bytes = BytesIO()
        column_img.save(img_bytes, format='PNG')
        results = reader.readtext(img_bytes.getvalue(), detail=0, paragraph=True)
        col_text = " ".join(results).strip()
        if col_text:
            full_text.append(col_text)

    return " ".join(full_text)

def process_image_for_ocr(pil_img):
    # Reduz resolução se muito grande
    if pil_img.width > 1800:
        ratio = 1800 / pil_img.width
        new_size = (1800, int(pil_img.height * ratio))
        pil_img = pil_img.resize(new_size, Image.LANCZOS)
    return ocr_with_columns(pil_img, num_columns=2)  # Ajuste para 3 se necessário

def process_pdf(pdf_bytes):
    try:
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        full_text = []
        for i in range(min(pdf_doc.page_count, 3)):  # Máx 3 páginas
            page = pdf_doc.load_page(i)
            pix = page.get_pixmap(dpi=120)  # DPI moderado
            img_data = pix.tobytes("png")
            img = Image.open(BytesIO(img_data))
            with st.spinner(f"Processando página {i+1}..."):
                text = process_image_for_ocr(img)
                if text.strip():
                    full_text.append(f"[Pág {i+1}]\n{text}")
        pdf_doc.close()
        return "\n\n".join(full_text)
    except Exception as e:
        st.error("Erro ao processar PDF. Tente um arquivo menor.")
        return ""

# Interface
st.set_page_config(page_title="OCR por Colunas", layout="centered")
st.title("🗞️ OCR para Jornais (Leitura por Colunas)")
st.caption("Ideal para jornais antigos com 2 colunas. Suporta PDF e imagens.")

uploaded = st.file_uploader("Envie imagem ou PDF", type=["png", "jpg", "jpeg", "pdf"])

if uploaded:
    if uploaded.type == "application/pdf":
        with st.spinner("Convertendo PDF..."):
            text = process_pdf(uploaded.read())
    else:
        img = Image.open(uploaded)
        with st.spinner("Extraindo texto por colunas..."):
            text = process_image_for_ocr(img)

    if text and text.strip():
        st.text_area("Texto extraído", text[:2000] + "..." if len(text) > 2000 else text, height=200)
        prompt = st.text_input(
            "Instrução para o Qwen:",
            "Corrija erros de OCR e reescreva o texto em ordem correta, mantendo o estilo de jornal antigo."
        )
        if st.button("Enviar para Qwen"):
            # Limita o texto para evitar estouro de tokens
            limited_text = text[:1200]
            resp = query_qwen(f"{prompt}\n\nTexto:\n{limited_text}")
            if resp:
                st.subheader("Resposta:")
                st.write(resp)
    else:
        st.warning("Nenhum texto detectado.")
