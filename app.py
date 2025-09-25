import streamlit as st
import subprocess
import tempfile
import os

st.set_page_config(page_title="Processador de PDF com OCR", layout="centered")

# --- UI elements ---
st.title("Processador de PDF com OCR")
st.markdown("Faça o upload de um PDF digitalizado para que o OCRmyPDF o processe e gere um novo PDF com texto pesquisável.")

uploaded_file = st.file_uploader("Escolha um arquivo PDF...", type=["pdf"])

if uploaded_file is not None:
    st.info("Arquivo carregado com sucesso. Processando...")
    
    # Criar arquivos temporários para a entrada e saída
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as input_file:
        input_file.write(uploaded_file.read())
        input_filepath = input_file.name

    output_filepath = os.path.join(tempfile.gettempdir(), "output_ocr.pdf")

    try:
        # Comando para rodar o ocrmypdf
        # O argumento '--force-ocr' garante que o OCR seja executado mesmo em PDFs que já contenham texto
        command = [
            "ocrmypdf",
            "--force-ocr",
            "--sidecar",
            "/tmp/output.txt",
            input_filepath,
            output_filepath
        ]
        
        # Executar o comando ocrmypdf
        process = subprocess.run(command, check=True, capture_output=True, text=True)
        
        st.success("Processo de OCR concluído!")
        st.code(f"Saída do OCRmyPDF:\n{process.stdout}")

        # Baixar o arquivo de saída
        with open(output_filepath, "rb") as f:
            st.download_button(
                label="📥 Baixar PDF Processado",
                data=f.read(),
                file_name="ocr_output.pdf",
                mime="application/pdf"
            )

        # Exibir a barra lateral com o texto extraído (se disponível)
        if os.path.exists("/tmp/output.txt"):
            with open("/tmp/output.txt", "r") as f:
                sidecar_text = f.read()
            st.sidebar.subheader("Texto Extraído (Sidebar)")
            st.sidebar.text_area("Texto do PDF", sidecar_text, height=500)

    except subprocess.CalledProcessError as e:
        st.error(f"Erro ao processar o PDF. Detalhes: {e.stderr}")
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")
    finally:
        # Limpar os arquivos temporários, independentemente do resultado
        if os.path.exists(input_filepath):
            os.unlink(input_filepath)
        if os.path.exists(output_filepath):
            os.unlink(output_filepath)
        if os.path.exists("/tmp/output.txt"):
            os.unlink("/tmp/output.txt")
