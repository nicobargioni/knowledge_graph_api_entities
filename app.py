import streamlit as st
import sqlite3
import pandas as pd
import requests
import urllib

# ✅ Configurar la página
st.set_page_config(page_title="Google Knowledge Graph Explorer", page_icon="🔍", layout="wide")

# ✅ Obtener clave de admin desde Streamlit Secrets
ADMIN_PASS = st.secrets["ADMIN_PASS"]

# ✅ Obtener parámetros de la URL
query_string = st.query_params.to_dict()
admin_key = query_string.get("admin", "")

# Si admin_key sigue vacío, intenta leerlo directamente desde la URL completa
if not admin_key:
    parsed_url = urllib.parse.urlparse(st.experimental_get_query_params())
    query_params_dict = urllib.parse.parse_qs(parsed_url.query)
    admin_key = query_params_dict.get("admin", [""])[0]

st.write(f"🔍 Debug: admin_key = {admin_key}")


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

# ✅ Función para guardar una búsqueda en la base de datos
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
        df = pd.read_sql_query("SELECT * FROM searches ORDER BY timestamp DESC", conn)
        conn.close()
        return df if not df.empty else pd.DataFrame(columns=["query", "language", "timestamp"])
    except Exception as e:
        st.error(f"❌ Error al acceder a la base de datos: {e}")
        return pd.DataFrame(columns=["query", "language", "timestamp"])  # Retorna un DataFrame vacío en caso de error

# 🔐 Si accedes con `?admin=clave`, muestra el Panel de Administrador
if str(admin_key).strip() == str(ADMIN_PASS).strip():
    st.title("🔐 Panel de Administrador")

    df_logs = get_all_search_history()
    if df_logs.empty:
        st.warning("⚠ No hay registros en la base de datos.")
    else:
        st.write("## 📜 Historial de Todas las Búsquedas")
        st.dataframe(df_logs)

    st.stop()  # Para evitar que el resto de la app se ejecute

# 🔍 Si no es admin, mostrar la app normal con el buscador
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
            params = {"query": query, "limit": 50, "key": st.secrets["GOOGLE_KG_API_KEY"], "languages": lang_code}
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

                # ✅ Guardar búsqueda en la base de datos
                save_search(query, lang_code)

        # ✅ Mostrar resultados
        if results:
            st.write("### Resultados")
            st.dataframe(pd.DataFrame(results))
        else:
            st.warning("⚠ No se encontraron entidades relacionadas.")
