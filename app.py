import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from PIL import Image
import io
import os
from fpdf import FPDF
from sqlalchemy import create_engine, text, Column, Integer, String, Float, Date, LargeBinary
from sqlalchemy.orm import sessionmaker, declarative_base

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Ministerios Vida", layout="wide", page_icon="✝️")

# --- CONEXIÓN A BASE DE DATOS (SUPABASE / POSTGRESQL) ---
# Usamos st.secrets para obtener la URL segura desde la nube
try:
    DATABASE_URL = st.secrets["connections"]["postgresql"]["url"]
except:
    st.error("⚠️ Error: No se detectó la conexión a la base de datos. Configura los 'Secrets' en Streamlit Cloud.")
    st.stop()

# Configuración de SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELOS DE LA BASE DE DATOS ---
class Finanza(Base):
    __tablename__ = "finanzas"
    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(String)
    tipo = Column(String)
    categoria = Column(String)
    monto = Column(Float)
    nota = Column(String)
    usuario = Column(String)
    evidencia = Column(LargeBinary) # Para guardar archivos
    nombre_archivo = Column(String)

class Asistencia(Base):
    __tablename__ = "asistencia"
    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(String)
    servicio = Column(String)
    hombres = Column(Integer)
    mujeres = Column(Integer)
    ninos = Column(Integer)
    nota = Column(String)

class Actividad(Base):
    __tablename__ = "actividades"
    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(String)
    nombre = Column(String)
    encargado = Column(String)
    descripcion = Column(String)

# Crear tablas si no existen
# Base.metadata.create_all(bind=engine)

# --- FUNCIONES DE GESTIÓN DE DATOS ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def guardar_finanza(fecha, tipo, categoria, monto, nota, usuario, evidencia, nombre_archivo):
    db = SessionLocal()
    # Leer binario
    blob_data = evidencia.read() if evidencia else None
    nuevo = Finanza(
        fecha=str(fecha), tipo=tipo, categoria=categoria, monto=monto, 
        nota=nota, usuario=usuario, evidencia=blob_data, nombre_archivo=nombre_archivo
    )
    db.add(nuevo)
    db.commit()
    db.close()

def guardar_asistencia(fecha, servicio, h, m, n, nota):
    db = SessionLocal()
    nuevo = Asistencia(
        fecha=str(fecha), servicio=servicio, hombres=h, mujeres=m, ninos=n, nota=nota
    )
    db.add(nuevo)
    db.commit()
    db.close()

def guardar_actividad(fecha, nombre, encargado, descripcion):
    db = SessionLocal()
    nuevo = Actividad(
        fecha=str(fecha), nombre=nombre, encargado=encargado, descripcion=descripcion
    )
    db.add(nuevo)
    db.commit()
    db.close()

def cargar_datos(modelo):
    # Cargar datos usando pandas y sqlalchemy
    try:
        df = pd.read_sql(db.query(modelo).statement, db.bind)
        return df
    except Exception as e:
        return pd.DataFrame()

def eliminar_registro(modelo_class, id_registro):
    db = SessionLocal()
    registro = db.query(modelo_class).filter(modelo_class.id == id_registro).first()
    if registro:
        db.delete(registro)
        db.commit()
    db.close()

# --- FUNCIONES PDF (MISMAS QUE ANTES) ---
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

# --- INTERFAZ ---
# Inicializar sesión de DB para Pandas
db = SessionLocal()

logo_path = "logo.jpg"
try:
    logo = Image.open(logo_path)
    st.sidebar.image(logo, use_container_width=True)
except:
    pass

st.sidebar.title("Menú Principal")

