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

# ✅ Capturar parámetros de la URL
query_params = st.query_params.to_dict()
admin_key = str(query_params.get("admin", "")).strip()
related_key = str(query_params.get("related", "")).strip()

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

        # 🔹 Configurar cliente de DataForSEO
        client = RestClient(DATAFORSEO_USERNAME, DATAFORSEO_PASSWORD)

        # 🔹 Parámetros de la consulta
        post_data = [{
            "keyword": keyword,
            "location_code": 2840,
            "language_code": "es",
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

# 🔹 **Panel de Administrador si accedes con `?admin=nbseo`**
if admin_key.strip() == ADMIN_PASS.strip():

    st.title("🔐 Panel de Administrador")

    df_logs = get_all_search_history()
    if df_logs.empty:
        st.warning("⚠ No hay registros en la base de datos.")
    else:
        st.write("## 📜 Historial de Todas las Búsquedas")
        st.dataframe(df_logs)

    st.stop()  # Para evitar que el resto de la app se ejecute

# 🔹 **Si accedes con `?related=1`, mostrar "People Also Search For"**
elif related_key == "1":
    st.title("🔍 People Also Search For")
    keyword = st.text_input("Ingresar Keyword")

    if st.button("🔍 Buscar") and keyword:
        with st.spinner("Obteniendo términos relacionados..."):
            results = get_people_also_search_for(keyword)
            if results:
                # ✅ Mostrar en una tabla en lugar de una lista desordenada
                df = pd.DataFrame({"Términos relacionados": results})
                st.dataframe(df)
            else:
                st.warning("⚠ No se encontraron términos relacionados.")

    st.stop()


# 🔹 **Si no hay `?admin=...` ni `?related=1`, mostrar el buscador normal**
st.title("🔍 Google Knowledge Graph Explorer")

st.markdown("""Google Knowledge Graph es una base de datos de entidades del mundo real, como **📌 personas, 🌎 lugares y 📦 productos**, que ayuda a comprender mejor el significado **semántico** de las búsquedas.

---

### 📊 ¿Qué es el *Score* de una entidad?  
Cada entidad tiene un **📈 *score*** que indica su **relevancia** respecto a la keyword buscada:  
✅ **Valores altos** → Entidad ampliamente reconocida.  
⚠ **Valores bajos** → Entidad menos popular o con menos referencias.  

---

### 🛠 ¿Cómo usar estos datos?  
🔹 **SEO & Interlinking:** Encontrando relaciones entre entidades para mejorar el contenido.  
🔹 **Datos estructurados:** Utilizando etiquedas se relación semántica para mejorar la visibilidad del sitio en nuevos contextos / mercados.  
🔹 **Análisis de tendencias:** Se puede descubrir qué entidades están más relacionadas con una keyword en un momento determinado.  

---

### 😺 Pro tip:
✅ Las combinaciones de idiomas pueden dar resultados interesantes. Una entidad puede ser más popular en un idioma que en otro.
""")

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

# ✅ Buscar en la API de Google Knowledge Graph
if st.button("🔍 Buscar") and query:
    with st.spinner("Buscando entidades..."):
        results = []
        for lang_code in selected_languages:
            url = "https://kgsearch.googleapis.com/v1/entities:search"
            params = {"query": query, "limit": 50, "key": GOOGLE_KG_API_KEY, "languages": lang_code}

            try:
                response = requests.get(url, params=params)
                response.raise_for_status()

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

        # ✅ Mostrar resultados en tabla
        if results:
            st.write("### Resultados")
            st.dataframe(pd.DataFrame(results))
        else:
            st.warning("⚠ No se encontraron entidades relacionadas.")

footer = """
<style>
    .footer {
        position: fixed;
        bottom: 10px;
        width: 100%;
        text-align: center;
        font-size: 14px;
        color: gray;
    }
</style>
<div class="footer">
    Nicolás Bargioni | SEO Specialist
</div>
"""

st.markdown(footer, unsafe_allow_html=True)
