import streamlit as st
import requests
import pandas as pd
import sqlite3
import os
from datetime import datetime
import streamlit as st


# ✅ Configurar la página para ocultar el sidebar
st.set_page_config(layout="wide")

API_KEY = st.secrets["GOOGLE_KG_API_KEY"]
ADMIN_PASS = st.secrets["ADMIN_PASS"]


if not API_KEY:
    st.error("⚠️ No se encontró la API Key. Asegúrate de definir GOOGLE_KG_API_KEY como variable de entorno.")
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

# ✅ Pestañas de la aplicación
query_params = st.query_params
is_admin = query_params.get("admin", [""])[0]

# 🔹 Página principal (Explorador)
def explorador():
    st.title("🔍 Google Knowledge Graph Explorer")
    st.write("🔎 Ingresa una palabra clave para buscar información estructurada sobre entidades, conceptos y personas en la base de conocimiento de Google.")

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

# 🔹 Panel de administración (solo accesible con clave)
def admin():
    st.title("📊 Panel de Administrador")
    st.write("Aquí puedes ver todas las búsquedas realizadas por los usuarios.")

    conn = sqlite3.connect("search_logs.db")
    cursor = conn.cursor()

    cursor.execute("SELECT query, language, timestamp FROM searches ORDER BY timestamp DESC")
    searches = cursor.fetchall()

    if searches:
        df = pd.DataFrame(searches, columns=["Query", "Idioma", "Fecha"])
        st.dataframe(df)
    else:
        st.warning("No hay búsquedas registradas.")

    conn.close()

# 🔹 Control de acceso: Admin o Explorador
if is_admin == ADMIN_PASS:
    admin()
else:
    explorador()