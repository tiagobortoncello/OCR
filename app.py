import streamlit as st
import easyocr
import fitz  # PyMuPDF
import numpy as np

# Cache do EasyOCR para carregar o modelo uma vez
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

    # Limita o número de páginas
    max_pages = 5  # Reduzido para maior estabilidade
    if len(pdf_document) > max_pages:
        st.warning(f"O PDF tem {len(pdf_document)} páginas. Processando apenas as primeiras {max_pages} para evitar sobrecarga.")
    
    for i, page in enumerate(pdf_document[:max_pages]):
        try:
            # Renderiza com DPI=150 para economizar memória
            pixmap = page.get_pixmap(dpi=150)
            
            # Converte para array NumPy
            img = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, pixmap.n)
            
            # Libera o pixmap
            pixmap = None
            
            # Extrai texto com EasyOCR, ajustando para PDFs antigos
            results = reader.readtext(img, detail=0, contrast_ths=0.3, batch_size=1)
            
            # Junta o texto da página
            page_text = "\n".join(results)
            text_data += f"\n--- Página {i+1} ---\n{page_text}\n"
            
            # Libera a imagem
            img = None
            
        except Exception as e:
            st.warning(f"Erro ao processar a página {i+1}: {e}")
            continue
    
    pdf_document.close()
    return text_data

# Interface Streamlit
st.title("Leitor de OCR para PDFs Escaneados")
st.markdown("Faça upload de um PDF escaneado (máximo 5 MB, preferencialmente com boa qualidade).")

uploaded_file = st.file_uploader("Escolha um PDF...", type="pdf")

if uploaded_file is not None:
    if uploaded_file.size > 5 * 1024 * 1024:  # Limite reduzido para 5 MB
        st.error("O arquivo é muito grande. Envie um PDF com menos de 5 MB.")
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
            st.warning("Nenhum texto foi extraído. Tente um PDF com maior nitidez ou fontes mais legíveis.")
