import os
import streamlit as st
import sqlite3
import pandas as pd
import requests
import json
import base64
from client import RestClient  # ✅ Importar el cliente de DataForSEO

# ✅ Configurar la página
st.set_page_config(page_title="Google Knowledge Graph Explorer", page_icon="🔍", layout="wide")

# ✅ Obtener claves API desde Streamlit Secrets
ADMIN_PASS = st.secrets.get("ADMIN_PASS", "")
DATAFORSEO_USERNAME = st.secrets.get("DATAFORSEO_USERNAME", "")
DATAFORSEO_PASSWORD = st.secrets.get("DATAFORSEO_PASSWORD", "")
GOOGLE_KG_API_KEY = st.secrets.get("GOOGLE_KG_API_KEY", "")

# ✅ Cargar Location Codes (países)
file_path = "/mnt/data/locations_serp_google_2024_11_05.csv"
df_locations = pd.read_csv(file_path)
df_countries = df_locations[df_locations["location_type"] == "Country"]
country_location_codes = dict(zip(df_countries["location_name"], df_countries["location_code"]))

# ✅ Definir idiomas disponibles
language_options = {
    "Español": "es",
    "Inglés": "en",
    "Francés": "fr",
    "Portugués": "pt",
    "Italiano": "it"
}

# ✅ Capturar parámetros de la URL
query_params = st.query_params.to_dict()
admin_key = query_params.get("admin", [""])[0] if "admin" in query_params else ""
related_key = query_params.get("related", [""])[0] if "related" in query_params else ""

# ✅ Función para inicializar la base de datos
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

# ✅ Asegurar que la base de datos exista
initialize_db()

# ✅ Función para registrar búsquedas en la base de datos
def save_search(query, language):
    try:
        conn = sqlite3.connect("search_logs.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO searches (query, language) VALUES (?, ?)", (query, language))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"❌ Error al guardar la búsqueda: {e}")

# ✅ Función para obtener TODAS las búsquedas (solo para admin)
def get_all_search_history():
    try:
        conn = sqlite3.connect("search_logs.db")
        df = pd.read_sql_query("SELECT * FROM searches ORDER BY timestamp DESC LIMIT 50", conn)
        conn.close()
        return df if not df.empty else pd.DataFrame(columns=["query", "language", "timestamp"])
    except Exception as e:
        st.error(f"❌ Error al acceder a la base de datos: {e}")
        return pd.DataFrame(columns=["query", "language", "timestamp"])

# ✅ Función para obtener "People Also Search For" de DataForSEO
def get_people_also_search_for(keyword, location_code, language_code):
    """Consulta a la API de DataForSEO para obtener 'People Also Search For' con país e idioma personalizados."""
    try:
        if not DATAFORSEO_USERNAME or not DATAFORSEO_PASSWORD:
            st.error("❌ No se encontraron credenciales de DataForSEO.")
            return []

        # 🔹 Configurar cliente de DataForSEO
        client = RestClient(DATAFORSEO_USERNAME, DATAFORSEO_PASSWORD)

        # 🔹 Parámetros de la consulta
        post_data = [{
            "keyword": keyword,
            "location_code": location_code,
            "language_code": language_code,
            "device": "desktop"
        }]

        # 🔹 Hacer la solicitud
        response = client.post("/v3/serp/google/organic/live/advanced", post_data)

        # 🔹 Manejo de errores
        if response["status_code"] != 20000:
            st.error(f"❌ Error en la API: {response['status_code']} - {response['status_message']}")
            return []

        # 🔹 Extraer datos
        related_searches = []
        tasks = response.get("tasks", [])
        if tasks:
            results = tasks[0].get("result", [])
            for result in results:
                items = result.get("items", [])
                for item in items:
                    if item.get("type") == "people_also_search" and "items" in item:
                        related_searches.extend(item["items"])

        return related_searches

    except Exception as e:
        st.error(f"❌ Error en la solicitud: {e}")
        return []

# ✅ Bloque principal del script
if __name__ == "__main__":
    # 🔹 Panel de Administrador si accedes con `?admin=nbseo`
    if admin_key == ADMIN_PASS:
        st.title("🔐 Panel de Administrador")

        df_logs = get_all_search_history()
        if df_logs.empty:
            st.warning("⚠ No hay registros en la base de datos.")
        else:
            st.write("## 📜 Historial de Todas las Búsquedas")
            st.dataframe(df_logs)

        st.stop()

    # 🔹 Si accedes con `?related=1`, mostrar "People Also Search For"
    elif related_key == "1":
        st.title("🔍 People Also Search For")

        # 🔹 Selector de país
        country = st.selectbox("Selecciona un país", list(country_location_codes.keys()), index=0)
        location_code = country_location_codes[country]  # Obtener el código del país seleccionado

        # 🔹 Selector de idioma
        language = st.selectbox("Selecciona un idioma", list(language_options.keys()), index=0)
        language_code = language_options[language]  # Obtener el código del idioma seleccionado

        # 🔹 Campo para la keyword
        keyword = st.text_input("Ingresar Keyword")

        if st.button("🔍 Buscar") and keyword:
            with st.spinner("Obteniendo términos relacionados..."):
                results = get_people_also_search_for(keyword, location_code, language_code)
                if results:
                    # ✅ Mostrar en una tabla en lugar de una lista desordenada
                    df = pd.DataFrame({"Términos relacionados": results})
                    st.dataframe(df)
                else:
                    st.warning("⚠ No se encontraron términos relacionados.")

        st.stop()
