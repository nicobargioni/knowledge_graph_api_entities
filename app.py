import streamlit as st
import requests
import pandas as pd
import sqlite3
from datetime import datetime

# 🔹 Configuración inicial
st.set_page_config(page_title="Google Knowledge Graph Explorer", initial_sidebar_state="collapsed")

# 🔹 Ocultar sidebar completamente
st.markdown("""
    <style>
        section[data-testid="stSidebar"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

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
is_admin = query_params.get("admin") == "nbseo"  # 🔴 Usa ?admin=nbseo en la URL

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

api_key = st.text_input("API Key de Google Knowledge Graph", type="password")
query = st.text_input("Consulta de búsqueda")

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
