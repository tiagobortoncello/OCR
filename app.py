import streamlit as st
from pdf2image import convert_from_bytes
from PIL import Image
import io
import base64
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import markdown2
import requests

# --- CONFIGURAÇÃO HUGGING FACE API ---
HF_API_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-VL-3B-Instruct-AWQ"
HF_API_KEY = st.secrets.get("HF_API_KEY")  # coloque sua chave no Streamlit Secrets

headers = {"Authorization": f"Bearer {HF_API_KEY}"}

# Função para chamar o modelo via API
def query_hf_api(image_bytes):
    data = {
        "inputs": [
            {
                "type": "image_bytes",
                "data": image_bytes.decode("latin1")  # necessário para enviar bytes via JSON
            },
            {
                "type": "text",
                "text": "Please extract all text from this image."
            }
        ]
    }
    response = requests.post(HF_API_URL, headers=headers, json=data, timeout=60)
    if response.status_code == 200:
        # A API retorna texto como string
        result = response.json()
        # Depende do formato da resposta, ajustamos se necessário
        if isinstance(result, list) and "generated_text" in result[0]:
            return result[0]["generated_text"]
        elif isinstance(result, dict) and "error" in result:
            return f"API Error: {result['error']}"
        else:
            return str(result)
    else:
        return f"HTTP {response.status_code}: {response.text}"

# --- STREAMLIT UI ---
st.title("📄 Qwen2.5-VL OCR on PDFs (Hugging Face API)")

uploaded_files = st.file_uploader("Upload PDFs (max 200MB per arquivo)", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    st.session_state.processed = False
    st.session_state.file_results = {}

def process_page(file_name, page, page_idx):
    """Processa uma página via Hugging Face API"""
    page_start_time = time.time()
    
    buf = io.BytesIO()
    page.save(buf, format="PNG")
    img_bytes = buf.getvalue()
    
    text = query_hf_api(img_bytes)
    
    page_time = time.time() - page_start_time
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")
    
    return file_name, page_idx, text, page_time, img_b64, page

# Processamento paralelo
if uploaded_files and not st.session_state.get("processed", False):
    st.info("Processando PDFs via Hugging Face API...")
    progress_bar = st.progress(0)
    progress_text = st.empty()

    all_pages = []
    total_pages = 0
    st.session_state.file_results = {}
    
    for uploaded_file in uploaded_files:
        file_name = uploaded_file.name
        pages = convert_from_bytes(uploaded_file.read(), dpi=150)
        all_pages.extend([(file_name, page, i+1) for i, page in enumerate(pages)])
        total_pages += len(pages)
        st.session_state.file_results[file_name] = []

    processed_pages = 0
    MAX_WORKERS = 2  # ajuste conforme necessidade

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_page, f, p, i): (f, i) for f, p, i in all_pages}
        for future in as_completed(futures):
            file_name, page_idx = futures[future]
            try:
                file_name, page_idx, text, page_time, img_b64, page = future.result()
                processed_pages += 1
                progress_bar.progress(processed_pages / total_pages)
                progress_text.text(f"Processado {processed_pages}/{total_pages} páginas")
                st.session_state.file_results[file_name].append({
                    "page": page_idx,
                    "text": text,
                    "page_time": page_time,
                    "img_b64": img_b64,
                    "image": page
                })
            except Exception as e:
                st.error(f"Falha no arquivo {file_name} - página {page_idx}: {str(e)}")

    # Ordena páginas
    for file_name in st.session_state.file_results:
        st.session_state.file_results[file_name].sort(key=lambda x: x["page"])

    st.session_state.processed = True
    progress_text.text("Processamento concluído!")

# Exibir resultados
if st.session_state.get("file_results"):
    selected_file = st.selectbox("Selecione um arquivo para visualizar", list(st.session_state.file_results.keys()))
    if selected_file:
        col1, col2 = st.columns([2, 3])
        with col1:
            for result in st.session_state.file_results[selected_file]:
                st.subheader(f"Página {result['page']}")
                st.image(result["image"], use_container_width=True)
                st.text_area(f"OCR - Página {result['page']}", result["text"], height=150)
        
        with col2:
            markdown_content = f"# OCR Results for {selected_file}\n\n"
            for result in st.session_state.file_results[selected_file]:
                markdown_content += f"## Página {result['page']}\n\n"
                markdown_content += f"**Tempo de processamento**: {result['page_time']:.2f} segundos\n\n"
                markdown_content += f"```text\n{result['text']}\n```\n\n"
            html_content = markdown2.markdown(markdown_content, extras=["fenced-code-blocks", "tables"])
            st.markdown(f'<div class="markdown-preview">{html_content}</div>', unsafe_allow_html=True)
            st.download_button("Download Markdown", data=markdown_content, file_name=f"ocr_{selected_file}.md", mime="text/markdown")
