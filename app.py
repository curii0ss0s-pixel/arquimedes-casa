import streamlit as st
import os
from google import genai
from google.genai import types

# 1. Limpiamos la llave por si se colaron espacios o comillas extra
api_key = st.secrets["GEMINI_API_KEY"].strip().replace('"', '').replace("'", "")

# 2. Guardamos el cliente en caché para que no se cierre al recargar
@st.cache_resource
def get_client():
    return genai.Client(api_key=api_key)

client = get_client()

instrucciones = """
Eres Arquímedes, el director y arquitecto de una casa de bots.
Tu función es coordinar a otros bots para crear videos educativos (empezando por la historia de Tesla vs Edison).
El usuario (Botman) no sabe de programación, así que háblale en español sencillo, sé amable, estructurado y proactivo.
"""

st.title("🏛️ La Casa de Arquímedes")

# 3. Creamos un historial manual para tener control total
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

# Mostramos los mensajes anteriores en pantalla
for msg in st.session_state.mensajes:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. Entrada del usuario
if prompt := st.chat_input("Escríbele una orden a Arquímedes..."):
    # Mostrar el mensaje del usuario
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Guardar en el historial
    st.session_state.mensajes.append({"role": "user", "content": prompt})
    
    # 5. Construir el historial en el formato que pide la API de Google
    contents = []
    for m in st.session_state.mensajes:
        role = "user" if m["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))
    
    # 6. Llamar al modelo gemini-3.8-flash
    try:
        with st.spinner("Arquímedes está pensando..."):
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=instrucciones
                )
            )
            
            # Mostrar respuesta y guardar
            with st.chat_message("assistant"):
                st.markdown(response.text)
            st.session_state.mensajes.append({"role": "assistant", "content": response.text})
            
    except Exception as e:
        st.error(f"Ups, hubo un problema técnico. Detalle: {e}")
