import streamlit as st
import sqlite3
import pandas as pd

# Ocultar esta página del menú de Streamlit
st.set_page_config(page_title="Panel de Administrador", page_icon="📊", layout="wide")

# Función para obtener el historial de búsquedas
def get_search_history():
    conn = sqlite3.connect("search_logs.db")
    df = pd.read_sql_query("SELECT * FROM searches ORDER BY timestamp DESC", conn)
    conn.close()
    return df

# 🌟 Panel de Administración
st.markdown("<h1 style='text-align: center;'>📊 Panel de Administrador</h1>", unsafe_allow_html=True)

# 🔒 Protección con clave de acceso
password = st.text_input("🔑 Ingresa la clave de administrador", type="password")

# 🔑 Verificar clave
if password == "tu_clave_secreta":  # 🚨 CAMBIA ESTO POR UNA CLAVE SEGURA
    st.success("✅ Acceso concedido")

    # Obtener historial de búsquedas
    df_logs = get_search_history()

    if df_logs.empty:
        st.warning("⚠ No hay registros en la base de datos.")
    else:
        st.write("## 📜 Historial de Búsquedas")
        st.dataframe(df_logs)

else:
    st.warning("⚠ Acceso denegado. Ingresa la clave correcta.")
