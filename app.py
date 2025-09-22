import streamlit as st
import easyocr
from PIL import Image
import numpy as np
import cv2

st.set_page_config(page_title="OCR Online Avançado", layout="centered")
st.title("📄 OCR Avançado com Streamlit Cloud")

# Função de pré-processamento
def preprocess_image(pil_image):
    # Converter para array OpenCV
    img = np.array(pil_image.convert('RGB'))
    img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Remover ruído
    img_denoised = cv2.fastNlMeansDenoising(img_gray, h=30)

    # Aumentar contraste
    img_eq = cv2.equalizeHist(img_denoised)

    # Binarização adaptativa
    img_bin = cv2.adaptiveThreshold(
        img_eq, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    # Deskew (corrigir inclinação)
    coords = np.column_stack(np.where(img_bin > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = img_bin.shape
    M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
    img_rotated = cv2.warpAffine(img_bin, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    return img_rotated

# Upload de imagem
uploaded_file = st.file_uploader("Carregue uma imagem (PNG, JPG, JPEG)", type=["png","jpg","jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Imagem enviada", use_column_width=True)

    # Botão para processar OCR
    if st.button("🔍 Extrair Texto"):
        with st.spinner("Processando imagem e extraindo texto..."):
            # Pré-processar
            processed_img = preprocess_image(image)

            # Executar OCR
            reader = easyocr.Reader(['pt'])
            result = reader.readtext(processed_img, detail=0)
            text = "\n".join(result)

        st.subheader("📑 Texto extraído:")
        st.text_area("Resultado", text, height=300)

        # Botão para download
        st.download_button(
            label="📥 Baixar texto",
            data=text,
            file_name="ocr_resultado.txt",
            mime="text/plain"
        )
