import streamlit as st
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import io

# Pode ser necessário configurar o caminho para o Tesseract no Streamlit Cloud
# Mas para a maioria dos casos, não é preciso se estiver instalado corretamente.
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

def ocr_pdf(uploaded_file):
    """Processa um PDF escaneado e retorna o texto extraído."""
    text_data = ""
    
    # Converte PDF para uma lista de imagens PIL
    images = convert_from_bytes(uploaded_file.read(), dpi=300)

    for i, image in enumerate(images):
        # Pré-processamento da imagem (exemplo básico)
        processed_image = image.convert("L")  # Converte para tons de cinza
        
        # O Pytesseract pode receber a imagem diretamente
        # O Tesseract faz um pré-processamento interno, mas o nosso melhora a precisão
        text = pytesseract.image_to_string(processed_image, lang='por')
        text_data += f"\n--- Página {i+1} ---\n{text}"

    return text_data

st.title("Leitor de OCR para PDFs Escaneados")

uploaded_file = st.file_uploader("Escolha um PDF escaneado", type="pdf")

if uploaded_file is not None:
    st.info("Processando o PDF. Isso pode levar alguns minutos...")
    extracted_text = ocr_pdf(uploaded_file)
    
    st.subheader("Texto Extraído:")
    st.text_area("Resultado", extracted_text, height=500)
    
    st.download_button(
        label="Baixar texto",
        data=extracted_text,
        file_name="texto_extraido.txt",
        mime="text/plain"
    )
