import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
from PIL import Image
import io
import os
from fpdf import FPDF

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Ministerios Vida", layout="wide", page_icon="✝️")

# --- FUNCIONES DE BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('iglesia.db')
    c = conn.cursor()
    # Tabla Finanzas
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
    # Traemos el ROWID para poder borrar
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
        # Intentar poner logo si existe
        if os.path.exists("logo.jpg"):
            self.image('logo.jpg', 10, 8, 25) # x, y, w
            self.set_font('Arial', 'B', 15)
            # Mover a la derecha para el titulo
            self.cell(80)
            self.cell(30, 10, 'Reporte - Ministerios Vida', 0, 1, 'C')
        else:
            self.set_font('Arial', 'B', 15)
            self.cell(0, 10, 'Reporte - Ministerios Vida', 0, 1, 'C')
        self.ln(20)

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
    anchos = [30, 30, 40, 30, 60]
    
    for i, col in enumerate(cols):
        pdf.cell(anchos[i], 10, col, 1, 0, 'C')
    pdf.ln()
    
    # Datos
    for index, row in df.iterrows():
        pdf.cell(anchos[0], 10, str(row['fecha']), 1)
        pdf.cell(anchos[1], 10, str(row['tipo']), 1)
        cat_str = str(row['categoria']).encode('latin-1', 'replace').decode('latin-1')
        nota_str = str(row['nota']).encode('latin-1', 'replace').decode('latin-1')
        
        pdf.cell(anchos[2], 10, cat_str[:18], 1)
        pdf.cell(anchos[3], 10, f"${row['monto']}", 1)
        pdf.cell(anchos[4], 10, nota_str[:30], 1)
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

def generar_pdf_asistencia(df):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Encabezados (Fecha, Servicio, H, M, N, Total, Obs)
    headers = ["Fecha", "Servicio", "H", "M", "N", "Total", "Observaciones"]
    anchos = [25, 45, 10, 10, 10, 15, 75]
    
    for i, h in enumerate(headers):
        pdf.cell(anchos[i], 10, h, 1, 0, 'C')
    pdf.ln()
    
    # Datos
    for index, row in df.iterrows():
        total = row['hombres'] + row['mujeres'] + row['ninos']
        
        pdf.cell(anchos[0], 10, str(row['fecha']), 1)
        serv_str = str(row['servicio']).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(anchos[1], 10, serv_str[:22], 1)
        
        pdf.cell(anchos[2], 10, str(row['hombres']), 1, 0, 'C')
        pdf.cell(anchos[3], 10, str(row['mujeres']), 1, 0, 'C')
        pdf.cell(anchos[4], 10, str(row['ninos']), 1, 0, 'C')
        pdf.cell(anchos[5], 10, str(total), 1, 0, 'C')
        
        nota_str = str(row['nota']).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(anchos[6], 10, nota_str[:40], 1)
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

# Inicializar DB
init_db()

# --- INTERFAZ ---
logo_path = "logo.jpg"
try:
    logo = Image.open(logo_path)
    st.sidebar.image(logo, use_container_width=True)
except:
    pass # Si no hay logo, no mostrar error, solo no carga

st.sidebar.title("Menú Principal")

