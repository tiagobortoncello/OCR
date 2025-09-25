import streamlit as st
import pdfplumber

st.title("📄 Extrator de Texto de PDF (com layout preservado)")
st.write("Upload de PDF com texto (mesmo antigo ou com colunas).")

uploaded_file = st.file_uploader("Escolha um arquivo PDF", type="pdf")

if uploaded_file is not None:
    try:
        all_text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for i, page in enumerate(pdf.pages):
                # Estratégia 1: tentar extrair com layout preservado
                text = page.extract_text(layout=True, x_tolerance=2, y_tolerance=2)
                if not text or len(text.strip()) < 50:  # Se falhar, tentar modo raw
                    text = page.extract_text(x_tolerance=1, y_tolerance=1)
                if not text or len(text.strip()) < 20:
                    text = "(Texto não detectado ou muito curto nesta página)"
                all_text += f"\n\n--- Página {i + 1} ---\n\n{text}"
        
        st.text_area("Texto extraído", all_text, height=600)
        st.download_button(
            label="📥 Baixar texto extraído",
            data=all_text,
            file_name="texto_extraido.txt",
            mime="text/plain"
        )
        
    except Exception as e:
        st.error(f"Erro ao processar o PDF: {e}")
        st.exception(e)  # útil para debug no Streamlit Cloud
else:
    st.info("👆 Faça upload do PDF do jornal.")
