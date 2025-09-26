import streamlit as st
import subprocess
import tempfile
import os
import shutil
import requests # NOVO: Necessário para a API da Gemini
import json     # NOVO: Necessário para a API da Gemini

st.set_page_config(page_title="Processador de PDF com OCR", layout="centered")

# --- FUNÇÕES PARA A CORREÇÃO DE TEXTO COM GEMINI ---

def get_api_key():
    """
    Tenta obter a chave de API das variáveis de ambiente ou secrets do Streamlit.
    """
    # No ambiente Canvas, a chave é fornecida automaticamente no fetch se for string vazia.
    api_key = os.environ.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY")
    return api_key

def correct_ocr_text(raw_text):
    """
    Chama a API da Gemini para corrigir erros de OCR e normalizar a ortografia arcaica.
    """
    api_key = get_api_key()
    
    # O Streamlit Canvas injeta a chave automaticamente se for uma string vazia (API Key "").
    apiUrl = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key if api_key else ''}"
    
    system_prompt = """
    Você é um corretor ortográfico e normalizador de texto brasileiro. 
    Sua tarefa é receber um texto bruto de um processo de OCR, que pode conter erros de detecção e ortografia arcaica (comum em documentos legais e antigos).

    Regras de correção e normalização (use o Português moderno do Brasil):
    - Corrija falhas de detecção do OCR (ex: 'Asy!o' para 'Asilo', '¢m' para 'em').
    - Normalize ortografias arcaicas como 'Geraes' para 'Gerais', 'Conceigao' para 'Conceição', 'Immaculada' para 'Imaculada', 'sancciono' para 'sanciono', 'uti-lidade' para 'utilidade', 'legaes' para 'legais', 'Asylo' para 'Asilo', 'Collegio' para 'Colégio', 'Gymnasio' para 'Ginásio'.
    - **APÓS a correção, remova todas as quebras de linha (newlines), retornos de carro e múltiplos espaços, unindo todo o texto em um único parágrafo contínuo.**
    - **Retorne APENAS o texto corrigido e contínuo**, sem qualquer introdução, explicação ou formatação adicional (como markdown).
    """

    payload = {
        "contents": [{"parts": [{"text": raw_text}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
    }
    
    try:
        response = requests.post(apiUrl, 
                                 headers={'Content-Type': 'application/json'}, 
                                 data=json.dumps(payload))
        response.raise_for_status() # Lança exceção para erros HTTP (4xx ou 5xx)
        result = response.json()
        
        corrected_text = result.get("candidates", [])[0].get("content", {}).get("parts", [])[0].get("text", "")
        return corrected_text if corrected_text else raw_text

    except requests.exceptions.HTTPError as http_err:
        st.error(f"Erro HTTP ({http_err.response.status_code}) na correção via Gemini. Exibindo texto bruto.")
    except Exception as e:
        st.error(f"Erro inesperado durante a correção via Gemini: {e}. Exibindo texto bruto.")

    return raw_text # Fallback: retorna o texto original em caso de falha


# --- CORPO PRINCIPAL DO APP ---

# --- TRECHO DE CÓDIGO PARA ROBUSTEZ ---
# Usamos shutil.which() para encontrar o caminho completo do executável.
OCRMypdf_PATH = shutil.which("ocrmypdf")

if not OCRMypdf_PATH:
    # Se o caminho não for encontrado, o erro é mais claro.
    st.error("""
        O executável **'ocrmypdf' não foi encontrado** no ambiente do Streamlit Cloud.
        Isso pode ser uma falha na instalação das dependências de sistema (`packages.txt`).
        
        **Ações recomendadas:**
        1. Confirme se o arquivo `packages.txt` contém apenas `ocrmypdf` e está na **raiz** do seu repositório.
        2. Force um **restart ou re-deploy** do seu aplicativo no Streamlit Cloud.
    """)
    st.stop()
# ---------------------------------------------

# --- UI elements ---
st.title("Processador de PDF com OCR e Correção de IA")
st.markdown("Faça o upload de um PDF digitalizado para que o OCRmyPDF o processe. O texto extraído será corrigido pela IA e formatado em **linha contínua**.")

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
            OCRMypdf_PATH,
            "--force-ocr",
            "--sidecar",
            "/tmp/output.txt",
            input_filepath,
            output_filepath
        ]
        
        # Executar o comando ocrmypdf
        process = subprocess.run(command, check=True, capture_output=True, text=True)
        
        st.success("Processo de OCR concluído!")

        # Exibir e Corrigir o texto extraído
        if os.path.exists("/tmp/output.txt"):
            with open("/tmp/output.txt", "r") as f:
                sidecar_text_raw = f.read()
            
            # --- Tentar correção com Gemini ---
            st.markdown("---")
            st.subheader("🤖 Texto Extraído e Corrigido (IA)")
            
            with st.spinner("Corrigindo ortografia arcaica, erros de OCR e formatando o texto em linha única com Gemini..."):
                sidecar_text_corrected = correct_ocr_text(sidecar_text_raw)

            # Exibe o texto corrigido no corpo principal em formato contínuo
            st.text_area("Texto Contínuo Corrigido (Gemini)", sidecar_text_corrected, height=200, key="corrected_text_final")
            
            # Adiciona botão de download para o texto
            st.download_button(
                label="⬇️ Baixar Texto Corrigido (.txt)",
                data=sidecar_text_corrected.encode('utf-8'),
                file_name="texto_corrigido.txt",
                mime="text/plain"
            )
            
            st.markdown("---")
            
            # Baixar o arquivo de saída (PDF)
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
        # Limpar os arquivos temporários, independentemente do resultado
        if os.path.exists(input_filepath):
            os.unlink(input_filepath)
        if os.path.exists(output_filepath):
            os.unlink(output_filepath)
        if os.path.exists("/tmp/output.txt"):
            os.unlink("/tmp/output.txt")
