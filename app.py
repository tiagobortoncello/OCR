import streamlit as st
import easyocr
from PIL import Image
import numpy as np
import cv2
import io
import pdfplumber
import fitz  # PyMuPDF

st.set_page_config(page_title="OCR Inteligente", layout="centered")
st.title("📄 OCR Inteligente: Imagem ou PDF")

# Função de pré-processamento para OCR
def preprocess_image(pil_image):
    img = np.array(pil_image.convert('RGB'))
    img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    img_denoised = cv2.fastNlMeansDenoising(img_gray, h=30)
    img_eq = cv2.equalizeHist(img_denoised)
    img_bin = cv2.adaptiveThreshold(
        img_eq, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    coords = np.column_stack(np.where(img_bin > 0))
    if coords.size == 0:
        return img_bin
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = img_bin.shape
    M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
    img_rotated = cv2.warpAffine(img_bin, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return img_rotated

# Escolha do tipo de arquivo
file_type = st.radio("Escolha o tipo de arquivo", ("Imagem", "PDF"))
uploaded_file = st.file_uploader("Carregue o arquivo", type=["png","jpg","jpeg","pdf"])

if uploaded_file:
    reader = easyocr.Reader(['pt'])

    if file_type == "Imagem":
        image = Image.open(uploaded_file)
        st.image(image, caption="Imagem enviada", use_column_width=True)

        if st.button("🔍 Extrair Texto"):
            with st.spinner("Processando imagem e extraindo texto..."):
                processed_img = preprocess_image(image)
                result = reader.readtext(processed_img, detail=0)
                text = "\n".join(result)

            st.subheader("📑 Texto extraído:")
            st.text_area("Resultado", text, height=300)

            st.download_button(
                label="📥 Baixar texto",
                data=text,
                file_name="ocr_resultado.txt",
                mime="text/plain"
            )

    else:  # PDF
        if st.button("🔍 Extrair Texto do PDF"):
            pdf_bytes = uploaded_file.read()
            text_output = []

            # Tenta PDF nativo primeiro
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                native_text_pages = []
                is_scanned = False
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        native_text_pages.append(page_text)
                    else:
                        is_scanned = True
                        break

            if not is_scanned:  # PDF nativo
                text_output = native_text_pages
                st.subheader("📑 Texto extraído do PDF (nativo):")
                st.text_area("Resultado", "\n\n".join(text_output), height=400)
            else:  # PDF escaneado
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                num_pages = doc.page_count

                st.subheader("⚙️ Configurações de OCR do PDF escaneado")
                start_page = st.number_input("Página inicial", min_value=1, max_value=num_pages, value=1)
                end_page = st.number_input("Página final", min_value=1, max_value=num_pages, value=min(5, num_pages))

                start_idx = int(start_page) - 1
                end_idx = int(end_page)

                with st.spinner("Processando páginas selecionadas..."):
                    for i in range(start_idx, end_idx):
                        page = doc[i]
                        pix = page.get_pixmap(dpi=150)  # DPI reduzido
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        processed_img = preprocess_image(img)
                        result = reader.readtext(processed_img, detail=0)
                        text_output.append(f"--- Página {i+1} ---\n" + "\n".join(result))
                        st.text_area(f"Página {i+1}", "\n".join(result), height=200)

                st.subheader("📑 Texto extraído do PDF (scan):")
                st.text_area("Resultado completo", "\n\n".join(text_output), height=400)

            st.download_button(
                label="📥 Baixar texto",
                data="\n\n".join(text_output),
                file_name="ocr_resultado.txt",
                mime="text/plain"
            )
