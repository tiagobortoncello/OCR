import streamlit as st
import subprocess
import tempfile
import os
import shutil
import requests
import json

st.set_page_config(page_title="Processador de PDF com OCR", layout="centered")

# --- FUNÇÕES PARA A CORREÇÃO DE TEXTO COM GEMINI ---

def get_api_key():
    """
    Tenta obter a chave de API das variáveis de ambiente ou secrets do Streamlit.
    """
    api_key = os.environ.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY")
    return api_key

def correct_ocr_text(raw_text):
    """
    Chama a API da Gemini para corrigir erros de OCR, normalizar a ortografia arcaica
    e IGNORAR O CABEÇALHO.
    """
    api_key = get_api_key()
    
    apiUrl = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key if api_key else ''}"
    
    system_prompt = """
    Você é um corretor ortográfico e normalizador de texto brasileiro. 
    Sua tarefa é receber um texto bruto de um processo de OCR, que pode conter erros de detecção e ortografia arcaica (comum em documentos legais e antigos).

    Regras de correção, normalização e **REMOÇÃO**:
    - **Remova o cabeçalho do jornal ou documento, incluindo TÍTULO (Ex: "MINAS GERAES"), subtítulo, informações de ASSINATURA, VENDA AVULSA, data, número da edição, e quaisquer linhas divisórias.** O objetivo é extrair APENAS o corpo legal/noticioso do texto.
    - Corrija falhas de detecção do OCR (ex: 'Asy!o' para 'Asilo', '¢m' para 'em').
    - Normalize ortografias arcaicas como 'Geraes' para 'Gerais', 'Conceigao' para 'Conceição', 'Immaculada' para 'Imaculada', 'legaes' para 'legais', 'Asylo' para 'Asilo'.
    - **Após a correção e remoção, mantenha a separação de parágrafos, inserindo uma linha em branco entre eles.** Remova apenas quebras de linha desnecessárias dentro de um mesmo parágrafo e espaços múltiplos.
    - **Retorne APENAS o texto corrigido e com os parágrafos separados**, sem qualquer introdução, explicação ou formatação adicional (como markdown).
    """

    payload = {
        "contents": [{"parts": [{"text": raw_text}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
    }
    
    try:
        response = requests.post(apiUrl, 
                                 headers={'Content-Type': 'application/json'}, 
                                 data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        
        corrected_text = result.get("candidates", [])[0].get("content", {}).get("parts", [])[0].get("text", "")
        return corrected_text if corrected_text else raw_text

    except requests.exceptions.HTTPError as http_err:
        st.error(f"Erro HTTP ({http_err.response.status_code}) na correção via Gemini. Exibindo texto bruto.")
    except Exception as e:
        st.error(f"Erro inesperado durante a correção via Gemini: {e}. Exibindo texto bruto.")

    return raw_text

# --- CORPO PRINCIPAL DO APP ---

OCRMypdf_PATH = shutil.which("ocrmypdf")

if not OCRMypdf_PATH:
    st.error("""
        O executável **'ocrmypdf' não foi encontrado** no ambiente do Streamlit Cloud.
        Isso pode ser uma falha na instalação das dependências de sistema (`packages.txt`).
        
        **Ações recomendadas:**
        1. Confirme se o arquivo `packages.txt` contém apenas `ocrmypdf` e está na **raiz** do seu repositório.
        2. Force um **restart ou re-deploy** do seu aplicativo no Streamlit Cloud.
    """)
    st.stop()

st.title("Processador de PDF com OCR e Correção de IA")
st.markdown("Faça o upload de um PDF digitalizado. A IA irá processar o texto, **remover o cabeçalho** e formatar o corpo **mantendo a separação entre os parágrafos**.")

uploaded_file = st.file_uploader("Escolha um arquivo PDF...", type=["pdf"])

if uploaded_file is not None:
    st.info("Arquivo carregado com sucesso. Processando...")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as input_file:
        input_file.write(uploaded_file.read())
        input_filepath = input_file.name

    output_filepath = os.path.join(tempfile.gettempdir(), "output_ocr.pdf")

    try:
        command = [
            OCRMypdf_PATH,
            "--force-ocr",
            "--sidecar",
            "/tmp/output.txt",
            input_filepath,
            output_filepath
        ]
        
        process = subprocess.run(command, check=True, capture_output=True, text=True)
        
        st.success("Processo de OCR concluído!")

        if os.path.exists("/tmp/output.txt"):
            with open("/tmp/output.txt", "r") as f:
                sidecar_text_raw = f.read()
            
            st.markdown("---")
            st.subheader("🤖 Texto Extraído e Corrigido (IA)")
            
            with st.spinner("Removendo cabeçalho, corrigindo ortografia arcaica, erros de OCR e formatando o texto com parágrafos..."):
                sidecar_text_corrected = correct_ocr_text(sidecar_text_raw)

            st.text_area("Texto Corrigido (Gemini)", sidecar_text_corrected, height=400, key="corrected_text_final")
            
            st.download_button(
                label="⬇️ Baixar Texto Corrigido (.txt)",
                data=sidecar_text_corrected.encode('utf-8'),
                file_name="texto_corrigido_com_paragrafos.txt",
                mime="text/plain"
            )
            
            st.markdown("---")
            
            with open(output_filepath, "rb") as f:
                st.download_button(
                    label="📥 Baixar PDF Processado (Pesquisável)",
                    data=f.read(),
                    file_name="ocr_output.pdf",
                    mime="application/pdf"
                )

    except subprocess.CalledProcessError as e:
        st.error(f"Erro ao processar o PDF. Detalhes: {e.stderr}")
        st.code(f"Comando tentado: {' '.join(command)}")
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")
    finally:
        if os.path.exists(input_filepath):
            os.unlink(input_filepath)
        if os.path.exists(output_filepath):
            os.unlink(output_filepath)
        if os.path.exists("/tmp/output.txt"):
            os.unlink("/tmp/output.txt")
