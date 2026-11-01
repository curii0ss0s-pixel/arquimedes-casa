import streamlit as st
import google.generativeai as genai
import os

# Configurar la IA (la llave se leerá de los secretos de Streamlit)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

instrucciones = """
Eres Arquímedes, el director y arquitecto de una casa de bots.
Tu función es coordinar a otros bots para crear videos educativos (empezando por la historia de Tesla vs Edison).
El usuario (Botman) no sabe de programación, así que háblale en español sencillo, sé amable, estructurado y proactivo.
"""

# Inicializar el modelo y el historial del chat
if "model" not in st.session_state:
    st.session_state.model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=instrucciones)
    st.session_state.chat = st.session_state.model.start_chat(history=[])

st.title("🏛️ La Casa de Arquímedes")

# Mostrar historial
for message in st.session_state.chat.history:
    with st.chat_message(message.role):
        st.markdown(message.parts[0].text)

# Entrada del usuario
if prompt := st.chat_input("Escríbele una orden a Arquímedes..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    response = st.session_state.chat.send_message(prompt)
    
    with st.chat_message("assistant"):
        st.markdown(response.text)
