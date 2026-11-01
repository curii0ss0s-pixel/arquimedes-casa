import streamlit as st
from google import genai
from google.genai import types

# 1. ESTA ES LA MAGIA: Guardamos el cliente en caché para que no se cierre
@st.cache_resource
def get_client():
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

client = get_client()

instrucciones = """
Eres Arquímedes, el director y arquitecto de una casa de bots.
Tu función es coordinar a otros bots para crear videos educativos (empezando por la historia de Tesla vs Edison).
El usuario (Botman) no sabe de programación, así que háblale en español sencillo, sé amable, estructurado y proactivo.
"""

# 2. Inicializamos el chat usando el modelo vigente
if "chat" not in st.session_state:
    st.session_state.chat = client.chats.create(
        model="gemini-1.5-flash", 
        config=types.GenerateContentConfig(
            system_instruction=instrucciones
        )
    )

st.title("🏛️ La Casa de Arquímedes")

# Mostrar historial
for message in st.session_state.chat.get_history():
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# Entrada del usuario
if prompt := st.chat_input("Escríbele una orden a Arquímedes..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    response = st.session_state.chat.send_message(prompt)
    
    with st.chat_message("assistant"):
        st.markdown(response.text)
