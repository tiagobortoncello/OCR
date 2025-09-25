import streamlit as st
import pdfplumber

st.title("📄 Extrator de Texto de PDF (sem OCR)")
st.write("Faça upload de um PDF com texto (não escaneado) para extrair seu conteúdo.")

uploaded_file = st.file_uploader("Escolha um arquivo PDF", type="pdf")

if uploaded_file is not None:
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            all_text = ""
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    all_text += f"\n\n--- Página {i + 1} ---\n\n{text}"
                else:
                    all_text += f"\n\n--- Página {i + 1} ---\n\n(Nenhuma texto detectado nesta página)"
        
        st.text_area("Texto extraído", all_text, height=600)
        
        # Opcional: botão para baixar o texto
        st.download_button(
            label="📥 Baixar texto extraído",
            data=all_text,
            file_name="texto_extraido.txt",
            mime="text/plain"
        )
        
    except Exception as e:
        st.error(f"Erro ao processar o PDF: {e}")
else:
    st.info("👆 Por favor, faça upload de um arquivo PDF.")
