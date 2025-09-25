import streamlit as st
from pdf2image import convert_from_bytes
from PIL import Image
import io
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import markdown2
from transformers import AutoProcessor, AutoModelForVision2Seq
import torch
import base64

# Inicializa modelo Hugging Face
@st.cache_resource
def load_model():
    processor = AutoProcessor.from_pretrained("Qwen/Qwen2.5-VL-3B-Instruct")
    model = AutoModelForVision2Seq.from_pretrained("Qwen/Qwen2.5-VL-3B-Instruct")
    model.eval()
    if torch.cuda.is_available():
        model.to("cuda")
    return processor, model

processor, model = load_model()

# Custom CSS
st.markdown("""
<style>
.main { background-color: #f8f9fa; padding: 30px; }
.stButton>button { background-color: #28a745; color: white; border-radius: 8px; padding: 8px 16px; font-size: 16px; margin-top: 10px; }
.stTextArea>label { font-weight: bold; color: #1a3c34; font-size: 16px; }
.stImage>img { border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 15px; }
.sidebar .sidebar-content { background-color: #ffffff; padding: 20px; border-right: 1px solid #e0e0e0; }
h1, h2, h3 { color: #1a3c34; font-family: 'Helvetica Neue', Arial, sans-serif; margin-bottom: 20px; }
.markdown-preview { background-color: #ffffff; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px; min-height: 400px; font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 16px; }
</style>
""", unsafe_allow_html=True)

st.title("📄 Qwen2.5-VL OCR on PDFs (Hugging Face)")

# Upload de PDFs
uploaded_files = st.file_uploader("Upload PDFs (max 200MB por arquivo)", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    st.session_state.processed = False
    st.session_state.file_results = {}

def process_page(file_name, page, page_idx):
    """Processa uma página usando Qwen2.5-VL via Hugging Face"""
    page_start_time = time.time()
    
    # Converte a página em imagem
    buf = io.BytesIO()
    page.save(buf, format="PNG")
    img_bytes = buf.getvalue()
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")
    
    image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    
    # Prepara entrada para o modelo
    inputs = processor(images=image, return_tensors="pt")
    if torch.cuda.is_available():
        inputs = {k:v.to("cuda") for k,v in inputs.items()}
    
    # Gera resposta
    with torch.no_grad():
        outputs = model.generate(**inputs)
        text = processor.decode(outputs[0], skip_special_tokens=True)
    
    page_time = time.time() - page_start_time
    return file_name, page_idx, text, page_time, img_b64, page

if uploaded_files and not st.session_state.get("processed", False):
    st.info("Processando PDFs em paralelo...")
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
    MAX_WORKERS = 2  # você pode ajustar conforme GPU/CPU

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
