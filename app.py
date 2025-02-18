import streamlit as st
import requests
import pandas as pd
import sqlite3
from datetime import datetime

# ✅ Configurar la página
st.set_page_config(page_title="Google Knowledge Graph Explorer", page_icon="🔍", layout="wide")

# ✅ Obtener las credenciales desde secrets
API_KEY = st.secrets["GOOGLE_KG_API_KEY"]
ADMIN_PASS = st.secrets["ADMIN_PASS"]

# ✅ Verificar si hay API Key
if not API_KEY:
    st.error("⚠️ No se encontró la API Key. Asegúrate de definir GOOGLE_KG_API_KEY en los secretos.")
    st.stop()

# ✅ Inicializar la base de datos SQLite
def initialize_db():
    conn = sqlite3.connect("search_logs.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS searches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT NOT NULL,
        language TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

initialize_db()

# ✅ Guardar búsqueda en la base de datos
def save_search(query, language):
    conn = sqlite3.connect("search_logs.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO searches (query, language) VALUES (?, ?)", (query, language))
    conn.commit()
    conn.close()

# ✅ Obtener historial de búsquedas
def get_search_history():
    conn = sqlite3.connect("search_logs.db")
    df = pd.read_sql_query("SELECT * FROM searches ORDER BY timestamp DESC", conn)
    conn.close()
    return df

# ✅ Obtener historial de usuario
def get_user_search_history():
    conn = sqlite3.connect("search_logs.db")
    df = pd.read_sql_query("SELECT query, language, timestamp FROM searches ORDER BY timestamp DESC LIMIT 10", conn)
    conn.close()
    return df

# ✅ Verificar si el usuario es administrador
query_params = st.query_params
admin_key = query_params.get("admin", [""])[0]

# 🔹 Si el usuario es administrador, mostrar el panel de administración
if admin_key == ADMIN_PASS:
    st.title("📊 Panel de Administrador")
    
    df_logs = get_search_history()
    if df_logs.empty:
        st.warning("⚠ No hay registros en la base de datos.")
    else:
        st.write("## 📜 Historial de Búsquedas")
        st.dataframe(df_logs)

# 🔹 Si el usuario no es administrador, mostrar la aplicación normal
else:
    st.title("🔍 Google Knowledge Graph Explorer")
    st.write("🔎 Ingresa una palabra clave para buscar información estructurada sobre entidades, conceptos y personas en la base de conocimiento de Google.")

    # 🔍 Sección de búsqueda
    query = st.text_input("Ingresar Keyword")

    language_options = {
        "Español": "es",
        "Inglés": "en",
        "Francés": "fr",
        "Alemán": "de",
        "Italiano": "it"
    }
    selected_languages = [code for lang, code in language_options.items() if st.checkbox(f"Buscar en {lang}")]

    if st.button("🔍 Buscar") and query:
        with st.spinner("Buscando entidades..."):
            results = []
            for lang_code in selected_languages:
                url = "https://kgsearch.googleapis.com/v1/entities:search"
                params = {"query": query, "limit": 50, "key": API_KEY, "languages": lang_code}
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
                            "Idioma": lang_code
                        })

                    # 🔹 Guardar búsqueda en la base de datos
                    save_search(query, lang_code)

            if results:
                st.write("### Resultados")
                st.dataframe(pd.DataFrame(results))
            else:
                st.warning("No se encontraron entidades relacionadas.")

    # 📖 Historial de Búsquedas del Usuario
    st.write("## 📖 Tu Historial de Búsquedas")

    user_logs = get_user_search_history()
    if user_logs.empty:
        st.warning("⚠ No tienes búsquedas recientes.")
    else:
        st.dataframe(user_logs)
