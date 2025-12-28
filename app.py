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
    # Tabla Actividades (NUEVA)
    c.execute('''CREATE TABLE IF NOT EXISTS actividades
                 (fecha TEXT, nombre TEXT, encargado TEXT, descripcion TEXT)''')
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

def guardar_actividad(fecha, nombre, encargado, descripcion):
    conn = sqlite3.connect('iglesia.db')
    c = conn.cursor()
    c.execute("INSERT INTO actividades VALUES (?,?,?,?)", (fecha, nombre, encargado, descripcion))
    conn.commit()
    conn.close()

def cargar_datos(tabla):
    conn = sqlite3.connect('iglesia.db')
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
        if os.path.exists("logo.jpg"):
            self.image('logo.jpg', 10, 8, 25)
            self.set_font('Arial', 'B', 15)
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
    cols = ["Fecha", "Tipo", "Categoria", "Monto", "Nota"]
    anchos = [30, 30, 40, 30, 60]
    for i, col in enumerate(cols): pdf.cell(anchos[i], 10, col, 1, 0, 'C')
    pdf.ln()
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
    headers = ["Fecha", "Servicio", "H", "M", "N", "Total", "Observaciones"]
    anchos = [25, 45, 10, 10, 10, 15, 75]
    for i, h in enumerate(headers): pdf.cell(anchos[i], 10, h, 1, 0, 'C')
    pdf.ln()
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
    pass

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

    menu = st.sidebar.radio("Navegación:", ["📊 Panel", "💰 Finanzas", "👥 Asistencia", "📅 Actividades", "📂 Reportes"])

    # 1. PANEL
    if menu == "📊 Panel":
        st.title("Panel de Control")
        
        # --- SECCIÓN FINANZAS ---
        st.subheader("Resumen Financiero")
        df_fin = cargar_datos("finanzas")
        if not df_fin.empty:
            ing = df_fin[df_fin['tipo'] == 'Ingreso']['monto'].sum()
            gas = df_fin[df_fin['tipo'] == 'Gasto']['monto'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Ingresos", f"${ing:,.2f}")
            c2.metric("Gastos", f"${gas:,.2f}")
            c3.metric("Caja", f"${ing - gas:,.2f}")
            
            g1, g2 = st.columns(2)
            with g1:
                fig_bar = px.bar(df_fin, x='tipo', y='monto', color='tipo', 
                                 title="Total por Tipo", text_auto=True,
                                 color_discrete_map={'Ingreso':'green', 'Gasto':'red'})
                st.plotly_chart(fig_bar, use_container_width=True)
            with g2:
                fig_pie = px.pie(df_fin, values='monto', names='categoria', 
                                 title="Desglose de Movimientos", hole=0.3)
                st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No hay datos financieros para mostrar.")

        st.divider()

        # --- SECCIÓN ASISTENCIA (NUEVA GRÁFICA) ---
        st.subheader("Comportamiento de Asistencia")
        df_asis = cargar_datos("asistencia")
        
        if not df_asis.empty:
            # Calcular total por registro
            df_asis['Total Asistentes'] = df_asis['hombres'] + df_asis['mujeres'] + df_asis['ninos']
            # Ordenar por fecha para que la línea tenga sentido
            df_asis = df_asis.sort_values(by='fecha')
            
            # Gráfico de Líneas
            fig_line = px.line(df_asis, x='fecha', y='Total Asistentes', 
                               markers=True, text='Total Asistentes',
                               title="Tendencia de Asistencia por Fecha",
                               color_discrete_sequence=['#2E86C1'])
            fig_line.update_traces(textposition="bottom right")
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Registra asistencias para ver la gráfica de comportamiento.")

    # 2. FINANZAS
    elif menu == "💰 Finanzas":
        st.header("Gestión Financiera")
        pestana1, pestana2 = st.tabs(["➕ Nuevo Registro", "📋 Historial"])

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
                f_nota = st.text_area("Nota")
                f_archivo = st.file_uploader("Evidencia", type=['png', 'jpg', 'pdf'])
                submitted = st.form_submit_button("💾 Guardar", use_container_width=True)
                if submitted:
                    f_name = f_archivo.name if f_archivo else None
                    guardar_finanza(f_fecha, f_tipo, f_cat, f_monto, f_nota, st.session_state['user_role'], f_archivo, f_name)
                    st.success("Guardado.")

        with pestana2:
            df = cargar_datos("finanzas")
            if not df.empty:
                df = df.sort_values(by='fecha', ascending=False)
                # Headers
                c1, c2, c3, c4, c5 = st.columns([2, 2, 3, 2, 1])
                c1.markdown("**Fecha**"); c2.markdown("**Tipo**"); c3.markdown("**Detalle**"); c4.markdown("**Monto**"); c5.markdown("**Acción**")
                st.divider()
                for i, row in df.iterrows():
                    xc1, xc2, xc3, xc4, xc5 = st.columns([2, 2, 3, 2, 1])
                    with xc1: st.write(row['fecha'])
                    with xc2: st.write(f"{'🟢' if row['tipo']=='Ingreso' else '🔴'} {row['categoria']}")
                    with xc3: 
                        st.caption(row['nota'])
                        if row['evidencia']: st.caption("📎 Con adjunto")
                    with xc4: st.write(f"${row['monto']:,.2f}")
                    with xc5:
                        if st.button("🗑️", key=f"del_f_{row['rowid']}"):
                            eliminar_registro("finanzas", row['rowid'])
                            st.rerun()
                    st.markdown("---")
            else: st.info("Sin registros.")

    # 3. ASISTENCIA
    elif menu == "👥 Asistencia":
        st.header("Control de Asistencia")
        t1, t2 = st.tabs(["➕ Nueva Asistencia", "📋 Historial"])
        
        with t1:
            with st.form("form_asis", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    a_fecha = st.date_input("Fecha")
                    a_serv = st.selectbox("Servicio", ["Culto Dominical", "Lunes de Oración", "Estudio Biblico", "Vigilia", "Otras Actividades Especiales"])
                with c2:
                    h = st.number_input("Hombres", 0); m = st.number_input("Mujeres", 0); n = st.number_input("Niños", 0)
                a_nota = st.text_area("Observaciones")
                if st.form_submit_button("💾 Guardar", use_container_width=True):
                    guardar_asistencia(a_fecha, a_serv, h, m, n, a_nota)
                    st.success("Guardado.")
        
        with t2:
            dfa = cargar_datos("asistencia")
            if not dfa.empty:
                dfa = dfa.sort_values(by='fecha', ascending=False)
                c1, c2, c3, c4, c5 = st.columns([2, 3, 2, 3, 1])
                c1.markdown("**Fecha**"); c2.markdown("**Servicio**"); c3.markdown("**Desglose**"); c4.markdown("**Obs**"); c5.markdown("**Borrar**")
                st.divider()
                for i, row in dfa.iterrows():
                    xc1, xc2, xc3, xc4, xc5 = st.columns([2, 3, 2, 3, 1])
                    with xc1: st.write(row['fecha'])
                    with xc2: st.write(row['servicio'])
                    with xc3: st.write(f"H:{row['hombres']} M:{row['mujeres']} N:{row['ninos']} (Tot: {row['hombres']+row['mujeres']+row['ninos']})")
                    with xc4: st.write(row['nota'])
                    with xc5:
                        if st.button("🗑️", key=f"del_a_{row['rowid']}"):
                            eliminar_registro("asistencia", row['rowid'])
                            st.rerun()
                    st.markdown("---")
            else: st.info("Sin registros.")

    # 4. ACTIVIDADES (NUEVO MODULO)
    elif menu == "📅 Actividades":
        st.header("Planificación de Actividades")
        tab_act_1, tab_act_2 = st.tabs(["➕ Nueva Actividad", "📋 Cronograma"])

        with tab_act_1:
            with st.form("form_actividades", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    act_fecha = st.date_input("Fecha de Actividad")
                    act_nombre = st.text_input("Nombre de la Actividad")
                with col2:
                    act_encargado = st.text_input("Encargado / Líder")
                
                act_desc = st.text_area("Detalles / En qué consiste")
                
                submitted_act = st.form_submit_button("💾 Guardar Actividad", use_container_width=True)
                
                if submitted_act:
                    if act_nombre and act_encargado:
                        guardar_actividad(act_fecha, act_nombre, act_encargado, act_desc)
                        st.success("Actividad programada exitosamente.")
                    else:
                        st.error("Por favor completa el nombre y el encargado.")

        with tab_act_2:
            st.subheader("Cronograma de Actividades")
            df_act = cargar_datos("actividades")
            
            if not df_act.empty:
                df_act = df_act.sort_values(by='fecha', ascending=True) # Ordenar por fecha próxima
                
                # Encabezados
                c1, c2, c3, c4, c5 = st.columns([2, 3, 3, 3, 1])
                c1.markdown("**Fecha**")
                c2.markdown("**Actividad**")
                c3.markdown("**Encargado**")
                c4.markdown("**Detalles**")
                c5.markdown("**Acción**")
                
                st.divider()
                
                for index, row in df_act.iterrows():
                    ac1, ac2, ac3, ac4, ac5 = st.columns([2, 3, 3, 3, 1])
                    with ac1: st.write(row['fecha'])
                    with ac2: st.write(f"📌 {row['nombre']}")
                    with ac3: st.write(f"👤 {row['encargado']}")
                    with ac4: st.caption(row['descripcion'])
                    with ac5:
                        if st.button("🗑️", key=f"del_act_{row['rowid']}"):
                            eliminar_registro("actividades", row['rowid'])
                            st.rerun()
                    st.markdown("---")
            else:
                st.info("No hay actividades programadas.")

    # 5. REPORTES
    elif menu == "📂 Reportes":
        st.header("Generar Reportes PDF")
        t1, t2 = st.tabs(["💰 Finanzas", "👥 Asistencia"])
        with t1:
            df_fin = cargar_datos("finanzas")
            if not df_fin.empty:
                if st.button("📄 Descargar PDF Finanzas"):
                    st.download_button("⬇️ Descargar", generar_pdf_finanzas(df_fin), "Finanzas.pdf", "application/pdf")
            else: st.warning("Sin datos.")
        with t2:
            df_asis = cargar_datos("asistencia")
            if not df_asis.empty:
                if st.button("📄 Descargar PDF Asistencia"):
                    st.download_button("⬇️ Descargar", generar_pdf_asistencia(df_asis), "Asistencia.pdf", "application/pdf")
            else: st.warning("Sin datos.")