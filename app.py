import streamlit as st
import requests
import pandas as pd
import sqlite3
from datetime import datetime
import os
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery

# 🔹 Configuración inicial
st.set_page_config(page_title="Google Knowledge Graph Explorer", initial_sidebar_state="collapsed")

# 🔹 Ocultar sidebar completamente
st.markdown("""
    <style>
        section[data-testid="stSidebar"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)


# 🔹 Configuración de Google OAuth 2.0
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "https://knowledge-graph-api-entities.streamlit.app/"  # Reemplázalo con la URL de tu app

SCOPES = ["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"]

# 🔹 Función para iniciar sesión con Google
def google_login():
    flow = google_auth_oauthlib.flow.Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=SCOPES
    )
    flow.redirect_uri = REDIRECT_URI

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true"
    )

    return authorization_url

# 🔹 Interfaz de usuario en Streamlit
st.title("🔑 Iniciar sesión con Google")

if "user" not in st.session_state:
    if st.button("Iniciar sesión con Google"):
        auth_url = google_login()
        st.write(f"[Haz clic aquí para autenticarte]({auth_url})")
else:
    st.success(f"✅ Bienvenido {st.session_state['user']['name']}")
    st.image(st.session_state["user"]["picture"], width=100)

def get_user_ip():
    """ Obtiene la IP pública del usuario """
    if "user_ip" not in st.session_state:
        try:
            response = requests.get("https://api64.ipify.org?format=json")
            st.session_state["user_ip"] = response.json().get("ip", "Desconocida")
        except:
            st.session_state["user_ip"] = "No disponible"
    
    return st.session_state["user_ip"]

def initialize_db():
    """ Crea la base de datos y la tabla si no existen """
    conn = sqlite3.connect("search_logs.db")
    cursor = conn.cursor()

    # Crear la tabla si no existe
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS searches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT NOT NULL,
        language TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        ip_address TEXT
    )
    """)
    conn.commit()
    conn.close()

def log_search(query, language):
    """ Registra las búsquedas en SQLite """
    ip_address = get_user_ip()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("search_logs.db")
    cursor = conn.cursor()

    cursor.execute("INSERT INTO searches (query, language, ip_address, timestamp) VALUES (?, ?, ?, ?)",
                   (query, language, ip_address, timestamp))
    
    conn.commit()
    conn.close()

def get_search_history():
    """ Obtiene el historial de búsquedas desde la base de datos """
    conn = sqlite3.connect("search_logs.db")
    df = pd.read_sql_query("SELECT id, query, language, ip_address, timestamp FROM searches ORDER BY timestamp DESC", conn)
    conn.close()
    return df

def get_knowledge_graph_entities(api_key, query, language, lang_label, limit=50):
    """ Consulta Google Knowledge Graph API """
    url = "https://kgsearch.googleapis.com/v1/entities:search"
    params = {
        "query": query,
        "limit": limit,
        "key": api_key,
        "languages": language
    }
    
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return []
    
    data = response.json()
    entities = []
    
    for item in data.get("itemListElement", []):
        entity = item.get("result", {})
        entities.append({
            "Nombre": entity.get("name", "N/A"),
            "Tipo": ", ".join(entity.get("@type", [])),
            "Descripción": entity.get("description", "N/A"),
            "Score": item.get("resultScore", 0),
            "Idioma": lang_label
        })
    
    return entities

# ✅ **Asegurar que la base de datos esté inicializada**
initialize_db()

# ✅ **Acceso al Panel de Administrador**
query_params = st.query_params
is_admin = query_params.get("admin") == os.getenv("ADMIN_PASS")

if is_admin:
    st.title("📊 Panel de Administrador")
    df_logs = get_search_history()

    if df_logs.empty:
        st.warning("⚠️ No hay registros en la base de datos.")
    else:
        st.write("### Historial de Búsquedas")
        st.dataframe(df_logs)

        # 📊 Mostrar búsquedas por IP
        st.write("### 🔍 Búsquedas por IP")
        df_ip_counts = df_logs.groupby("ip_address").size().reset_index(name="Total Búsquedas")
        st.dataframe(df_ip_counts)

    st.stop()  # Evita que se muestre la app normal

# ✅ **Interfaz de Usuario**
st.title("Google Knowledge Graph Explorer")

# 📝 Agregar descripción debajo del título
st.write(
    "🔍 Esta aplicación permite determinar si una keyword está reconocida como entidad en el Knowledge Graph de Google.\n\n"
    "Ingresa una keyword y selecciona los idiomas en los que deseas realizar la búsqueda.\n\n"
    "📖 **Las entidades relacionadas** son conceptos, personas, lugares u objetos "
    "que Google reconoce y asocia en su base de datos semántica. Este enfoque ayuda "
    "a comprender mejor el contexto de las búsquedas en lugar de depender solo de palabras clave.\n\n"
    "🛠️ **Puedes utilizar esta información en datos estructurados** como Schema.org "
    "para mejorar el SEO de tu sitio web, ayudando a los motores de búsqueda a "
    "interpretar con mayor precisión el contenido y las relaciones entre diferentes temas."
)


# Obtener API Key desde las variables de entorno
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
                    results.extend(get_knowledge_graph_entities(api_key, query, code, lang))
                    log_search(query, lang)
            
            if results:
                df = pd.DataFrame(results)
                st.write("### Resultados")
                st.dataframe(df)
            else:
                st.warning("No se encontraron entidades relacionadas.")
