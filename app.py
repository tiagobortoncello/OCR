import streamlit as st
from PIL import Image
import requests
from io import BytesIO
import fitz  # PyMuPDF

# Configurações
MODEL_NAME = "Qwen/Qwen2-0.5B-Instruct"
HF_TOKEN = st.secrets.get("HF_API_TOKEN", "")

if not HF_TOKEN:
    st.error("❌ HF_API_TOKEN não configurado nos Secrets.")
    st.stop()

# Carrega OCR apenas quando usado (sem cache pesado no início)
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
    response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    if response.status_code == 200:
        return response.json()[0]["generated_text"]
    else:
        st.error(f"Erro na API: {response.status_code}")
        return None

def ocr_image(pil_img):
    reader = get_ocr_reader()
    img_bytes = BytesIO()
    # Reduz tamanho se muito grande (evita crash)
    if pil_img.width > 1500 or pil_img.height > 1500:
        pil_img = pil_img.resize((int(pil_img.width * 0.7), int(pil_img.height * 0.7)), Image.LANCZOS)
    pil_img.save(img_bytes, format='PNG')
    results = reader.readtext(img_bytes.getvalue(), detail=0, paragraph=True)
    return " ".join(results)

def process_pdf(pdf_bytes):
    try:
        pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        full_text = []
        for i in range(min(pdf_doc.page_count, 5)):  # Máx 5 páginas
            page = pdf_doc.load_page(i)
            # Usa DPI baixo para economizar memória
            pix = page.get_pixmap(dpi=100)  # era 150–200, agora 100
            img_data = pix.tobytes("png")
            img = Image.open(BytesIO(img_data))
            with st.spinner(f"Página {i+1}..."):
                text = ocr_image(img)
                if text.strip():
                    full_text.append(f"[Pág {i+1}] {text}")
        pdf_doc.close()
        return "\n\n".join(full_text)
    except Exception as e:
        st.error("Erro ao processar PDF. Tente um arquivo menor.")
        return ""

# Interface
st.title("📄 OCR Leve + Qwen")
st.caption("Suporta imagens e PDFs (máx. 5 páginas)")

uploaded = st.file_uploader("Envie imagem ou PDF", type=["png", "jpg", "jpeg", "pdf"])

if uploaded:
    if uploaded.type == "application/pdf":
        with st.spinner("Lendo PDF..."):
            text = process_pdf(uploaded.read())
    else:
        img = Image.open(uploaded)
        if img.width * img.height > 2_000_000:  # ~2MP
            st.warning("Imagem grande — pode demorar ou falhar.")
        with st.spinner("Extraindo texto..."):
            text = ocr_image(img)

    if text and text.strip():
        st.text_area("Texto extraído", text[:2000] + "..." if len(text) > 2000 else text, height=150)
        prompt = st.text_input("Instrução para o Qwen:", "Resuma o texto.")
        if st.button("Enviar"):
            resp = query_qwen(f"{prompt}\n\nTexto:\n{text[:1500]}")  # Limita tokens
            if resp:
                st.write("**Resposta:**", resp)
    else:
        st.warning("Nenhum texto encontrado.")
