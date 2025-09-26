import streamlit as st
import subprocess
import tempfile
import os
import shutil # Importação adicionada

st.set_page_config(page_title="Processador de PDF com OCR", layout="centered")

# --- NOVO TRECHO DE CÓDIGO PARA ROBUSTEZ ---
# Usamos shutil.which() para encontrar o caminho completo do executável.
OCRMypdf_PATH = shutil.which("ocrmypdf")

if not OCRMypdf_PATH:
    # Se o caminho não for encontrado, o erro é mais claro.
    st.error("""
        O executável **'ocrmypdf' não foi encontrado** no ambiente do Streamlit Cloud.
        Isso pode ser uma falha temporária na instalação das dependências de sistema.
        
        **Ações recomendadas:**
        1. Confirme se o arquivo `packages.txt` contém apenas `ocrmypdf`.
        2. Force um **restart ou re-deploy** do seu aplicativo no Streamlit Cloud para forçar uma nova instalação.
    """)
    st.stop()
# ---------------------------------------------

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
        # Comando para rodar o ocrmypdf, usando o caminho COMPLETO para maior segurança
        command = [
            OCRMypdf_PATH, # Agora usamos a variável com o caminho completo
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
        st.code(f"Comando tentado: {' '.join(command)}")
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
