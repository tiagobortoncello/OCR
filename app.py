import streamlit as st
from PIL import Image
from io import BytesIO
import fitz  # PyMuPDF

# --- OCR Functions (leve, sem easyocr no início) ---
def get_ocr_reader():
    import easyocr
    return easyocr.Reader(['pt', 'en'], gpu=False, verbose=False)

def ocr_with_columns(pil_img, num_columns=2):
    reader = get_ocr_reader()
    width, height = pil_img.size
    col_width = width // num_columns
    texts = []
    for i in range(num_columns):
        left = i * col_width
        right = width if i == num_columns - 1 else (i + 1) * col_width
        col = pil_img.crop((left, 0, right, height))
        buf = BytesIO()
        col.save(buf, format='PNG')
        results = reader.readtext(buf.getvalue(), detail=0, paragraph=True)
        txt = " ".join(results).strip()
        if txt:
            texts.append(txt)
    return " ".join(texts)

def process_image(pil_img):
    if pil_img.width > 1800:
        ratio = 1800 / pil_img.width
        pil_img = pil_img.resize((1800, int(pil_img.height * ratio)), Image.LANCZOS)
    return ocr_with_columns(pil_img, num_columns=2)

def process_pdf(pdf_bytes):
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        all_text = []
        for i in range(min(doc.page_count, 3)):  # até 3 páginas
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=100)
            img = Image.open(BytesIO(pix.tobytes("png")))
            with st.spinner(f"Página {i+1}..."):
                text = process_image(img)
                if text.strip():
                    all_text.append(f"[Pág {i+1}]\n{text}")
        doc.close()
        return "\n\n".join(all_text)
    except Exception as e:
        st.error("Erro ao processar PDF.")
        return ""

# --- Interface LEVE ---
st.set_page_config(page_title="OCR para Jornais Antigos", layout="centered")
st.title("🗞️ OCR para Jornais com Colunas")
st.caption("Extrai texto de PDFs/imagem de jornais antigos (2 colunas).")

uploaded = st.file_uploader("Envie imagem ou PDF", type=["png", "jpg", "jpeg", "pdf"])

if uploaded:
    if uploaded.type == "application/pdf":
        with st.spinner("Processando PDF..."):
            text = process_pdf(uploaded.read())
    else:
        img = Image.open(uploaded)
        with st.spinner("Lendo por colunas..."):
            text = process_image(img)

    if text and text.strip():
        st.subheader("Texto extraído:")
        st.text_area("Copie o texto abaixo para corrigir manualmente ou em outra ferramenta:",
                     text, height=300)
    else:
        st.warning("Nenhum texto detectado.")
