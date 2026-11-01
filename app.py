import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI
import json
import os
import re

# --- 1. CONFIGURACIÓN DE CLIENTES ---
def get_secret(key):
    return st.secrets.get(key, "").strip().replace('"', '').replace("'", "")

@st.cache_resource
def get_google_client():
    key = get_secret("GEMINI_API_KEY")
    return genai.Client(api_key=key) if key else None

@st.cache_resource
def get_openai_client(base_url, key_name):
    key = get_secret(key_name)
    return OpenAI(base_url=base_url, api_key=key) if key else None

google_client = get_google_client()
openrouter_client = get_openai_client("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY")
mistral_client = get_openai_client("https://api.mistral.ai/v1", "MISTRAL_API_KEY")
groq_client = get_openai_client("https://api.groq.com/openai/v1", "GROQ_API_KEY")
hf_client = get_openai_client("https://api-inference.huggingface.co/v1", "HUGGINGFACE_API_KEY")

# --- 2. SISTEMA DE MEMORIA ---
MEMORY_FILE = "memoria_arquimedes.json"

def cargar_memoria():
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump({"reglas": ["Hablar en español sencillo.", "Enfocarse en Tesla vs Edison."]}, f, ensure_ascii=False, indent=4)
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_memoria(nueva_regla):
    memoria = cargar_memoria()
    if nueva_regla not in memoria["reglas"]:
        memoria["reglas"].append(nueva_regla)
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memoria, f, ensure_ascii=False, indent=4)

# --- 3. INTERFAZ GRÁFICA ESTILO CHATGPT ---
st.set_page_config(page_title="Arquímedes", layout="wide")
st.title("🏛️ La Casa de Arquímedes")

# --- SIDEBAR: MÚLTIPLES CHATS Y SELECTOR DE IA ---
with st.sidebar:
    st.header("💬 Tus Chats")
    
    # Inicializar diccionario de chats
    if "mis_chats" not in st.session_state:
        st.session_state.mis_chats = {"Chat Principal": []}
        st.session_state.chat_actual = "Chat Principal"

    # Botón para crear nuevo chat
    if st.button("➕ Nuevo Chat"):
        nuevo_nombre = f"Chat {len(st.session_state.mis_chats) + 1}"
        st.session_state.mis_chats[nuevo_nombre] = []
        st.session_state.chat_actual = nuevo_nombre
        st.rerun()

    # Selector de chat
    chat_seleccionado = st.selectbox("Selecciona un chat:", list(st.session_state.mis_chats.keys()), index=list(st.session_state.mis_chats.keys()).index(st.session_state.chat_actual))
    if chat_seleccionado != st.session_state.chat_actual:
        st.session_state.chat_actual = chat_seleccionado
        st.rerun()

    st.divider()

    st.header("⚙️ Configuración de IA")
    proveedor = st.selectbox(
        "Elige el cerebro de Arquímedes:",
        ["Google (Gemini)", "OpenRouter (Llama 3)", "Mistral AI", "Groq", "Hugging Face"]
    )
    
    st.subheader("🧠 Memoria")
    memoria_actual = cargar_memoria()
    for regla in memoria_actual["reglas"]:
        st.write(f"- {regla}")

# --- ARCHIVOS Y DESCARGAS ---
with st.expander("📂 Subir archivos o imágenes (Opcional)"):
    archivo_subido = st.file_uploader("Sube un archivo de texto o imagen", type=["txt", "png", "jpg", "jpeg"])

# --- MOSTRAR HISTORIAL DEL CHAT ACTUAL ---
mensajes_actuales = st.session_state.mis_chats[st.session_state.chat_actual]

for i, msg in enumerate(mensajes_actuales):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Botón de descarga para respuestas del asistente
        if msg["role"] == "assistant":
            st.download_button(
                label="⬇️ Descargar respuesta",
                data=msg["content"],
                file_name=f"respuesta_arquimedes_{i}.txt",
                mime="text/plain",
                key=f"descarga_{i}"
            )

# --- LÓGICA DEL CHAT ---
instrucciones = f"Eres Arquímedes. Habla claro y en español.\nREGLAS:\n" + "\n".join(memoria_actual["reglas"]) + "\nSi debes recordar algo, usa: [MEMORIA: <regla>]"

