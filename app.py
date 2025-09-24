import streamlit as st
import easyocr
import fitz  # PyMuPDF
import numpy as np
import requests
import json

# Cache do EasyOCR para carregar o modelo uma vez
@st.cache_resource
def init_ocr_reader():
    return easyocr.Reader(['pt'], gpu=False, model_storage_directory='/tmp/easyocr')

# Inicializa o leitor OCR
reader = init_ocr_reader()

# Função para corrigir texto usando a API do Gemini
def correct_text_with_gemini(text, api_key):
    """
    Envia o texto extraído para a API do Gemini para correção.
    """
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        headers = {"Content-Type": "application/json"}
        prompt = (
            "Você é um especialista em correção de textos extraídos de OCR de jornais antigos em português, "
            "como os de Minas Gerais, organizados em colunas. Corrija o texto abaixo, consertando palavras mal interpretadas "
            "e mantendo o contexto original. O texto é lido coluna por coluna, de cima para baixo. "
            "Retorne apenas o texto corrigido, sem explicações, preservando a estrutura de colunas com marcações claras. "
            "Evite adicionar ou remover informações que não estejam no texto original.\n\n"
            f"Texto para corrigir:\n{text}"
        )
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2000}
        }
        
        response = requests.post(f"{url}?key={api_key}", headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        corrected_text = result["candidates"][0]["content"]["parts"][0]["text"]
        return corrected_text.strip()
    
    except Exception as e:
        st.warning(f"Erro ao corrigir o texto com Gemini: {e}")
        return text  # Retorna o texto original em caso de erro

def split_image_into_columns(img, num_columns=2):
    """
    Divide a imagem em colunas para OCR.
    """
    height, width = img.shape[:2]
    column_width = width // num_columns
    columns = []
    
    for i in range(num_columns):
        # Define as coordenadas da coluna
        x_start = i * column_width
        x_end = (i + 1) * column_width if i < num_columns - 1 else width
        column_img = img[:, x_start:x_end]
        columns.append(column_img)
    
    return columns

def ocr_pdf(uploaded_file):
    """
    Processa um PDF escaneado, extrai texto por colunas e retorna o texto organizado.
    """
    text_data = ""
    
    try:
        pdf_document = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    except Exception as e:
        st.error(f"Erro ao abrir o PDF: {e}")
        return ""

    # Limita o número de páginas
    max_pages = 5
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
            
            # Divide a imagem em colunas (assumindo 2 colunas, comum em jornais)
            columns = split_image_into_columns(img, num_columns=2)
            
            # Extrai texto de cada coluna
            page_text = ""
            for col_idx, column_img in enumerate(columns):
                results = reader.readtext(column_img, detail=0, contrast_ths=0.3, batch_size=1)
                column_text = "\n".join(results)
                page_text += f"\n--- Coluna {col_idx + 1} ---\n{column_text}\n"
                
                # Libera a memória da coluna
                column_img = None
            
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
st.markdown("Faça upload de um PDF escaneado com layout em colunas (máximo 5 MB, preferencialmente com boa qualidade).")

# Recupera a chave da API do secrets
api_key = st.secrets.get("GEMINI_API_KEY", "")

uploaded_file = st.file_uploader("Escolha um PDF...", type="pdf")

if uploaded_file is not None:
    if uploaded_file.size > 5 * 1024 * 1024:
        st.error("O arquivo é muito grande. Envie um PDF com menos de 5 MB.")
    else:
        with st.spinner("Processando o PDF... Pode levar alguns minutos."):
            extracted_text = ocr_pdf(uploaded_file)
        
        if extracted_text:
            st.success("Texto extraído com sucesso!")
            st.subheader("Texto Extraído (OCR):")
            st.text_area("Resultado do OCR", extracted_text, height=300)
            
            if api_key:
                with st.spinner("Corrigindo texto com Gemini..."):
                    corrected_text = correct_text_with_gemini(extracted_text, api_key)
                st.subheader("Texto Corrigido (Gemini):")
                st.text_area("Resultado Corrigido", corrected_text, height=300)
                
                st.download_button(
                    label="Baixar texto corrigido",
                    data=corrected_text,
                    file_name="texto_do_pdf_corrigido.txt",
                    mime="text/plain"
                )
            else:
                st.warning("Chave da API do Gemini não encontrada no secrets. Adicione 'GEMINI_API_KEY' no Streamlit Cloud.")
            
            st.download_button(
                label="Baixar texto extraído (OCR)",
                data=extracted_text,
                file_name="texto_do_pdf.txt",
                mime="text/plain"
            )
        else:
            st.warning("Nenhum texto foi extraído. Tente um PDF com maior nitidez ou fontes mais legíveis.")
