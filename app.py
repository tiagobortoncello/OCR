import streamlit as st
import subprocess
import tempfile
import os
import shutil
import requests
import json

# Define as configurações básicas da página
st.set_page_config(page_title="Conversor de PDF para ODT (Formatado)", layout="centered")

# --- FUNÇÕES PARA A CORREÇÃO DE TEXTO COM GEMINI ---

def get_api_key():
    """
    Tenta obter a chave de API das variáveis de ambiente ou secrets do Streamlit.
    """
    # Preferência para a chave 'GEMINI_API_KEY' nos secrets do Streamlit
    api_key = os.environ.get("GOOGLE_API_KEY") or st.secrets.get("GEMINI_API_KEY")
    return api_key

def correct_ocr_text(raw_text):
    """
    Chama a API da Gemini para corrigir erros de OCR, normalizar a ortografia arcaica,
    IGNORAR O CABEÇALHO e **REFORMATAR EM MARKDOWN, INCLUINDO TABELAS**, sendo fiel aos dados.
    """
    api_key = get_api_key()
    
    if not api_key:
        st.error("Chave de API do Gemini não encontrada. Verifique as variáveis de ambiente ou secrets.")
        return raw_text
    
    # Modelo gemini-2.5-flash
    apiUrl = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    # PROMPT ATUALIZADO PARA PROIBIR INFERÊNCIA DE DADOS
    system_prompt = """
    Você é um corretor ortográfico e normalizador de texto brasileiro, especializado em documentos históricos.
    Sua tarefa é receber um texto bruto de um processo de OCR, corrigir erros e normalizar a ortografia arcaica (comum em documentos legais e antigos).

    **Você deve retornar o resultado INTEIRO no formato Markdown.**

    Regras de correção, normalização e formatação:
    - **Proibição de Inferência de Dados:** É proibido **INVENTAR, DEDUZIR, RESUMIR ou ADICIONAR** quaisquer palavras, números, títulos ou linhas de rodapé (como "Total", "Subtotal", "Geral") que não estejam explicitamente no texto bruto do OCR. **Mantenha-se 100% fiel aos dados.**
    - **Remoção de Cabeçalho:** Remova o cabeçalho do jornal ou documento, incluindo TÍTULO (Ex: "MINAS GERAES"), subtítulo, informações de ASSINATURA, VENDA AVULSA, data, número da edição e quaisquer linhas divisórias. O objetivo é extrair APENAS o corpo legal/noticioso do texto.
    - **Correção e Normalização:** Corrija falhas de detecção do OCR (ex: 'Asy!o' para 'Asilo') e normalize ortografias arcaicas ('Geraes' para 'Gerais', 'legaes' para 'legais').
    - **Tabelas:** Se o texto extraído contiver dados que formavam uma tabela no PDF, **RE-CRIE ESSA TABELA usando a sintaxe Markdown de tabelas** (cabeçalhos, separadores e linhas). Use cabeçalhos de coluna APENAS se estiverem visíveis no texto bruto.
    - **Parágrafos:** Após a correção e remoção, mantenha a separação de parágrafos, inserindo uma linha em branco entre eles. Remova apenas quebras de linha desnecessárias dentro de um mesmo parágrafo e espaços múltiplos.
    - **Não crie ou deduza palavras que não estejam completas no texto.**
    - **Retorne APENAS o texto corrigido e formatado em Markdown**, sem qualquer introdução, explicação ou formatação adicional (como ```markdown```).
    """

    # Payload Corrigido (usando system_instruction)
    payload = {
        "contents": [{"parts": [{"text": raw_text}]}],
        "system_instruction": {"parts": [{"text": system_prompt}]}, 
    }
    
    try:
        response = requests.post(apiUrl, 
                                 headers={'Content-Type': 'application/json'}, 
                                 data=json.dumps(payload))
        
        if response.status_code == 400:
            st.error(f"Erro detalhado da API (400): {response.text}. Verifique o tamanho do PDF.")
            return raw_text

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
PANDOC_PATH = shutil.which("pandoc") 

