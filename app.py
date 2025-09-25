import streamlit as st
import pdfplumber

st.title("📄 Extrator de PDFs Antigos (ex: jornais de 1927)")
st.write("Funciona mesmo com PDFs com texto mal posicionado.")

uploaded_file = st.file_uploader("Escolha um PDF", type="pdf")

if uploaded_file is not None:
    try:
        full_text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for i, page in enumerate(pdf.pages):
                # Método 1: extrair com layout
                text = page.extract_text(layout=True, x_tolerance=3, y_tolerance=3)
                
                # Método 2: se falhar, extrair todos os chars (útil para texto 'escondido')
                if not text or len(text.strip()) < 50:
                    chars = page.chars
                    if chars:
                        # Ordenar por posição (top, x0) para simular leitura
                        sorted_chars = sorted(chars, key=lambda c: (c["top"], c["x0"]))
                        text = "".join(c["text"] for c in sorted_chars)
                    else:
                        text = "(Nenhum caractere detectado nesta página)"
                
                full_text += f"\n\n--- Página {i + 1} ---\n\n{text}"
        
        st.text_area("Texto extraído", full_text, height=600)
        st.download_button("📥 Baixar texto", full_text, "texto.txt", "text/plain")
        
    except Exception as e:
        st.error(f"Erro: {e}")
        st.exception(e)
else:
    st.info("👆 Faça upload do seu PDF (ex: Minas_Gerais_1927-09-25.pdf)")
