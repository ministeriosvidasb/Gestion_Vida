import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import os
from fpdf import FPDF
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, LargeBinary
from sqlalchemy.orm import sessionmaker, declarative_base
from PIL import Image

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Ministerios Vida", layout="wide", page_icon="✝️")

# --- CONEXIÓN A BASE DE DATOS ---
try:
    DATABASE_URL = st.secrets["connections"]["postgresql"]["url"]
except:
    st.error("⚠️ Error: Configura los 'Secrets' en Streamlit Cloud.")
    st.stop()

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
    evidencia = Column(LargeBinary)
    nombre_archivo = Column(String)

class Diezmo(Base):
    __tablename__ = "diezmos"
    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date)
    miembro_nombre = Column(String)
    monto = Column(Float)
    mes_contable = Column(String) # Formato YYYY-MM
    estado = Column(String, default="Pendiente") # Pendiente o Entregado

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
Base.metadata.create_all(bind=engine)

# --- FUNCIONES DE GESTIÓN DE DATOS ---
def cargar_datos(modelo_class):
    db = SessionLocal()
    try:
        query = db.query(modelo_class).statement
        df = pd.read_sql(query, db.bind)
        return df
    finally:
        db.close()

def eliminar_registro(modelo_class, id_registro):
    db = SessionLocal()
    try:
        registro = db.query(modelo_class).filter(modelo_class.id == id_registro).first()
        if registro:
            db.delete(registro)
            db.commit()
    finally:
        db.close()

# --- CLASE PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Ministerios Vida - Reporte Oficial', 0, 1, 'C')
        self.ln(10)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

