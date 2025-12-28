import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
from PIL import Image
import io
from fpdf import FPDF

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Ministerios Vida", layout="wide", page_icon="✝️")

# --- FUNCIONES DE BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('iglesia.db')
    c = conn.cursor()
    # Tabla Finanzas (Ahora con campo 'evidencia' para archivos)
    c.execute('''CREATE TABLE IF NOT EXISTS finanzas
                 (fecha TEXT, tipo TEXT, categoria TEXT, monto REAL, nota TEXT, usuario TEXT, evidencia BLOB, nombre_archivo TEXT)''')
    # Tabla Asistencia
    c.execute('''CREATE TABLE IF NOT EXISTS asistencia
                 (fecha TEXT, servicio TEXT, hombres INTEGER, mujeres INTEGER, ninos INTEGER, nota TEXT)''')
    conn.commit()
    conn.close()

def guardar_finanza(fecha, tipo, categoria, monto, nota, usuario, evidencia, nombre_archivo):
    conn = sqlite3.connect('iglesia.db')
    c = conn.cursor()
    # Convertir archivo a binario si existe
    blob_data = evidencia.read() if evidencia else None
    
    c.execute("INSERT INTO finanzas VALUES (?,?,?,?,?,?,?,?)", 
              (fecha, tipo, categoria, monto, nota, usuario, blob_data, nombre_archivo))
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
    # Traemos el ROWID para poder identificar qué borrar
    df = pd.read_sql_query(f"SELECT rowid, * FROM {tabla}", conn)
    conn.close()
    return df

def eliminar_registro(tabla, id_registro):
    conn = sqlite3.connect('iglesia.db')
    c = conn.cursor()
    c.execute(f"DELETE FROM {tabla} WHERE rowid = ?", (id_registro,))
    conn.commit()
    conn.close()

# --- FUNCIONES PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Reporte - Ministerios Vida', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def generar_pdf_finanzas(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Encabezados
    cols = ["Fecha", "Tipo", "Categoria", "Monto", "Nota"]
    for col in cols:
        pdf.cell(38, 10, col, 1, 0, 'C')
    pdf.ln()
    
    # Datos
    for index, row in df.iterrows():
        pdf.cell(38, 10, str(row['fecha']), 1)
        pdf.cell(38, 10, str(row['tipo']), 1)
        pdf.cell(38, 10, str(row['categoria']).encode('latin-1', 'replace').decode('latin-1')[:15], 1)
        pdf.cell(38, 10, f"${row['monto']}", 1)
        pdf.cell(38, 10, str(row['nota']).encode('latin-1', 'replace').decode('latin-1')[:15], 1)
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

# Inicializar DB
init_db()

# --- INTERFAZ ---
# Cargar Logo
try:
    logo = Image.open("logo.jpg")
    st.sidebar.image(logo, use_column_width=True)
except:
    st.sidebar.warning("Falta logo.jpg")

st.sidebar.title("Menú")

# LOGIN (Mismo de antes)
users = {"admin": "vida123"}
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if usuario in users and users[usuario] == password:
            st.session_state['logged_in'] = True
            st.session_state['user_role'] = usuario
            st.rerun()
        else:
            st.error("Datos incorrectos")
else:
    st.sidebar.write(f"Hola, {st.session_state['user_role']}")
    if st.sidebar.button("Salir"):
        st.session_state['logged_in'] = False
        st.rerun()

    menu = st.sidebar.radio("Ir a:", ["📊 Panel", "💰 Finanzas", "👥 Asistencia", "📂 Reportes"])

    # 1. PANEL
    if menu == "📊 Panel":
        st.title("Panel de Control")
        df_fin = cargar_datos("finanzas")
        if not df_fin.empty:
            ing = df_fin[df_fin['tipo'] == 'Ingreso']['monto'].sum()
            gas = df_fin[df_fin['tipo'] == 'Gasto']['monto'].sum()
            st.metric("Caja Actual", f"${ing - gas:,.2f}")
        else:
            st.info("Sin datos.")

    # 2. FINANZAS
    elif menu == "💰 Finanzas":
        st.header("Gestión Financiera")
        pestana1, pestana2 = st.tabs(["➕ Nuevo (Auto-Limpieza)", "📋 Historial y Borrar"])

        with pestana1:
            # USAMOS st.form PARA LIMPIAR AL GUARDAR
            with st.form("form_finanzas", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    f_fecha = st.date_input("Fecha")
                    f_tipo = st.selectbox("Tipo", ["Ingreso", "Gasto"])
                with col2:
                    cat_opts = ["Diezmos", "Ofrendas", "Ventas"] if f_tipo == "Ingreso" else ["Luz/Agua", "Mantenimiento", "Ayuda"]
                    f_cat = st.selectbox("Categoría", cat_opts)
                    f_monto = st.number_input("Monto", min_value=0.0)
                
                f_nota = st.text_area("Nota")
                f_archivo = st.file_uploader("Subir Recibo/Foto", type=['png', 'jpg', 'jpeg', 'pdf'])
                
                submitted = st.form_submit_button("💾 Guardar Registro")
                
                if submitted:
                    f_nombre_archivo = f_archivo.name if f_archivo else None
                    guardar_finanza(f_fecha, f_tipo, f_cat, f_monto, f_nota, st.session_state['user_role'], f_archivo, f_nombre_archivo)
                    st.success("¡Guardado y formulario limpio!")

        with pestana2:
            df = cargar_datos("finanzas")
            if not df.empty:
                st.dataframe(df[['fecha', 'tipo', 'categoria', 'monto', 'nota', 'nombre_archivo']])
                
                # SECCIÓN PARA BORRAR
                st.divider()
                st.warning("Zona de Peligro: Borrar Registros")
                id_borrar = st.selectbox("Selecciona ID para borrar", df['rowid'])
                if st.button("🗑️ Borrar Registro Seleccionado"):
                    eliminar_registro("finanzas", id_borrar)
                    st.rerun()
            else:
                st.info("No hay registros.")

    # 3. ASISTENCIA
    elif menu == "👥 Asistencia":
        st.header("Asistencia")
        with st.form("form_asistencia", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                a_fecha = st.date_input("Fecha")
                a_serv = st.selectbox("Servicio", ["Dominical", "Jóvenes"])
            with col2:
                h = st.number_input("Hombres", 0)
                m = st.number_input("Mujeres", 0)
                n = st.number_input("Niños", 0)
            
            submitted_a = st.form_submit_button("💾 Guardar Asistencia")
            if submitted_a:
                guardar_asistencia(a_fecha, a_serv, h, m, n, "")
                st.success("Guardado.")

    # 4. REPORTES
    elif menu == "📂 Reportes":
        st.header("Generar Reportes PDF")
        df = cargar_datos("finanzas")
        
        if not df.empty:
            st.write("Vista previa de datos:")
            st.dataframe(df.head())
            
            if st.button("📄 Generar PDF de Finanzas"):
                pdf_bytes = generar_pdf_finanzas(df)
                st.download_button(
                    label="⬇️ Descargar Reporte PDF",
                    data=pdf_bytes,
                    file_name="reporte_finanzas.pdf",
                    mime="application/pdf"
                )
        else:
            st.warning("No hay datos para generar reporte.")