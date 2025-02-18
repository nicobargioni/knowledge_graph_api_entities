import streamlit as st
import sqlite3
import pandas as pd

# ✅ Configurar la página
st.set_page_config(page_title="Panel de Administrador", page_icon="🔐", layout="wide")

# ✅ Obtener clave de admin desde Streamlit Secrets
ADMIN_PASS = st.secrets["ADMIN_PASS"]

# ✅ Obtener parámetros de la URL correctamente
query_params = st.query_params
admin_key = query_params.get("admin", [""])[0] if query_params else ""

# 🔐 Bloquear el acceso si no eres admin
if admin_key != ADMIN_PASS:
    st.error("❌ Acceso denegado. Debes ingresar la clave de administrador.")
    st.stop()

# ✅ Función para obtener TODAS las búsquedas
def get_all_search_history():
    try:
        conn = sqlite3.connect("search_logs.db")
        df = pd.read_sql_query("SELECT * FROM searches ORDER BY timestamp DESC", conn)
        conn.close()
        return df if not df.empty else pd.DataFrame(columns=["query", "language", "timestamp"])
    except Exception as e:
        st.error(f"❌ Error al acceder a la base de datos: {e}")
        return pd.DataFrame(columns=["query", "language", "timestamp"])  # Retorna un DataFrame vacío en caso de error

# 🔹 Panel de Administrador
st.title("🔐 Panel de Administrador")

df_logs = get_all_search_history()
if df_logs.empty:
    st.warning("⚠ No hay registros en la base de datos.")
else:
    st.write("## 📜 Historial de Todas las Búsquedas")
    st.dataframe(df_logs)
