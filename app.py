import streamlit as st
from PIL import Image
from io import BytesIO
import fitz  # PyMuPDF
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import gc

# --- OCR (mantido igual) ---
def get_ocr_reader():
    import easyocr
    return easyocr.Reader(['pt', 'en'], gpu=False, verbose=False)

def ocr_with_columns(pil_img, num_columns=2):
    reader = get_ocr_reader()
    width, height = pil_img.size
    col_width = width // num_columns
    texts = []
    for i in range(num_columns):
        left = i * col_width
        right = width if i == num_columns - 1 else (i + 1) * col_width
        col = pil_img.crop((left, 0, right, height))
        buf = BytesIO()
        col.save(buf, format='PNG')
        results = reader.readtext(buf.getvalue(), detail=0, paragraph=True)
        txt = " ".join(results).strip()
        if txt:
            texts.append(txt)
    return " ".join(texts)

def process_image(pil_img):
    if pil_img.width > 1800:
        ratio = 1800 / pil_img.width
        pil_img = pil_img.resize((1800, int(pil_img.height * ratio)), Image.LANCZOS)
    return ocr_with_columns(pil_img, num_columns=2)

def process_pdf(pdf_bytes):
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        all_text = []
        for i in range(min(doc.page_count, 2)):  # só 2 páginas para economizar RAM
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=100)
            img = Image.open(BytesIO(pix.tobytes("png")))
            with st.spinner(f"Página {i+1}..."):
                text = process_image(img)
                if text.strip():
                    all_text.append(f"[Pág {i+1}]\n{text}")
        doc.close()
        return "\n\n".join(all_text)
    except Exception as e:
        st.error("Erro ao processar PDF.")
        return ""

# --- Qwen2-0.5B (rodando localmente) ---
@st.cache_resource
def load_qwen_model():
    with st.spinner("Carregando Qwen2-0.5B... (pode levar 1-2 minutos)"):
        model_name = "Qwen/Qwen2-0.5B-Instruct"
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,  # usa menos memória
            device_map="auto",
            trust_remote_code=True
        )
        return model, tokenizer

def run_qwen(prompt):
    model, tokenizer = load_qwen_model()
    messages = [
        {"role": "system", "content": "Você é um assistente útil."},
        {"role": "user", "content": prompt}
    ]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    model_inputs = tokenizer([text], return_tensors="pt").to("cpu")
    
    with torch.no_grad():
        generated_ids = model.generate(
            model_inputs.input_ids,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.6,
            pad_token_id=tokenizer.eos_token_id
        )
    
    generated_text = generated_ids[0][len(model_inputs.input_ids[0]):]
    response = tokenizer.decode(generated_text, skip_special_tokens=True)
    return response

# --- Interface ---
st.set_page_config(page_title="OCR + Qwen Local", layout="centered")
st.title("🗞️ OCR + Qwen2-0.5B (100% Hugging Face)")
st.caption("Modelo rodando localmente — sem API externa, sem erro 403.")

uploaded = st.file_uploader("Envie imagem ou PDF", type=["png", "jpg", "jpeg", "pdf"])

if uploaded:
    if uploaded.type == "application/pdf":
        with st.spinner("Processando PDF..."):
            text = process_pdf(uploaded.read())
    else:
        img = Image.open(uploaded)
        with st.spinner("Lendo por colunas..."):
            text = process_image(img)

    if text and text.strip():
        st.text_area("Texto extraído", text[:1500] + "..." if len(text) > 1500 else text, height=150)
        prompt = st.text_input(
            "Instrução para o Qwen:",
            "Corrija erros de OCR de jornal antigo. Mantenha grafia da época ('annos'), mas corrija 'Fonscea' → 'Fonseca', etc."
        )
        if st.button("Corrigir com Qwen (local)"):
            full_prompt = f"{prompt}\n\nTexto:\n{text[:1000]}"
            with st.spinner("Qwen processando... (pode demorar 20-40s)"):
                try:
                    resposta = run_qwen(full_prompt)
                    st.subheader("Resultado:")
                    st.write(resposta)
                except Exception as e:
                    st.error(f"Erro ao rodar Qwen: {str(e)}")
                    st.info("Tente reduzir o tamanho do texto ou recarregar a página.")
    else:
        st.warning("Nenhum texto encontrado.")