if not OCRMypdf_PATH or not PANDOC_PATH:
    st.error("""
        O executável **'ocrmypdf' ou 'pandoc' não foi encontrado**.
        Verifique se o arquivo `packages.txt` (na raiz do repositório) contém as linhas `ocrmypdf` e `pandoc`.
        Pode ser necessário forçar um re-deploy ou restart do aplicativo.
    """)
    st.stop()

# Título do App
st.title("Conversor de PDF para ODT (LibreOffice)")

# Aviso
st.warning("⚠️ **AVISO IMPORTANTE:** Este aplicativo só deve ser utilizado para edições antigas do Jornal Minas Gerais. Versões atuais são pesadas e podem fazer o aplicativo parar de funcionar devido aos limites de recursos.")

uploaded_file = st.file_uploader("Escolha um arquivo PDF...", type=["pdf"])

if uploaded_file is not None:
    st.info("Arquivo carregado com sucesso. Processando...")
    
    # Define caminhos temporários
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as input_file:
        input_file.write(uploaded_file.read())
        input_filepath = input_file.name

    output_ocr_filepath = os.path.join(tempfile.gettempdir(), "output_ocr.pdf")
    markdown_filepath = os.path.join(tempfile.gettempdir(), "texto_temporario.md") 
    odt_filepath = os.path.join(tempfile.gettempdir(), "documento_final.odt") 

    try:
        # 1. Execução do OCRMypdf (Extração de texto bruto)
        with st.spinner("1/3: Extraindo texto bruto do PDF com OCR..."):
            command_ocr = [
                OCRMypdf_PATH,
                "--force-ocr",
                "--sidecar",
                markdown_filepath, 
                input_filepath,
                output_ocr_filepath
            ]
            
            subprocess.run(command_ocr, check=True, capture_output=True, text=True)
            st.success("Extração de texto concluída.")

        if os.path.exists(markdown_filepath):
            with open(markdown_filepath, "r") as f:
                sidecar_text_raw = f.read()
            
            # 2. Execução do Gemini (Correção e formatação Markdown)
            with st.spinner("2/3: Corrigindo ortografia arcaica, removendo cabeçalhos e formatando tabelas via IA..."):
                sidecar_text_corrected = correct_ocr_text(sidecar_text_raw)
            
            # Sobrescreve o arquivo .md com o texto corrigido pelo Gemini
            with open(markdown_filepath, "w", encoding='utf-8') as f:
                f.write(sidecar_text_corrected)

            # 3. Execução do Pandoc (Conversão de MD para ODT)
            with st.spinner("3/3: Convertendo Markdown para arquivo ODT do LibreOffice..."):
                command_pandoc = [
                    PANDOC_PATH,
                    "--standalone", 
                    "-s",
                    markdown_filepath,
                    "-o",
                    odt_filepath
                ]
                subprocess.run(command_pandoc, check=True, capture_output=True, text=True)
                st.success("Conversão para ODT concluída! Seu documento está pronto para download.")

            st.markdown("---")
            st.subheader("✅ Processo Finalizado com Sucesso")
            st.info("O download abaixo contém o texto corrigido, com ortografia normalizada e tabelas reestruturadas, pronto para edição no LibreOffice Writer.")
            
            # Download do ODT formatado (tabelas inclusas, ideal para LibreOffice)
            with open(odt_filepath, "rb") as f:
                st.download_button(
                    label="⬇️ Baixar Documento Formatado (.odt)",
                    data=f.read(),
                    file_name="documento_final_formatado.odt",
                    mime="application/vnd.oasis.opendocument.text"
                )
            
            st.markdown("---")


    except subprocess.CalledProcessError as e:
        # Captura erros tanto do OCRMypdf quanto do Pandoc
        st.error(f"Erro ao processar o arquivo (OCR ou Pandoc). Detalhes: {e.stderr}")
        st.code(f"Comando tentado: {' '.join(e.cmd)}")
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")
    finally:
        # Limpeza de todos os arquivos temporários, fundamental no Streamlit Cloud
        for filepath in [input_filepath, output_ocr_filepath, markdown_filepath, odt_filepath]:
            if os.path.exists(filepath):
                try:
                    # Verifica se o arquivo existe antes de tentar apagar
                    if filepath and os.path.exists(filepath):
                        os.unlink(filepath)
                except Exception:
                    pass