# LOGIN
users = {
    "dfuentes": "Pastordf2026**",
    "rmerlin": "rebeka2026"
}

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
        
        st.subheader("Resumen Financiero")
        df_fin = cargar_datos(Finanza)
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

        st.subheader("Comportamiento de Asistencia")
        df_asis = cargar_datos(Asistencia)
        
        if not df_asis.empty:
            df_asis['Total Asistentes'] = df_asis['hombres'] + df_asis['mujeres'] + df_asis['ninos']
            df_asis = df_asis.sort_values(by='fecha')
            
            fig_line = px.line(df_asis, x='fecha', y='Total Asistentes', 
                               markers=True, text='Total Asistentes',
                               title="Tendencia de Asistencia por Fecha",
                               color_discrete_sequence=['#2E86C1'])
            fig_line.update_traces(textposition="bottom right")
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Registra asistencias para ver la gráfica.")

    # 2. FINANZAS
    elif menu == "💰 Finanzas":
        st.header("Gestión Financiera")
        pestana1, pestana2 = st.tabs(["➕ Nuevo Registro", "📋 Historial"])

        with pestana1:
            col_ext_1, col_ext_2 = st.columns([1, 2])
            with col_ext_1:
                f_tipo = st.radio("Seleccione Tipo de Movimiento:", ["Ingreso", "Gasto"], horizontal=True)

            if f_tipo == "Ingreso":
                cat_opts = ["Ofrendas", "Diezmos", "Ofrendas de Amor", "Donaciones", "Otros"]
            else:
                cat_opts = ["Pago de Servicios", "Pago de renta", "Ayuda Social", "Otros"]
                st.warning("⚠️ REQUERIDO: Para registrar un GASTO es OBLIGATORIO subir la factura o recibo.")

            with st.form("form_finanzas", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    f_fecha = st.date_input("Fecha")
                    st.write(f"Tipo seleccionado: **{f_tipo}**")
                with col2:
                    f_cat = st.selectbox("Categoría", cat_opts)
                    f_monto = st.number_input("Monto", min_value=0.0, step=0.01)
                
                f_nota = st.text_area("Nota / Detalle")
                f_archivo = st.file_uploader("Adjuntar Soporte (Factura/Recibo)", type=['png', 'jpg', 'jpeg', 'pdf'])
                
                if f_archivo:
                    st.info(f"Archivo cargado: {f_archivo.name}")
                    if f_archivo.type in ['image/png', 'image/jpeg', 'image/jpg']:
                        st.image(f_archivo, width=200, caption="Vista previa")
                
                submitted = st.form_submit_button("💾 Guardar Registro", use_container_width=True)
                
                if submitted:
                    if f_tipo == "Gasto" and f_archivo is None:
                        st.error("⛔ ERROR: No se puede guardar un GASTO sin adjuntar el soporte físico.")
                    else:
                        f_name = f_archivo.name if f_archivo else None
                        guardar_finanza(f_fecha, f_tipo, f_cat, f_monto, f_nota, st.session_state['user_role'], f_archivo, f_name)
                        st.success("✅ Registro guardado exitosamente en la Nube.")

        with pestana2:
            df = cargar_datos(Finanza)
            if not df.empty:
                df = df.sort_values(by='fecha', ascending=False)
                c1, c2, c3, c4, c5 = st.columns([2, 2, 3, 2, 1])
                c1.markdown("**Fecha**"); c2.markdown("**Tipo**"); c3.markdown("**Detalle**"); c4.markdown("**Monto**"); c5.markdown("**Acción**")
                st.divider()
                for i, row in df.iterrows():
                    xc1, xc2, xc3, xc4, xc5 = st.columns([2, 2, 3, 2, 1])
                    with xc1: st.write(row['fecha'])
                    with xc2: st.write(f"{'🟢' if row['tipo']=='Ingreso' else '🔴'} {row['categoria']}")
                    with xc3: 
                        st.caption(f"Por: {row['usuario']}")
                        st.write(row['nota'])
                        if row['evidencia']: 
                            file_name = row['nombre_archivo'] if row['nombre_archivo'] else "doc"
                            if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                                try:
                                    image = Image.open(io.BytesIO(row['evidencia']))
                                    st.image(image, width=100)
                                except: pass
                            else:
                                st.download_button("📎 Descargar PDF", row['evidencia'], file_name, key=f"dl_{row['id']}")
                    with xc4: st.write(f"${row['monto']:,.2f}")
                    with xc5:
                        if st.button("🗑️", key=f"del_f_{row['id']}"):
                            eliminar_registro(Finanza, row['id'])
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
                    st.success("Guardado en la Nube.")
        
        with t2:
            dfa = cargar_datos(Asistencia)
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
                        if st.button("🗑️", key=f"del_a_{row['id']}"):
                            eliminar_registro(Asistencia, row['id'])
                            st.rerun()
                    st.markdown("---")
            else: st.info("Sin registros.")

    # 4. ACTIVIDADES
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
            df_act = cargar_datos(Actividad)
            if not df_act.empty:
                df_act = df_act.sort_values(by='fecha', ascending=True)
                c1, c2, c3, c4, c5 = st.columns([2, 3, 3, 3, 1])
                c1.markdown("**Fecha**"); c2.markdown("**Actividad**"); c3.markdown("**Encargado**"); c4.markdown("**Detalles**"); c5.markdown("**Acción**")
                st.divider()
                for index, row in df_act.iterrows():
                    ac1, ac2, ac3, ac4, ac5 = st.columns([2, 3, 3, 3, 1])
                    with ac1: st.write(row['fecha'])
                    with ac2: st.write(f"📌 {row['nombre']}")
                    with ac3: st.write(f"👤 {row['encargado']}")
                    with ac4: st.caption(row['descripcion'])
                    with ac5:
                        if st.button("🗑️", key=f"del_act_{row['id']}"):
                            eliminar_registro(Actividad, row['id'])
                            st.rerun()
                    st.markdown("---")
            else:
                st.info("No hay actividades programadas.")

    # 5. REPORTES
    elif menu == "📂 Reportes":
        st.header("Generar Reportes PDF")
        t1, t2 = st.tabs(["💰 Finanzas", "👥 Asistencia"])
        with t1:
            df_fin = cargar_datos(Finanza)
            if not df_fin.empty:
                if st.button("📄 Descargar PDF Finanzas"):
                    st.download_button("⬇️ Descargar", generar_pdf_finanzas(df_fin), "Finanzas.pdf", "application/pdf")
            else: st.warning("Sin datos.")
        with t2:
            df_asis = cargar_datos(Asistencia)
            if not df_asis.empty:
                if st.button("📄 Descargar PDF Asistencia"):
                    st.download_button("⬇️ Descargar", generar_pdf_asistencia(df_asis), "Asistencia.pdf", "application/pdf")
            else: st.warning("Sin datos.")

# Cierre sesión final
db.close()