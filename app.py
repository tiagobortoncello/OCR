import streamlit as st
import easyocr
from PIL import Image
import fitz  # PyMuPDF
import numpy as np
import cv2

# Cache do EasyOCR para evitar recarregar o modelo
@st.cache_resource
def init_ocr_reader():
    return easyocr.Reader(['pt'], gpu=False, model_storage_directory='/tmp/easyocr')

# Inicializa o leitor OCR
reader = init_ocr_reader()

def preprocess_image(img):
    """
    Pré-processa a imagem para melhorar a qualidade do OCR.
    """
    # Converte para escala de cinza
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    # Aplica binarização adaptativa para melhorar contraste
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return thresh

def ocr_pdf(uploaded_file):
    """
    Processa um PDF escaneado e extrai o texto usando PyMuPDF e EasyOCR.
    """
    text_data = ""
    
    try:
        pdf_document = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    except Exception as e:
        st.error(f"Erro ao abrir o PDF: {e}")
        return ""

    # Limita o número de páginas
    max_pages = 10
    if len(pdf_document) > max_pages:
        st.warning(f"O PDF tem {len(pdf_document)} páginas. Processando apenas as primeiras {max_pages} para evitar sobrecarga.")
    
    for i, page in enumerate(pdf_document[:max_pages]):
        try:
            # Renderiza a página com DPI=200 para melhor legibilidade
            pixmap = page.get_pixmap(dpi=200)
            
            # Converte o pixmap para um array NumPy
            img = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, pixmap.n)
            
            # Pré-processa a imagem
            img_processed = preprocess_image(img)
            
            # Libera a memória do pixmap
            pixmap = None
            
            # Extrai o texto com EasyOCR, ajustando parâmetros para PDFs antigos
            results = reader.readtext(img_processed, detail=0, contrast_ths=0.3, adjust_contrast=0.5)
            
            # Junta o texto da página
            page_text = "\n".join(results)
            text_data += f"\n--- Página {i+1} ---\n{page_text}\n"
            
            # Libera a memória da imagem
            img = None
            img_processed = None
            
        except Exception as e:
            st.warning(f"Erro ao processar a página {i+1}: {e}")
            continue
    
    pdf_document.close()
    return text_data

# Interface Streamlit
st.title("Leitor de OCR para PDFs Escaneados")
st.markdown("Faça upload de um PDF escaneado (máximo 10 MB, preferencialmente com boa qualidade de imagem).")

uploaded_file = st.file_uploader("Escolha um PDF...", type="pdf")

if uploaded_file is not None:
    if uploaded_file.size > 10 * 1024 * 1024:
        st.error("O arquivo é muito grande. Por favor, envie um PDF com menos de 10 MB.")
    else:
        with st.spinner("Processando o PDF... Pode levar alguns minutos."):
            extracted_text = ocr_pdf(uploaded_file)
        
        if extracted_text:
            st.success("Texto extraído com sucesso!")
            st.subheader("Texto Extraído:")
            st.text_area("Resultado", extracted_text, height=300)
            
            st.download_button(
                label="Baixar texto extraído",
                data=extracted_text,
                file_name="texto_do_pdf.txt",
                mime="text/plain"
            )
        else:
            st.warning("Nenhum texto foi extraído. Tente um PDF com melhor qualidade de imagem.")