# LOGIN
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
    st.sidebar.write(f"Conectado como: **{st.session_state['user_role']}**")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state['logged_in'] = False
        st.rerun()

    menu = st.sidebar.radio("Navegación:", ["📊 Panel", "💰 Finanzas", "👥 Asistencia", "📂 Reportes"])

    # 1. PANEL
    if menu == "📊 Panel":
        st.title("Panel de Control")
        df_fin = cargar_datos("finanzas")
        
        if not df_fin.empty:
            ing = df_fin[df_fin['tipo'] == 'Ingreso']['monto'].sum()
            gas = df_fin[df_fin['tipo'] == 'Gasto']['monto'].sum()
            col1, col2, col3 = st.columns(3)
            col1.metric("Ingresos Totales", f"${ing:,.2f}")
            col2.metric("Gastos Totales", f"${gas:,.2f}")
            col3.metric("Caja Actual", f"${ing - gas:,.2f}", delta_color="normal")
            
            st.divider()
            
            g1, g2 = st.columns(2)
            with g1:
                st.subheader("Ingresos vs Gastos")
                fig_bar = px.bar(df_fin, x='tipo', y='monto', color='tipo', 
                                 title="Total por Tipo", text_auto=True,
                                 color_discrete_map={'Ingreso':'green', 'Gasto':'red'})
                st.plotly_chart(fig_bar, use_container_width=True)
            
            with g2:
                st.subheader("Distribución por Categoría")
                fig_pie = px.pie(df_fin, values='monto', names='categoria', 
                                 title="Desglose de Movimientos", hole=0.3)
                st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Registra movimientos para ver los gráficos.")

    # 2. FINANZAS
    elif menu == "💰 Finanzas":
        st.header("Gestión Financiera")
        pestana1, pestana2 = st.tabs(["➕ Nuevo Registro", "📋 Historial y Edición"])

        with pestana1:
            with st.form("form_finanzas", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    f_fecha = st.date_input("Fecha")
                    f_tipo = st.selectbox("Tipo", ["Ingreso", "Gasto"])
                with col2:
                    cat_opts = ["Diezmos", "Ofrendas", "Ventas"] if f_tipo == "Ingreso" else ["Luz/Agua", "Mantenimiento", "Ayuda", "Honorarios", "Limpieza"]
                    f_cat = st.selectbox("Categoría", cat_opts)
                    f_monto = st.number_input("Monto", min_value=0.0, step=0.01)
                
                f_nota = st.text_area("Nota / Descripción")
                f_archivo = st.file_uploader("Adjuntar Comprobante", type=['png', 'jpg', 'jpeg', 'pdf'])
                
                submitted = st.form_submit_button("💾 Guardar Registro", use_container_width=True)
                
                if submitted:
                    f_nombre_archivo = f_archivo.name if f_archivo else None
                    guardar_finanza(f_fecha, f_tipo, f_cat, f_monto, f_nota, st.session_state['user_role'], f_archivo, f_nombre_archivo)
                    st.success("Guardado exitosamente.")

        with pestana2:
            st.subheader("Historial de Movimientos")
            df = cargar_datos("finanzas")
            
            if not df.empty:
                df = df.sort_values(by='fecha', ascending=False)
                
                # Encabezados
                col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns([2, 2, 3, 2, 1])
                col_h1.markdown("**Fecha**")
                col_h2.markdown("**Tipo/Cat**")
                col_h3.markdown("**Detalle/Evidencia**") 
                col_h4.markdown("**Monto**")
                col_h5.markdown("**Acción**")
                
                st.divider()

                for index, row in df.iterrows():
                    c1, c2, c3, c4, c5 = st.columns([2, 2, 3, 2, 1])
                    with c1: st.write(row['fecha'])
                    with c2:
                        color = "🟢" if row['tipo'] == "Ingreso" else "🔴"
                        st.write(f"{color} {row['categoria']}")
                    with c3:
                        st.caption(row['nota'])
                        if row['evidencia']:
                            file_name = row['nombre_archivo'] if row['nombre_archivo'] else "doc"
                            if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                                try:
                                    image = Image.open(io.BytesIO(row['evidencia']))
                                    st.image(image, width=100)
                                except: st.error("Error img")
                            else:
                                st.download_button("📎 Ver", row['evidencia'], file_name)
                    with c4: st.write(f"**${row['monto']:,.2f}**")
                    with c5:
                        if st.button("🗑️", key=f"del_fin_{row['rowid']}"):
                            eliminar_registro("finanzas", row['rowid'])
                            st.rerun()
                    st.markdown("---")
            else:
                st.info("No hay datos.")

    # 3. ASISTENCIA (ACTUALIZADO: PESTAÑAS Y FORMATO IGUAL A FINANZAS)
    elif menu == "👥 Asistencia":
        st.header("Control de Asistencia")
        # PESTAÑAS
        tab_asis_1, tab_asis_2 = st.tabs(["➕ Nueva Asistencia", "📋 Historial y Borrar"])
        
        # PESTAÑA 1: Formulario
        with tab_asis_1:
            with st.form("form_asistencia", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    a_fecha = st.date_input("Fecha")
                    servicios_lista = ["Culto Dominical", "Lunes de Oración", "Estudio Biblico", "Vigilia", "Otras Actividades Especiales"]
                    a_serv = st.selectbox("Servicio", servicios_lista)
                
                with col2:
                    h = st.number_input("Hombres", min_value=0)
                    m = st.number_input("Mujeres", min_value=0)
                    n = st.number_input("Niños", min_value=0)
                
                a_nota = st.text_area("Observaciones", placeholder="Detalles adicionales del servicio...")
                
                total = h + m + n
                st.write(f"**Total Asistentes: {total}**")
                
                submitted_a = st.form_submit_button("💾 Guardar Asistencia", use_container_width=True)
                
                if submitted_a:
                    guardar_asistencia(a_fecha, a_serv, h, m, n, a_nota)
                    st.success("Asistencia guardada correctamente.")

        # PESTAÑA 2: Historial idéntico a Finanzas
        with tab_asis_2:
            st.subheader("Historial de Servicios")
            df_asis = cargar_datos("asistencia")
            
            if not df_asis.empty:
                df_asis = df_asis.sort_values(by='fecha', ascending=False)
                
                # Encabezados
                c_h1, c_h2, c_h3, c_h4, c_h5 = st.columns([2, 3, 2, 3, 1])
                c_h1.markdown("**Fecha**")
                c_h2.markdown("**Servicio**")
                c_h3.markdown("**Desglose**")
                c_h4.markdown("**Observaciones**")
                c_h5.markdown("**Acción**")
                
                st.divider()
                
                for index, row in df_asis.iterrows():
                    total_asis = row['hombres'] + row['mujeres'] + row['ninos']
                    col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 3, 1])
                    
                    with col1: st.write(row['fecha'])
                    with col2: st.write(f"⛪ {row['servicio']}")
                    with col3: 
                        st.write(f"H: {row['hombres']} | M: {row['mujeres']} | N: {row['ninos']}")
                        st.caption(f"**Total: {total_asis}**")
                    with col4: st.write(row['nota'])
                    with col5:
                        if st.button("🗑️", key=f"del_asis_{row['rowid']}"):
                            eliminar_registro("asistencia", row['rowid'])
                            st.rerun()
                    st.markdown("---")
            else:
                st.info("No hay registros de asistencia.")

    # 4. REPORTES (ACTUALIZADO: AÑADIDO REPORTE ASISTENCIA)
    elif menu == "📂 Reportes":
        st.header("Generar Reportes PDF")
        
        tab_rep_1, tab_rep_2 = st.tabs(["💰 Reporte Finanzas", "👥 Reporte Asistencia"])
        
        with tab_rep_1:
            st.subheader("Finanzas")
            df_fin = cargar_datos("finanzas")
            if not df_fin.empty:
                if st.button("📄 Descargar PDF Finanzas"):
                    pdf_bytes = generar_pdf_finanzas(df_fin)
                    st.download_button("⬇️ Descargar", pdf_bytes, f"Finanzas_{datetime.now().date()}.pdf", "application/pdf")
            else:
                st.warning("Sin datos financieros.")
                
        with tab_rep_2:
            st.subheader("Asistencia")
            df_asis = cargar_datos("asistencia")
            if not df_asis.empty:
                if st.button("📄 Descargar PDF Asistencia"):
                    pdf_bytes_a = generar_pdf_asistencia(df_asis)
                    st.download_button("⬇️ Descargar", pdf_bytes_a, f"Asistencia_{datetime.now().date()}.pdf", "application/pdf")
            else:
                st.warning("Sin datos de asistencia.")