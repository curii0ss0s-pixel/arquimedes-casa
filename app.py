import streamlit as st
from google import genai
from google.genai import types
import json
import os
import re

# --- 1. CONFIGURACIÓN DEL CLIENTE ---
api_key = st.secrets["GEMINI_API_KEY"].strip().replace('"', '').replace("'", "")

@st.cache_resource
def get_client():
    return genai.Client(api_key=api_key)

client = get_client()

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

# Menú lateral
st.sidebar.header("⚙️ Configuración")
modelo_principal = st.sidebar.selectbox(
    "Modelo de IA:",
    ["gemini-3.8-flash", "gemini-1.5-flash"]
)
modelo_respaldo = "gemini-1.5-flash" if modelo_principal == "gemini-3.8-flash" else "gemini-3.8-flash"

# Mostrar lo que ha aprendido en la barra lateral
memoria_actual = cargar_memoria()
st.sidebar.subheader("🧠 Memoria de Arquímedes")
for regla in memoria_actual["reglas"]:
    st.sidebar.write(f"- {regla}")

# --- 4. LÓGICA DEL CHAT ---
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

# Mostrar historial
for msg in st.session_state.mensajes:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Instrucciones dinámicas (se actualizan cada vez que hablas)
reglas_aprendidas = "\n".join(memoria_actual["reglas"])

instrucciones = f"""
Eres Arquímedes, el director y arquitecto de una casa de bots.
Tu función es coordinar a otros bots para crear videos educativos.
El usuario (Botman) no sabe de programación, háblale en español sencillo.

REGLAS QUE HAS APRENDIDO:
{reglas_aprendidas}

INSTRUCCIÓN DE APRENDIZAJE:
Si Botman te da una orden permanente o te pide recordar algo para el futuro (ej. "A partir de ahora...", "Recuerda que..."), DEBES añadir al final de tu respuesta EXACTAMENTE este formato:
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
    
    try:
        with st.spinner(f"Arquímedes está procesando..."):
            try:
                response = client.models.generate_content(
                    model=modelo_principal,
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=instrucciones)
                )
            except Exception:
                response = client.models.generate_content(
                    model=modelo_respaldo,
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=instrucciones)
                )
            
            texto_respuesta = response.text
            
            # --- 5. DETECCIÓN DE APRENDIZAJE ---
            # Buscamos si Arquímedes usó la etiqueta [MEMORIA: ...]
            match = re.search(r"\[MEMORIA:\s*(.*?)\]", texto_respuesta)
            if match:
                nueva_regla = match.group(1)
                guardar_memoria(nueva_regla)
                # Le quitamos la etiqueta al texto para que se vea limpio
                texto_respuesta = re.sub(r"\[MEMORIA:\s*.*?\]", "", texto_respuesta).strip()
                st.toast(f"🧠 ¡Arquímedes ha aprendido: '{nueva_regla}'!")
            
            with st.chat_message("assistant"):
                st.markdown(texto_respuesta)
            st.session_state.mensajes.append({"role": "assistant", "content": texto_respuesta})
            
    except Exception as e:
        st.error(f"Ups, ambos modelos fallaron. Detalle: {e}")
