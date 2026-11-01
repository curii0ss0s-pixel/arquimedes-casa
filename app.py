import streamlit as st
from google import genai
from google.genai import types

# Configurar el cliente con la llave de los secretos
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

instrucciones = """
Eres Arquímedes, el director y arquitecto de una casa de bots.
Tu función es coordinar a otros bots para crear videos educativos (empezando por la historia de Tesla vs Edison).
El usuario (Botman) no sabe de programación, así que háblale en español sencillo, sé amable, estructurado y proactivo.
"""

# Inicializar el modelo y el historial del chat en la sesión
if "chat" not in st.session_state:
    st.session_state.chat = client.chats.create(
        model="gemini-3.8-flash", # Modelo actual y estable
        config=types.GenerateContentConfig(
            system_instruction=instrucciones
        )
    )

st.title("🏛️ La Casa de Arquímedes")

# Mostrar el historial de la conversación
for message in st.session_state.chat.get_history():
    # La estructura del historial en el nuevo SDK es diferente
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        # Los mensajes pueden tener varias partes, mostramos la primera de texto
        st.markdown(message.parts[0].text)

# Entrada del usuario
if prompt := st.chat_input("Escríbele una orden a Arquímedes..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    response = st.session_state.chat.send_message(prompt)
    
    with st.chat_message("assistant"):
        st.markdown(response.text)
