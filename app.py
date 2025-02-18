import streamlit as st
import requests
import pandas as pd
import os
import json
import webbrowser

# 🔹 Configuración de Google OAuth
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")  # Usa la URL pública de tu aplicación

# 🔹 Ocultar el menú lateral por completo
st.markdown(
    """
    <style>
        [data-testid="stSidebarNav"] {
            display: none !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ✅ Validación de configuración
if not CLIENT_ID or not CLIENT_SECRET:
    st.error("⚠️ CLIENT_ID o CLIENT_SECRET no están configurados.")
    st.stop()

# 🔹 Función para generar URL de autenticación con Google
def login_with_google():
    return f"https://accounts.google.com/o/oauth2/auth?" \
           f"client_id={CLIENT_ID}" \
           f"&redirect_uri={REDIRECT_URI}" \
           f"&response_type=code" \
           f"&scope=openid email profile" \
           f"&access_type=offline" \
           f"&prompt=consent"

# 🔹 Interfaz de autenticación
st.title("🔑 Autenticación con Google")

if "user" not in st.session_state:
    if st.button("🔑 Iniciar sesión con Google"):
        auth_url = login_with_google()
        webbrowser.open_new(auth_url)  # 🔹 Abre la URL de autenticación en una nueva ventana
        st.stop()
else:
    st.success(f"✅ Bienvenido {st.session_state['user']['name']}")
    if st.session_state["user"]["picture"]:
        st.image(st.session_state["user"]["picture"], width=100)

# 🔹 Verificar si se recibió un código de autenticación en la URL
query_params = st.query_params
auth_code = query_params.get("code")

if auth_code:
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": auth_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    response = requests.post(token_url, data=token_data)
    token_info = response.json()

    if "access_token" in token_info:
        access_token = token_info["access_token"]

        # 🔹 Obtener datos del usuario
        user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        user_response = requests.get(user_info_url, headers=headers)
        user_info = user_response.json()

        # ✅ Guardar datos en session_state
        st.session_state["user"] = {
            "name": user_info.get("name", "Usuario desconocido"),
            "email": user_info.get("email", "Correo no disponible"),
            "picture": user_info.get("picture"),
        }

        # 🔹 Cerrar la ventana de autenticación
        st.markdown('<script>window.close();</script>', unsafe_allow_html=True)
        st.rerun()
    else:
        st.error("No se pudo obtener el Access Token. Intenta de nuevo.")

# ✅ **Interfaz de Usuario**
st.title("Google Knowledge Graph Explorer")
st.write("🔍 Ingresa una keyword para buscar en Google Knowledge Graph.")

# 🔹 Obtener API Key desde variables de entorno
api_key = os.getenv("GOOGLE_KG_API_KEY")

if not api_key:
    st.error("⚠️ Error: No se encontró una API Key configurada.")

query = st.text_input("Ingresar Keyword")

# 🔹 Checkboxes para idiomas
language_options = {
    "Español": "es",
    "Inglés": "en",
    "Francés": "fr",
    "Alemán": "de",
    "Italiano": "it"
}

selected_languages = [lang for lang, code in language_options.items() if st.checkbox(f"Buscar en {lang}")]

results = []

# ✅ **Botón de búsqueda**
if st.button("🔍 Buscar"):
    if not api_key or not query:
        st.warning("Por favor, ingrese una API Key y una consulta de búsqueda.")
    else:
        with st.spinner("Buscando entidades..."):
            for lang, code in language_options.items():
                if lang in selected_languages:
                    url = "https://kgsearch.googleapis.com/v1/entities:search"
                    params = {"query": query, "limit": 50, "key": api_key, "languages": code}
                    response = requests.get(url, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        for item in data.get("itemListElement", []):
                            entity = item.get("result", {})
                            results.append({
                                "Nombre": entity.get("name", "N/A"),
                                "Tipo": ", ".join(entity.get("@type", [])),
                                "Descripción": entity.get("description", "N/A"),
                                "Score": item.get("resultScore", 0),
                                "Idioma": lang
                            })

            if results:
                df = pd.DataFrame(results)
                st.write("### Resultados")
                st.dataframe(df)
            else:
                st.warning("No se encontraron entidades relacionadas.")
