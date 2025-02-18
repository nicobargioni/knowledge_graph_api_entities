import streamlit as st
import sqlite3
import pandas as pd
import os

# Ocultar esta página del menú de Streamlit
st.set_page_config(page_title="Panel de Administrador", page_icon="📊", layout="wide")

ADMIN_PASS = st.secrets["ADMIN_PASS"]

# Obtener parámetros de la URL
query_params = st.query_params
admin_key = query_params.get("admin", [""])[0]

# Si la clave en la URL no coincide, denegar acceso
if admin_key != ADMIN_PASS:
    st.warning("⚠ Acceso denegado. No tienes permisos para ver esta página.")
    st.stop()

# Función para obtener historial de búsquedas
def get_search_history():
    conn = sqlite3.connect("search_logs.db")
    df = pd.read_sql_query("SELECT * FROM searches ORDER BY timestamp DESC", conn)
    conn.close()
    return df

# 🌟 Panel de Administración
st.markdown("<h1 style='text-align: center;'>📊 Panel de Administrador</h1>", unsafe_allow_html=True)

df_logs = get_search_history()

if df_logs.empty:
    st.warning("⚠ No hay registros en la base de datos.")
else:
    st.write("## 📜 Historial de Búsquedas")
    st.dataframe(df_logs)