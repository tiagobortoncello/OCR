import streamlit as st
import easyocr
from PIL import Image
import fitz  # PyMuPDF
import numpy as np

# --- Configuração do EasyOCR ---
# Cria uma instância do leitor de OCR.
# 'gpu=False' garante que ele funcione na CPU no Streamlit Cloud.
# 'lang_list=['pt']' especifica o idioma português.
reader = easyocr.Reader(['pt'], gpu=False)

def ocr_pdf(uploaded_file):
    """
    Processa um PDF escaneado e extrai o texto usando PyMuPDF e EasyOCR.
    """
    text_data = ""
    
    try:
        pdf_document = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    except Exception as e:
        st.error(f"Não foi possível abrir o arquivo PDF. Erro: {e}")
        return ""

    for i, page in enumerate(pdf_document):
        # Renderiza a página como uma imagem (pixmap) com alta resolução
        pixmap = page.get_pixmap(dpi=300)
        
        # Converte o pixmap para um array NumPy, que é o formato ideal para o EasyOCR
        img = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, pixmap.n)

        # Usa o EasyOCR para extrair o texto
        results = reader.readtext(img, detail=0)  # 'detail=0' retorna apenas o texto
        
        # Junta todas as linhas de texto em um único bloco
        page_text = "\n".join(results)
        
        text_data += f"\n--- Página {i+1} ---\n{page_text}\n"

    pdf_document.close()
    
    return text_data

# --- Interface Streamlit ---

st.title("Leitor de OCR para PDFs Escaneados")
st.markdown("Faça o upload de um PDF escaneado ou antigo para extrair o texto.")

uploaded_file = st.file_uploader("Escolha um arquivo PDF...", type="pdf")

if uploaded_file is not None:
    with st.spinner("Processando o PDF... Isso pode levar alguns minutos dependendo do tamanho do arquivo."):
        extracted_text = ocr_pdf(uploaded_file)
    
    if extracted_text:
        st.success("Texto extraído com sucesso!")
        st.subheader("Texto Extraído:")
        st.text_area("Resultado", extracted_text, height=500)
        
        st.download_button(
            label="Baixar texto extraído",
            data=extracted_text,
            file_name="texto_do_pdf.txt",
            mime="text/plain"
        )
