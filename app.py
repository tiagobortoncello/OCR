import streamlit as st
import pytesseract
from PIL import Image
import fitz  # O nome da biblioteca PyMuPDF que você importa

def ocr_pdf(uploaded_file):
    """
    Processa um PDF escaneado e extrai o texto de cada página usando PyMuPDF
    e Pytesseract.
    """
    text_data = ""
    
    # Abre o arquivo PDF com PyMuPDF (fitz)
    try:
        pdf_document = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    except Exception as e:
        st.error(f"Não foi possível abrir o arquivo PDF. Erro: {e}")
        return ""

    # Itera por cada página do PDF
    for i, page in enumerate(pdf_document):
        # Renderiza a página como uma imagem (pixmap) com alta resolução (300 DPI)
        pixmap = page.get_pixmap(dpi=300)
        
        # Converte o pixmap para um objeto de imagem PIL (Pillow)
        img = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)

        # Converte a imagem para tons de cinza para otimizar o OCR
        gray_image = img.convert("L")
        
        # Aplica o OCR do Tesseract na imagem processada
        # 'lang='por'' especifica o idioma português para maior precisão
        text = pytesseract.image_to_string(gray_image, lang='por')
        
        text_data += f"\n--- Página {i+1} ---\n{text}\n"

    # Fecha o documento PDF
    pdf_document.close()
    
    return text_data

# --- Interface Streamlit ---

st.title("Leitor de OCR para PDFs Escaneados")
st.markdown("Faça o upload de um PDF escaneado ou antigo para extrair o texto.")

uploaded_file = st.file_uploader("Escolha um arquivo PDF...", type="pdf")

if uploaded_file is not None:
    # Exibe uma mensagem de processamento enquanto a tarefa é executada
    with st.spinner("Processando o PDF... Isso pode levar alguns minutos dependendo do tamanho do arquivo."):
        extracted_text = ocr_pdf(uploaded_file)
    
    if extracted_text:
        st.success("Texto extraído com sucesso!")
        st.subheader("Texto Extraído:")
        st.text_area("Resultado", extracted_text, height=500)
        
        # Botão para baixar o texto extraído como um arquivo
        st.download_button(
            label="Baixar texto extraído",
            data=extracted_text,
            file_name="texto_do_pdf.txt",
            mime="text/plain"
        )
