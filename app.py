import streamlit as st
import subprocess
import tempfile
import os
import shutil
import requests
import json

# NOVO NOME AQUI
st.set_page_config(page_title="Conversor de PDF para texto (OCR)", layout="centered")

# --- FUNÇÕES PARA A CORREÇÃO DE TEXTO COM GEMINI ---

def get_api_key():
    """
    Tenta obter a chave de API das variáveis de ambiente ou secrets do Streamlit.
    """
    api_key = os.environ.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY")
    return api_key

def correct_ocr_text(raw_text):
    """
    Chama a API da Gemini para corrigir erros de OCR, normalizar a ortografia arcaica,
    IGNORAR O CABEÇALHO e **REFORMATAR EM MARKDOWN, INCLUINDO TABELAS**.
    """
    api_key = get_api_key()
    
    if not api_key:
        st.error("Chave de API do Gemini não encontrada. Verifique as variáveis de ambiente ou secrets.")
        return raw_text
    
    # Usando um modelo mais robusto para formatação de tabelas
    apiUrl = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    system_prompt = """
    Você é um corretor ortográfico e normalizador de texto brasileiro, especializado em documentos históricos.
    Sua tarefa é receber um texto bruto de um processo de OCR, corrigir erros e normalizar a ortografia arcaica (comum em documentos legais e antigos).

    **Você deve retornar o resultado INTEIRO no formato Markdown.**

    Regras de correção, normalização e formatação:
    - **Remoção de Cabeçalho:** Remova o cabeçalho do jornal ou documento, incluindo TÍTULO (Ex: "MINAS GERAES"), subtítulo, informações de ASSINATURA, VENDA AVULSA, data, número da edição e quaisquer linhas divisórias. O objetivo é extrair APENAS o corpo legal/noticioso do texto.
    - **Correção e Normalização:** Corrija falhas de detecção do OCR (ex: 'Asy!o' para 'Asilo') e normalize ortografias arcaicas ('Geraes' para 'Gerais', 'legaes' para 'legais').
    - **Tabelas:** Se o texto extraído contiver dados que formavam uma tabela no PDF, **RE-CRIE ESSA TABELA usando a sintaxe Markdown de tabelas** (cabeçalhos, separadores e linhas).
    - **Parágrafos:** Após a correção e remoção, mantenha a separação de parágrafos, inserindo uma linha em branco entre eles. Remova apenas quebras de linha desnecessárias dentro de um mesmo parágrafo e espaços múltiplos.
    - **Não crie ou deduza palavras que não estejam completas no texto.**
    - **Retorne APENAS o texto corrigido e formatado em Markdown**, sem qualquer introdução, explicação ou formatação adicional (como ```markdown```).
    """

    payload = {
        "contents": [{"parts": [{"text": raw_text}]}],
        "config": {
            "systemInstruction": system_prompt
        }
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
        st.error(f"Ocorreu um erro inesperado durante a correção via Gemini: {e}. Exibindo texto bruto.")

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

# NOVO TÍTULO AQUI
st.title("Conversor de PDF para texto (OCR)")
# A LINHA st.markdown("Faça o upload de um PDF digitalizado. A IA irá processar o texto, **remover o cabeçalho**, **manter a separação entre os parágrafos** e **não completar palavras incompletas**.") FOI REMOVIDA.

# NOVO AVISO AQUI
st.warning("⚠️ **AVISO IMPORTANTE:** Este aplicativo só deve ser utilizado para edições antigas do Jornal Minas Gerais. Versões atuais são pesadas e podem fazer o aplicativo parar de funcionar.")

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
            
            with st.spinner("Removendo cabeçalho, corrigindo ortografia arcaica, erros de OCR e formatando o texto em Markdown (incluindo tabelas)..."):
                sidecar_text_corrected = correct_ocr_text(sidecar_text_raw)

            # Exibição formatada em Streamlit
            st.info("O texto abaixo está formatado em Markdown. Tabelas e parágrafos foram reestruturados.")
            st.markdown(sidecar_text_corrected, unsafe_allow_html=False)
            
            st.markdown("---")
            st.subheader("Código Fonte (Markdown)")
            st.code(sidecar_text_corrected, language="markdown")
            
            # Botão de Download
            st.download_button(
                label="⬇️ Baixar Texto Corrigido (Formato Markdown .md)",
                data=sidecar_text_corrected.encode('utf-8'),
                file_name="texto_corrigido_formatado.md",
                mime="text/markdown"
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