# --- INTERFAZ Y LOGIN ---
users = {"dfuentes": "Pastordf2026**", "rmerlin": "rebeka2026"}

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("⛪ Acceso Ministerios Vida")
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if usuario in users and users[usuario] == password:
            st.session_state['logged_in'] = True
            st.session_state['user_role'] = usuario
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
else:
    # Sidebar
    st.sidebar.title("Menú Principal")
    st.sidebar.write(f"Usuario: **{st.session_state['user_role']}**")
    menu = st.sidebar.radio("Navegación:", ["📊 Panel", "🕊️ Diezmos", "💰 Ofrendas y Gastos", "👥 Asistencia", "📅 Actividades"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state['logged_in'] = False
        st.rerun()

    # 1. PANEL (DASHBOARD)
    if menu == "📊 Panel":
        st.title("Panel de Control")
        
        df_fin = cargar_datos(Finanza)
        df_diez = cargar_datos(Diezmo)
        
        c1, c2, c3, c4 = st.columns(4)
        
        # Ofrendas e Ingresos (Excluyendo diezmos de la tabla finanzas si existen)
        ing_ofrendas = df_fin[df_fin['tipo'] == 'Ingreso']['monto'].sum()
        gastos = df_fin[df_fin['tipo'] == 'Gasto']['monto'].sum()
        
        # Diezmos del mes actual
        mes_actual = datetime.now().strftime("%Y-%m")
        diezmos_pendientes = df_diez[df_diez['estado'] == 'Pendiente']['monto'].sum()
        
        c1.metric("Ingresos (Ofrendas)", f"${ing_ofrendas:,.2f}")
        c2.metric("Gastos Totales", f"${gastos:,.2f}")
        c3.metric("Diezmos por Entregar", f"${diezmos_pendientes:,.2f}")
        c4.metric("Caja Real", f"${(ing_ofrendas - gastos) + diezmos_pendientes:,.2f}")

        st.divider()
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            if not df_fin.empty:
                fig_fin = px.pie(df_fin, values='monto', names='tipo', title="Distribución Gastos vs Ofrendas", color_discrete_map={'Ingreso':'#27AE60','Gasto':'#E74C3C'})
                st.plotly_chart(fig_fin, use_container_width=True)
        
        with col_graf2:
            df_asis = cargar_datos(Asistencia)
            if not df_asis.empty:
                df_asis['Total'] = df_asis['hombres'] + df_asis['mujeres'] + df_asis['ninos']
                fig_asis = px.line(df_asis, x='fecha', y='Total', title="Tendencia de Asistencia", markers=True)
                st.plotly_chart(fig_asis, use_container_width=True)

    # 2. DIEZMOS (NUEVO MÓDULO)
    elif menu == "🕊️ Diezmos":
        st.header("Gestión de Diezmos")
        t1, t2 = st.tabs(["📥 Nuevo Ingreso", "📊 Cierre Mensual"])
        
        with t1:
            with st.form("nuevo_diezmo", clear_on_submit=True):
                col_a, col_b = st.columns(2)
                f_fecha = col_a.date_input("Fecha de Entrega", datetime.now())
                f_nombre = col_a.text_input("Nombre del Miembro")
                f_monto = col_b.number_input("Monto $", min_value=0.0)
                
                if st.form_submit_button("Guardar Diezmo"):
                    db = SessionLocal()
                    nuevo = Diezmo(fecha=f_fecha, miembro_nombre=f_nombre, monto=f_monto, 
                                   mes_contable=f_fecha.strftime("%Y-%m"), estado="Pendiente")
                    db.add(nuevo)
                    db.commit()
                    db.close()
                    st.success("Diezmo registrado correctamente.")

        with t2:
            df_d = cargar_datos(Diezmo)
            if not df_d.empty:
                meses = df_d['mes_contable'].unique()
                mes_sel = st.selectbox("Seleccione Mes Contable", meses)
                
                data_mes = df_d[df_d['mes_contable'] == mes_sel]
                pend = data_mes[data_mes['estado'] == 'Pendiente']['monto'].sum()
                
                st.subheader(f"Resumen de {mes_sel}")
                st.write(f"Total acumulado pendiente de salida: **${pend:,.2f}**")
                st.dataframe(data_mes[['fecha', 'miembro_nombre', 'monto', 'estado']], use_container_width=True)
                
                if pend > 0:
                    if st.button(f"Confirmar Salida de Fondos - {mes_sel}"):
                        db = SessionLocal()
                        db.query(Diezmo).filter(Diezmo.mes_contable == mes_sel, Diezmo.estado == "Pendiente").update({"estado": "Entregado"})
                        db.commit()
                        db.close()
                        st.success("Salida registrada con éxito.")
                        st.rerun()
            else:
                st.info("No hay registros de diezmos.")

    # 3. OFRENDAS Y GASTOS (ANTES FINANZAS)
    elif menu == "💰 Ofrendas y Gastos":
        st.header("Ofrendas y Gastos Generales")
        t1, t2 = st.tabs(["➕ Nuevo Registro", "📋 Historial"])
        
        with t1:
            f_tipo = st.radio("Tipo:", ["Ingreso", "Gasto"], horizontal=True)
            cats = ["Ofrendas", "Donaciones", "Especiales"] if f_tipo == "Ingreso" else ["Renta", "Servicios", "Ayuda Social", "Mantenimiento"]
            
            with st.form("form_fin"):
                c1, c2 = st.columns(2)
                f_fecha = c1.date_input("Fecha")
                f_cat = c2.selectbox("Categoría", cats)
                f_monto = c1.number_input("Monto", min_value=0.0)
                f_nota = st.text_area("Nota")
                f_archivo = st.file_uploader("Soporte (Obligatorio para Gastos)", type=['png','jpg','pdf'])
                
                if st.form_submit_button("Guardar"):
                    if f_tipo == "Gasto" and not f_archivo:
                        st.error("Debes subir un comprobante para gastos.")
                    else:
                        db = SessionLocal()
                        blob = f_archivo.read() if f_archivo else None
                        nuevo = Finanza(fecha=str(f_fecha), tipo=f_tipo, categoria=f_cat, monto=f_monto,
                                        nota=f_nota, usuario=st.session_state['user_role'], 
                                        evidencia=blob, nombre_archivo=f_archivo.name if f_archivo else None)
                        db.add(nuevo)
                        db.commit()
                        db.close()
                        st.success("Guardado.")

        with t2:
            df = cargar_datos(Finanza)
            st.dataframe(df[['fecha', 'tipo', 'categoria', 'monto', 'nota']], use_container_width=True)

    # 4. ASISTENCIA
    elif menu == "👥 Asistencia":
        st.header("Control de Asistencia")
        with st.form("asis"):
            c1, c2 = st.columns(2)
            f = c1.date_input("Fecha")
            s = c1.selectbox("Servicio", ["Dominical", "Oración", "Estudio"])
            h = c2.number_input("Hombres", 0); m = c2.number_input("Mujeres", 0); n = c2.number_input("Niños", 0)
            if st.form_submit_button("Guardar Asistencia"):
                db = SessionLocal()
                nuevo = Asistencia(fecha=str(f), servicio=s, hombres=h, mujeres=m, ninos=n)
                db.add(nuevo)
                db.commit()
                db.close()
                st.success("Asistencia registrada.")
        
        df_a = cargar_datos(Asistencia)
        st.dataframe(df_a, use_container_width=True)

    # 5. ACTIVIDADES
    elif menu == "📅 Actividades":
        st.header("Cronograma")
        with st.form("act"):
            f = st.date_input("Fecha")
            n = st.text_input("Actividad")
            e = st.text_input("Encargado")
            d = st.text_area("Descripción")
            if st.form_submit_button("Programar"):
                db = SessionLocal()
                nuevo = Actividad(fecha=str(f), nombre=n, encargado=e, descripcion=d)
                db.add(nuevo)
                db.commit()
                db.close()
                st.success("Actividad guardada.")
        
        df_act = cargar_datos(Actividad)
        st.table(df_act[['fecha', 'nombre', 'encargado']])
        # Detalles de actividades