if prompt := st.chat_input("Escríbele una orden a Arquímedes..."):
    # Procesar archivo si existe
    texto_archivo = ""
    if archivo_subido:
        if archivo_subido.type == "text/plain":
            texto_archivo = archivo_subido.read().decode("utf-8")
            prompt = f"[El usuario adjuntó un archivo con este texto: {texto_archivo}]\n\n{prompt}"
    
    # Mostrar mensaje del usuario
    with st.chat_message("user"):
        st.markdown(prompt)
    
    mensajes_actuales.append({"role": "user", "content": prompt})
    
    texto_respuesta = ""
    error_real = ""

    with st.spinner(f"Arquímedes está pensando con {proveedor}..."):
        try:
            # 1. GOOGLE GEMINI
            if proveedor == "Google (Gemini)" and google_client:
                contents = []
                for m in mensajes_actuales:
                    role = "user" if m["role"] == "user" else "model"
                    contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))
                try:
                    res = google_client.models.generate_content(model="gemini-3.8-flash", contents=contents, config=types.GenerateContentConfig(system_instruction=instrucciones))
                    texto_respuesta = res.text
                except Exception:
                    res = google_client.models.generate_content(model="gemini-1.5-flash", contents=contents, config=types.GenerateContentConfig(system_instruction=instrucciones))
                    texto_respuesta = res.text
            
            # 2. OPENROUTER
            elif proveedor == "OpenRouter (Llama 3)" and openrouter_client:
                msgs = [{"role": "system", "content": instrucciones}] + [{"role": "assistant" if m["role"]=="model" else m["role"], "content": m["content"]} for m in mensajes_actuales]
                res = openrouter_client.chat.completions.create(model="meta-llama/llama-3-8b-instruct:free", messages=msgs)
                texto_respuesta = res.choices[0].message.content

            # 3. MISTRAL
            elif proveedor == "Mistral AI" and mistral_client:
                msgs = [{"role": "system", "content": instrucciones}] + [{"role": "assistant" if m["role"]=="model" else m["role"], "content": m["content"]} for m in mensajes_actuales]
                res = mistral_client.chat.completions.create(model="open-mistral-7b", messages=msgs)
                texto_respuesta = res.choices[0].message.content

            # 4. GROQ
            elif proveedor == "Groq" and groq_client:
                msgs = [{"role": "system", "content": instrucciones}] + [{"role": "assistant" if m["role"]=="model" else m["role"], "content": m["content"]} for m in mensajes_actuales]
                res = groq_client.chat.completions.create(model="llama-3.1-8b-instant", messages=msgs)
                texto_respuesta = res.choices[0].message.content

            # 5. HUGGING FACE
            elif proveedor == "Hugging Face" and hf_client:
                msgs = [{"role": "system", "content": instrucciones}] + [{"role": "assistant" if m["role"]=="model" else m["role"], "content": m["content"]} for m in mensajes_actuales]
                res = hf_client.chat.completions.create(model="meta-llama/Meta-Llama-3-8B-Instruct", messages=msgs)
                texto_respuesta = res.choices[0].message.content

            else:
                error_real = "No se seleccionó un modelo válido o falta la llave API en los Secretos."

        except Exception as e:
            error_real = str(e)

    # --- MOSTRAR RESPUESTA O ERROR REAL ---
    if texto_respuesta:
        # Procesar memoria
        match = re.search(r"\[MEMORIA:\s*(.*?)\]", texto_respuesta)
        if match:
            guardar_memoria(match.group(1))
            texto_respuesta = re.sub(r"\[MEMORIA:\s*.*?\]", "", texto_respuesta).strip()
            st.toast("🧠 ¡Arquímedes ha aprendido algo nuevo!")
        
        with st.chat_message("assistant"):
            st.markdown(texto_respuesta)
        mensajes_actuales.append({"role": "assistant", "content": texto_respuesta})
        st.rerun()
    else:
        # Si falló, mostramos exactamente qué llave falló
        st.error(f"❌ Error con {proveedor}. Detalle: {error_real}")
        st.info("💡 Revisa que la llave de este proveedor esté bien escrita en los Secrets de Streamlit y que hayas reiniciado la app.")
