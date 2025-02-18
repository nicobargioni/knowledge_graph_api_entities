import streamlit as st
import sqlite3
import pandas as pd

# ✅ Configurar la página
st.set_page_config(page_title="Historial de Búsquedas", page_icon="📖", layout="wide")

# ✅ Obtener clave de admin desde Streamlit Secrets
ADMIN_PASS = st.secrets["ADMIN_PASS"]

# ✅ Obtener parámetros de la URL correctamente
query_params = st.query_params
admin_key = query_params.get("admin", [""])[0] if query_params else ""


# ✅ Función para obtener TODAS las búsquedas (solo para admin)
def get_all_search_history():
    try:
        conn = sqlite3.connect("search_logs.db")
        df = pd.read_sql_query("SELECT * FROM searches ORDER BY timestamp DESC", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Error al acceder a la base de datos: {e}")
        return pd.DataFrame()

# ✅ Función para obtener el historial del usuario
def get_user_search_history():
    try:
        conn = sqlite3.connect("search_logs.db")
        df = pd.read_sql_query("SELECT query, language, timestamp FROM searches ORDER BY timestamp DESC LIMIT 20", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Error al acceder a la base de datos: {e}")
        return pd.DataFrame()

# 🔐 Verificar si es admin
if admin_key == ADMIN_PASS:
    st.title("🔐 Panel de Administrador")

    df_logs = get_all_search_history()
    if df_logs.empty:
        st.warning("⚠ No hay registros en la base de datos o no se pudo conectar.")
    else:
        st.write("## 📜 Historial de Todas las Búsquedas")
        st.dataframe(df_logs)

# 📖 Si no es admin, mostrar solo su historial
else:
    st.title("📖 Tu Historial de Búsquedas")

    user_logs = get_user_search_history()
    if user_logs.empty():
        st.warning("⚠ No tienes búsquedas recientes o no se pudo conectar a la base de datos.")
    else:
        st.dataframe(user_logs)
