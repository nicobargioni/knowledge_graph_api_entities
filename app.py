import streamlit as st
import requests
import pandas as pd
import sqlite3

# 🔹 Configuración inicial
st.set_page_config(page_title="Google Knowledge Graph Explorer", initial_sidebar_state="collapsed")

# 🔹 Función para conectar y registrar búsquedas en SQLite
def log_search(query, language):
    conn = sqlite3.connect("search_logs.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            language TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("INSERT INTO searches (query, language) VALUES (?, ?)", (query, language))
    conn.commit()
    conn.close()

# 🔹 Función para obtener historial de búsquedas (para Admin)
def get_search_history():
    conn = sqlite3.connect("search_logs.db")
    cursor = conn.cursor()
    
    # 🛠️ Crear la tabla si no existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            language TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    # 🔹 Intentar leer los datos después de asegurarnos de que la tabla existe
    df = pd.read_sql_query("SELECT * FROM searches ORDER BY timestamp DESC", conn)
    
    conn.close()
    return df

# 🔹 Función para obtener entidades del Knowledge Graph
def get_knowledge_graph_entities(api_key, query, language, lang_label, limit=50):
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

# ✅ **Verificar si es Admin accediendo con una URL secreta**
query_params = st.query_params
is_admin = query_params.get("nb_seo_admin") == "nbseo"  # 🔴 CAMBIA "clave_secreta"

# ✅ **Si es Admin, muestra el panel de administrador**
if is_admin:
    st.title("📊 Panel de Administrador")

    df_logs = get_search_history()

    if df_logs.empty:
        st.warning("⚠️ No hay registros en la base de datos.")
    else:
        st.write("### Historial de Búsquedas")
        st.dataframe(df_logs)

    st.stop()  # Evita que se muestre el resto de la app

# ✅ **Si no es admin, muestra la app normal**
st.title("Google Knowledge Graph Explorer")

api_key = st.text_input("API Key de Google Knowledge Graph", type="password")
query = st.text_input("Consulta de búsqueda")

# 🔹 Checkboxes para idiomas
language_es = st.checkbox("Buscar en español", value=True)
language_en = st.checkbox("Buscar en inglés", value=False)
language_fr = st.checkbox("Buscar en francés", value=False)
language_de = st.checkbox("Buscar en alemán", value=False)
language_it = st.checkbox("Buscar en italiano", value=False)

results = []

# ✅ **Botón de búsqueda**
if st.button("Buscar"):
    if not api_key or not query:
        st.warning("Por favor, ingrese una API Key y una consulta de búsqueda.")
    else:
        with st.spinner("Buscando entidades..."):
            if language_es:
                results.extend(get_knowledge_graph_entities(api_key, query, "es", "Español"))
                log_search(query, "Español")
            if language_en:
                results.extend(get_knowledge_graph_entities(api_key, query, "en", "Inglés"))
                log_search(query, "Inglés")
            if language_fr:
                results.extend(get_knowledge_graph_entities(api_key, query, "fr", "Francés"))
                log_search(query, "Francés")
            if language_de:
                results.extend(get_knowledge_graph_entities(api_key, query, "de", "Alemán"))
                log_search(query, "Alemán")
            if language_it:
                results.extend(get_knowledge_graph_entities(api_key, query, "it", "Italiano"))
                log_search(query, "Italiano")
            
            if results:
                df = pd.DataFrame(results)
                st.write("### Resultados")
                st.dataframe(df)
            else:
                st.warning("No se encontraron entidades relacionadas.")
