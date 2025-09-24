import streamlit as st
import easyocr
from PIL import Image
import fitz  # PyMuPDF
import numpy as np

# Cache do EasyOCR para evitar recarregar o modelo repetidamente
@st.cache_resource
def init_ocr_reader():
    return easyocr.Reader(['pt'], gpu=False, model_storage_directory='/tmp/easyocr')

# Inicializa o leitor OCR
reader = init_ocr_reader()

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

    # Limita o número de páginas para evitar sobrecarga
    max_pages = 10
    if len(pdf_document) > max_pages:
        st.warning(f"O PDF tem {len(pdf_document)} páginas. Processando apenas as primeiras {max_pages} para evitar sobrecarga.")
    
    for i, page in enumerate(pdf_document[:max_pages]):
        try:
            # Renderiza a página com resolução reduzida (dpi=150) para economizar memória
            pixmap = page.get_pixmap(dpi=150)
            
            # Converte o pixmap para um array NumPy
            img = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, pixmap.n)
            
            # Libera a memória do pixmap imediatamente
            pixmap = None
            
            # Extrai o texto com EasyOCR, usando configurações otimizadas
            results = reader.readtext(img, detail=0, batch_size=1)  # batch_size=1 reduz uso de memória
            
            # Junta o texto da página
            page_text = "\n".join(results)
            text_data += f"\n--- Página {i+1} ---\n{page_text}\n"
            
            # Libera a memória da imagem
            img = None
            
        except Exception as e:
            st.warning(f"Erro ao processar a página {i+1}: {e}")
            continue
    
    pdf_document.close()
    return text_data

# Interface Streamlit
st.title("Leitor de OCR para PDFs Escaneados")
st.markdown("Faça upload de um PDF escaneado. Máximo de 10 páginas para garantir estabilidade.")

uploaded_file = st.file_uploader("Escolha um PDF...", type="pdf")

if uploaded_file is not None:
    # Verifica o tamanho do arquivo (limite de 10 MB para evitar sobrecarga)
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
