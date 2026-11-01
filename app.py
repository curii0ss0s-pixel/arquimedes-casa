import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI
import json
import os
import re

# --- 1. CONFIGURACIÓN DE CLIENTES ---
# Limpiamos las llaves
api_key_google = st.secrets["GEMINI_API_KEY"].strip().replace('"', '').replace("'", "")
api_key_openrouter = st.secrets["OPENROUTER_API_KEY"].strip().replace('"', '').replace("'", "")

@st.cache_resource
def get_google_client():
    return genai.Client(api_key=api_key_google)

@st.cache_resource
def get_openrouter_client():
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key_openrouter)

google_client = get_google_client()
openrouter_client = get_openrouter_client()

# --- 2. SISTEMA DE MEMORIA (APRENDIZAJE) ---
MEMORY_FILE = "memoria_arquimedes.json"

def cargar_memoria():
    if not os.path.exists(MEMORY_FILE):
        memoria_inicial = {
            "reglas": [
                "Hablar en español sencillo.",
                "Coordinar la creación de videos educativos.",
                "Enfocarse en la historia de Tesla vs Edison."
            ]
        }
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memoria_inicial, f, ensure_ascii=False, indent=4)
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_memoria(nueva_regla):
    memoria = cargar_memoria()
    if nueva_regla not in memoria["reglas"]:
        memoria["reglas"].append(nueva_regla)
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memoria, f, ensure_ascii=False, indent=4)

# --- 3. INTERFAZ GRÁFICA ---
st.title("🏛️ La Casa de Arquímedes")

st.sidebar.header("⚙️ Configuración")
modelo_principal = st.sidebar.selectbox(
    "Modelo de IA Principal:",
    ["gemini-3.8-flash", "gemini-1.5-flash"]
)
modelo_respaldo = "gemini-1.5-flash" if modelo_principal == "gemini-3.8-flash" else "gemini-3.8-flash"

memoria_actual = cargar_memoria()
st.sidebar.subheader("🧠 Memoria de Arquímedes")
for regla in memoria_actual["reglas"]:
    st.sidebar.write(f"- {regla}")

# --- 4. LÓGICA DEL CHAT ---
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

for msg in st.session_state.mensajes:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

reglas_aprendidas = "\n".join(memoria_actual["reglas"])

instrucciones = f"""
Eres Arquímedes, el director y arquitecto de una casa de bots.
Tu función es coordinar a otros bots para crear videos educativos.
El usuario (Botman) no sabe de programación, háblale en español sencillo.

REGLAS QUE HAS APRENDIDO:
{reglas_aprendidas}

INSTRUCCIÓN DE APRENDIZAJE:
Si Botman te da una orden permanente o te pide recordar algo para el futuro, DEBES añadir al final de tu respuesta EXACTAMENTE este formato:
[MEMORIA: <aquí va la regla a recordar>]
"""

if prompt := st.chat_input("Escríbele una orden a Arquímedes..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    st.session_state.mensajes.append({"role": "user", "content": prompt})
    
    contents = []
    for m in st.session_state.mensajes:
        role = "user" if m["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))
    
    texto_respuesta = ""
    
    # --- SISTEMA DE TRIPLE RESPALDO ---
    try:
        with st.spinner(f"Arquímedes está pensando (usando {modelo_principal})..."):
            try:
                # Intento 1: Modelo principal de Google
                response = google_client.models.generate_content(
                    model=modelo_principal,
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=instrucciones)
                )
                texto_respuesta = response.text
            except Exception:
                # Intento 2: Modelo de respaldo de Google
                st.info(f"El modelo {modelo_principal} falló. Saltando a {modelo_respaldo}...")
                response = google_client.models.generate_content(
                    model=modelo_respaldo,
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=instrucciones)
                )
                texto_respuesta = response.text

    except Exception:
        # Intento 3: Si Google falla por completo, usamos OpenRouter (Llama 3)
        st.warning("Los servidores de Google están caídos. Saltando al Plan C (OpenRouter - Llama 3)...")
        try:
            # Adaptamos el historial al formato de OpenRouter
            mensajes_openrouter = [{"role": "system", "content": instrucciones}]
            for m in st.session_state.mensajes:
                role_or = "assistant" if m["role"] == "model" else m["role"]
                mensajes_openrouter.append({"role": role_or, "content": m["content"]})
            
            response_or = openrouter_client.chat.completions.create(
                model="meta-llama/llama-3-8b-instruct:free", # Modelo gratuito de Meta
                messages=mensajes_openrouter
            )
            texto_respuesta = response_or.choices[0].message.content
        except Exception as e:
            st.error(f"Todos los modelos fallaron, incluso los externos. Detalle: {e}")
            texto_respuesta = "Lo siento, Botman. Todos mis cerebros están desconectados en este momento."

    # --- PROCESAMIENTO DE RESPUESTA Y MEMORIA ---
    if texto_respuesta:
        match = re.search(r"\[MEMORIA:\s*(.*?)\]", texto_respuesta)
        if match:
            nueva_regla = match.group(1)
            guardar_memoria(nueva_regla)
            texto_respuesta = re.sub(r"\[MEMORIA:\s*.*?\]", "", texto_respuesta).strip()
            st.toast(f"🧠 ¡Arquímedes ha aprendido: '{nueva_regla}'!")
        
        with st.chat_message("assistant"):
            st.markdown(texto_respuesta)
        st.session_state.mensajes.append({"role": "assistant", "content": texto_respuesta})
