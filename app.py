import os
import streamlit as st
import sqlite3
import pandas as pd
import requests
import json
import base64
import response
# ✅ Configurar la página
st.set_page_config(page_title="Google Knowledge Graph Explorer", page_icon="🔍", layout="wide")

# ✅ Obtener claves API desde Streamlit Secrets
ADMIN_PASS = st.secrets.get("ADMIN_PASS", "")
DATAFORSEO_USERNAME = st.secrets.get("DATAFORSEO_USERNAME", "")
DATAFORSEO_PASSWORD = st.secrets.get("DATAFORSEO_PASSWORD", "")
GOOGLE_KG_API_KEY = st.secrets.get("GOOGLE_KG_API_KEY", "")

# ✅ Capturar parámetros de la URL
query_params = st.query_params
admin_key = query_params.get("admin", [""])[0] if query_params else ""
related_key = query_params.get("related", [""])[0] if query_params else ""

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
def get_people_also_search_for(keyword):
    """Consulta a la API de DataForSEO para obtener 'People Also Search For'."""
    try:
        if not DATAFORSEO_USERNAME or not DATAFORSEO_PASSWORD:
            st.error("❌ No se encontraron credenciales de DataForSEO.")
            return []

        # 🔹 Configurar autenticación en Base64
        credentials = f"{DATAFORSEO_USERNAME}:{DATAFORSEO_PASSWORD}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        # 🔹 Headers de la petición
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }

        # 🔹 Endpoint de DataForSEO
        url = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"

        # 🔹 Parámetros de la consulta
        payload = [{"keyword": keyword, "location_code": 2840, "language_code": "es", "device": "desktop"}]

        # 🔹 Realizar la solicitud
        response = requests.post(url, headers=headers, json=payload)

        # 🔹 Manejo de errores
        if response.status_code != 200:
            st.error(f"❌ Error en la API: {response.status_code} - {response.text}")
            return []

        # 🔹 Extraer datos
        data = response.json()
        related_searches = []
        
        results = data.get("tasks", [])[0].get("result", [])
        for result in results:
            if "items" in result:
                for item in result["items"]:
                    if "people_also_search" in item:
                        for related in item["people_also_search"]:
                            related_searches.append(related["title"])

        return related_searches

    except Exception as e:
        st.error(f"❌ Error en la solicitud: {e}")
        return []
    
st.write(f"admin_key capturado: {admin_key}")
st.write(response.status_code)
st.write(response.json())

# 🔹 **Si accedes con `?admin=nbseo`, mostrar el Panel de Administrador**
if admin_key == ADMIN_PASS:
    st.title("🔐 Panel de Administrador")

    df_logs = get_all_search_history()
    if df_logs.empty:
        st.warning("⚠ No hay registros en la base de datos.")
    else:
        st.write("## 📜 Historial de Todas las Búsquedas")
        st.dataframe(df_logs)

    st.stop()  # Para evitar que el resto de la app se ejecute

# 🔹 **Si accedes con `?related=1`, mostrar People Also Search For**
elif related_key == "1":
    st.title("🔍 People Also Search For")
    keyword = st.text_input("Ingresar Keyword")

    if st.button("🔍 Buscar") and keyword:
        with st.spinner("Obteniendo términos relacionados..."):
            results = get_people_also_search_for(keyword)
            if results:
                st.write("### Resultados:")
                for term in results:
                    st.write(f"- {term}")
            else:
                st.warning("⚠ No se encontraron términos relacionados.")

    st.stop()

# 🔹 **Si no hay `?admin=...` ni `?related=1`, mostrar el buscador normal**
st.title("🔍 Google Knowledge Graph Explorer")
st.write("🔎 Ingresa una palabra clave para buscar información estructurada sobre entidades.")

# ✅ Entrada de búsqueda
query = st.text_input("Ingresar Keyword")

# ✅ Opciones de idioma
language_options = {
    "Español": "es",
    "Inglés": "en",
    "Francés": "fr",
    "Alemán": "de",
    "Italiano": "it"
}
selected_languages = [code for lang, code in language_options.items() if st.checkbox(f"Buscar en {lang}")]

# ✅ Buscar en la API
if st.button("🔍 Buscar") and query:
    with st.spinner("Buscando entidades..."):
        results = []
        for lang_code in selected_languages:
            url = "https://kgsearch.googleapis.com/v1/entities:search"
            params = {"query": query, "limit": 50, "key": GOOGLE_KG_API_KEY, "languages": lang_code}

            try:
                response = requests.get(url, params=params)
                response.raise_for_status()  # ✅ Verificar si la API responde correctamente

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

                # Guardar la búsqueda en la base de datos
                save_search(query, lang_code)

            except requests.exceptions.RequestException as e:
                st.error(f"❌ Error al conectar con la API: {e}")

        # ✅ Mostrar resultados
        if results:
            st.write("### Resultados")
            st.dataframe(pd.DataFrame(results))
        else:
            st.warning("⚠ No se encontraron entidades relacionadas.")
