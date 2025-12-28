import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
from PIL import Image

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Ministerios Vida", layout="wide", page_icon="✝️")

# --- FUNCIONES DE BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('iglesia.db')
    c = conn.cursor()
    # Tabla Finanzas
    c.execute('''CREATE TABLE IF NOT EXISTS finanzas
                 (fecha TEXT, tipo TEXT, categoria TEXT, monto REAL, nota TEXT, usuario TEXT)''')
    # Tabla Asistencia
    c.execute('''CREATE TABLE IF NOT EXISTS asistencia
                 (fecha TEXT, servicio TEXT, hombres INTEGER, mujeres INTEGER, ninos INTEGER, nota TEXT)''')
    conn.commit()
    conn.close()

def guardar_finanza(fecha, tipo, categoria, monto, nota, usuario):
    conn = sqlite3.connect('iglesia.db')
    c = conn.cursor()
    c.execute("INSERT INTO finanzas VALUES (?,?,?,?,?,?)", (fecha, tipo, categoria, monto, nota, usuario))
    conn.commit()
    conn.close()

def guardar_asistencia(fecha, servicio, h, m, n, nota):
    conn = sqlite3.connect('iglesia.db')
    c = conn.cursor()
    c.execute("INSERT INTO asistencia VALUES (?,?,?,?,?,?)", (fecha, servicio, h, m, n, nota))
    conn.commit()
    conn.close()

def cargar_datos(tabla):
    conn = sqlite3.connect('iglesia.db')
    df = pd.read_sql_query(f"SELECT * FROM {tabla}", conn)
    conn.close()
    return df

# Inicializar DB al arrancar
init_db()

# --- INTERFAZ PRINCIPAL ---

# Cargar Logo (Manejo de errores por si no está el archivo aún)
try:
    logo = Image.open("logo.jpg")
    st.sidebar.image(logo, use_column_width=True)
except:
    st.sidebar.warning("Sube el archivo 'logo.jpg' a la carpeta")

st.sidebar.title("Menú Principal")

# --- SISTEMA DE LOGIN SIMPLIFICADO ---
# En producción esto iría en una base de datos segura
users = {"admin": "vida123", "tesoreria": "finanzas2024"}

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_role'] = None

if not st.session_state['logged_in']:
    st.header("🔐 Acceso al Sistema - Ministerios Vida")
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if usuario in users and users[usuario] == password:
            st.session_state['logged_in'] = True
            st.session_state['user_role'] = usuario
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")
else:
    # --- APLICACIÓN UNA VEZ LOGUEADO ---
    st.sidebar.write(f"👤 Usuario: **{st.session_state['user_role'].upper()}**")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state['logged_in'] = False
        st.rerun()

    menu = st.sidebar.radio("Ir a:", ["📊 Panel General", "💰 Finanzas", "👥 Asistencia", "📂 Reportes"])

    # 1. PANEL GENERAL
    if menu == "📊 Panel General":
        st.title("Panel de Control - Ministerios Vida")
        
        # Cargar datos para métricas
        df_fin = cargar_datos("finanzas")
        df_asis = cargar_datos("asistencia")

        col1, col2, col3 = st.columns(3)
        
        # Métricas Financieras (Si hay datos)
        if not df_fin.empty:
            ingresos = df_fin[df_fin['tipo'] == 'Ingreso']['monto'].sum()
            gastos = df_fin[df_fin['tipo'] == 'Gasto']['monto'].sum()
            balance = ingresos - gastos
            col1.metric("Balance Total", f"${balance:,.2f}")
            col2.metric("Ingresos Totales", f"${ingresos:,.2f}")
            col3.metric("Gastos Totales", f"${gastos:,.2f}", delta_color="inverse")
        else:
            col1.info("Sin datos financieros aún.")

        st.divider()
        
        # Gráfico Rápido de Asistencia
        if not df_asis.empty:
            st.subheader("Tendencia de Asistencia")
            df_asis['total'] = df_asis['hombres'] + df_asis['mujeres'] + df_asis['ninos']
            fig = px.line(df_asis, x='fecha', y='total', color='servicio', markers=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Registra asistencias para ver gráficos aquí.")

    # 2. FINANZAS
    elif menu == "💰 Finanzas":
        st.header("Gestión Financiera")
        pestana1, pestana2 = st.tabs(["➕ Nuevo Registro", "📋 Ver Registros"])

        with pestana1:
            col1, col2 = st.columns(2)
            with col1:
                f_fecha = st.date_input("Fecha")
                f_tipo = st.selectbox("Tipo de Movimiento", ["Ingreso", "Gasto"])
            with col2:
                if f_tipo == "Ingreso":
                    f_cat = st.selectbox("Categoría", ["Diezmos", "Ofrendas", "Donaciones", "Ventas", "Otros"])
                else:
                    f_cat = st.selectbox("Categoría", ["Servicios Básicos", "Mantenimiento", "Ayuda Social", "Honorarios", "Materiales"])
                f_monto = st.number_input("Monto ($)", min_value=0.0, step=0.01)
            
            f_nota = st.text_area("Detalles / Nota")
            
            if st.button("Guardar Movimiento Financiero"):
                guardar_finanza(f_fecha, f_tipo, f_cat, f_monto, f_nota, st.session_state['user_role'])
                st.success("Registro guardado correctamente.")

        with pestana2:
            st.dataframe(cargar_datos("finanzas"), use_container_width=True)

    # 3. ASISTENCIA
    elif menu == "👥 Asistencia":
        st.header("Control de Asistencia")
        pestana1, pestana2 = st.tabs(["➕ Nueva Asistencia", "📋 Historial"])

        with pestana1:
            col1, col2 = st.columns(2)
            with col1:
                a_fecha = st.date_input("Fecha del Servicio")
                a_servicio = st.selectbox("Servicio", ["Culto Dominical", "Estudio Bíblico", "Jóvenes", "Ayuno"])
            with col2:
                a_h = st.number_input("Hombres", min_value=0, step=1)
                a_m = st.number_input("Mujeres", min_value=0, step=1)
                a_n = st.number_input("Niños", min_value=0, step=1)
            
            a_nota = st.text_area("Observaciones del servicio")
            
            if st.button("Guardar Asistencia"):
                guardar_asistencia(a_fecha, a_servicio, a_h, a_m, a_n, a_nota)
                st.success("Asistencia registrada.")
        
        with pestana2:
            df = cargar_datos("asistencia")
            if not df.empty:
                df['TOTAL'] = df['hombres'] + df['mujeres'] + df['ninos']
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No hay registros.")

    # 4. REPORTES
    elif menu == "📂 Reportes":
        st.header("Reportes Inteligentes")
        tipo_reporte = st.selectbox("Selecciona reporte:", ["Finanzas por Categoría", "Crecimiento de Iglesia"])
        
        if tipo_reporte == "Finanzas por Categoría":
            df = cargar_datos("finanzas")
            if not df.empty:
                fig = px.pie(df, values='monto', names='categoria', title='Distribución de Finanzas')
                st.plotly_chart(fig)
            else:
                st.warning("No hay datos para graficar.")
