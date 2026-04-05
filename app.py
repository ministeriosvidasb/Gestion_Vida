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
    st.error("⚠️ Error: Configura los 'Secrets' en Streamlit Cloud (Variable DATABASE_URL).")
    st.stop()

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELOS DE LA BASE DE DATOS ---
class Finanza(Base):
    __tablename__ = "finanzas"
    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(String) # Guardado como string ISO por simplicidad en formularios
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
    estado = Column(String, default="Pendiente")

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

Base.metadata.create_all(bind=engine)

# --- FUNCIONES DE CARGA ---
def cargar_datos(modelo_class):
    db = SessionLocal()
    try:
        query = db.query(modelo_class).statement
        return pd.read_sql(query, db.bind)
    finally:
        db.close()

# --- LÓGICA DE TIEMPO ACTUAL ---
hoy = datetime.now()
mes_actual_str = hoy.strftime("%Y-%m")
primer_dia_mes = hoy.replace(day=1).date()

# --- LOGIN ---
users = {"dfuentes": "Pastordf2026**"}

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("⛪ Acceso Ministerios Vida")
    col_log, _ = st.columns([1, 2])
    with col_log:
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("Ingresar", use_container_width=True):
            if usuario in users and users[usuario] == password:
                st.session_state['logged_in'] = True
                st.session_state['user_role'] = usuario
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
else:
    # --- SIDEBAR CON LOGO ---
    if os.path.exists("logo.jpg"):
        st.sidebar.image("logo.jpg", use_container_width=True)
    
    st.sidebar.title("Menú Principal")
    st.sidebar.write(f"Bienvenido: **{st.session_state['user_role']}**")
    
    menu = st.sidebar.radio("Ir a:", ["📊 Panel", "🕊️ Diezmos", "💰 Ofrendas y Gastos", "👥 Asistencia", "📅 Actividades"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state['logged_in'] = False
        st.rerun()

    # 1. PANEL (Solo Mes Corriente)
    if menu == "📊 Panel":
        st.title(f"Resumen Mensual: {hoy.strftime('%B %Y')}")
        
        df_f = cargar_datos(Finanza)
        df_d = cargar_datos(Diezmo)
        
        # Filtros para el mes actual
        if not df_f.empty:
            df_f['fecha_dt'] = pd.to_datetime(df_f['fecha']).dt.date
            df_mes_f = df_f[df_f['fecha_dt'] >= primer_dia_mes]
        else:
            df_mes_f = pd.DataFrame()

        df_mes_d = df_d[df_d['mes_contable'] == mes_actual_str] if not df_d.empty else pd.DataFrame()

        c1, c2, c3, c4 = st.columns(4)
        
        ing = df_mes_f[df_mes_f['tipo'] == 'Ingreso']['monto'].sum()
        gas = df_mes_f[df_mes_f['tipo'] == 'Gasto']['monto'].sum()
        diez_p = df_mes_d[df_mes_d['estado'] == 'Pendiente']['monto'].sum()
        
        c1.metric("Ofrendas del Mes", f"${ing:,.2f}")
        c2.metric("Gastos del Mes", f"${gas:,.2f}")
        c3.metric("Diezmos Pendientes", f"${diez_p:,.2f}")
        c4.metric("Saldo Disponible", f"${(ing - gas) + diez_p:,.2f}")

        st.divider()
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            if not df_mes_f.empty:
                fig = px.bar(df_mes_f, x='categoria', y='monto', color='tipo', title="Movimientos del Mes")
                st.plotly_chart(fig, use_container_width=True)
        with col_g2:
            df_a = cargar_datos(Asistencia)
            if not df_a.empty:
                df_a['fecha_dt'] = pd.to_datetime(df_a['fecha']).dt.date
                df_mes_a = df_a[df_a['fecha_dt'] >= primer_dia_mes]
                if not df_mes_a.empty:
                    df_mes_a['Total'] = df_mes_a['hombres'] + df_mes_a['mujeres'] + df_mes_a['ninos']
                    fig_a = px.line(df_mes_a, x='fecha', y='Total', title="Asistencia del Mes", markers=True)
                    st.plotly_chart(fig_a, use_container_width=True)

    # 2. DIEZMOS (Independientes)
    elif menu == "🕊️ Diezmos":
        st.header("Control de Diezmos")
        t1, t2 = st.tabs(["📥 Registro", "📊 Cierre de Mes"])
        
        with t1:
            with st.form("d_nuevo", clear_on_submit=True):
                col_x, col_y = st.columns(2)
                d_f = col_x.date_input("Fecha", hoy)
                d_n = col_x.text_input("Nombre del Miembro")
                d_m = col_y.number_input("Monto $", min_value=0.0)
                if st.form_submit_button("Guardar Diezmo"):
                    db = SessionLocal()
                    nuevo = Diezmo(fecha=d_f, miembro_nombre=d_n, monto=d_m, 
                                   mes_contable=d_f.strftime("%Y-%m"), estado="Pendiente")
                    db.add(nuevo)
                    db.commit()
                    db.close()
                    st.success("Registrado.")

        with t2:
            df_d = cargar_datos(Diezmo)
            if not df_d.empty:
                # Mostrar mes actual por defecto
                mes_sel = st.selectbox("Seleccione Mes para Liquidación", df_d['mes_contable'].unique()[::-1])
                resumen_mes = df_d[df_d['mes_contable'] == mes_sel]
                pend = resumen_mes[resumen_mes['estado'] == 'Pendiente']['monto'].sum()
                
                st.info(f"Total Diezmos de {mes_sel}: **${resumen_mes['monto'].sum():,.2f}**")
                st.dataframe(resumen_mes[['fecha', 'miembro_nombre', 'monto', 'estado']], use_container_width=True)
                
                if pend > 0:
                    if st.button(f"Confirmar Salida/Entrega de ${pend:,.2f}"):
                        db = SessionLocal()
                        db.query(Diezmo).filter(Diezmo.mes_contable == mes_sel, Diezmo.estado == "Pendiente").update({"estado": "Entregado"})
                        db.commit(); db.close()
                        st.success("Salida mensual procesada."); st.rerun()

    # 3. OFRENDAS Y GASTOS
    elif menu == "💰 Ofrendas y Gastos":
        st.header("Ingresos y Gastos")
        t1, t2 = st.tabs(["➕ Nuevo", "📋 Historial"])
        
        with t1:
            tipo = st.radio("Tipo", ["Ingreso", "Gasto"], horizontal=True)
            with st.form("f_form"):
                c1, c2 = st.columns(2)
                f = c1.date_input("Fecha")
                cat = c2.selectbox("Categoría", ["Ofrendas", "Donaciones"] if tipo == "Ingreso" else ["Servicios", "Renta", "Ayuda", "Mantenimiento"])
                m = c1.number_input("Monto", 0.0)
                n = st.text_area("Descripción")
                arch = st.file_uploader("Soporte")
                if st.form_submit_button("Guardar"):
                    db = SessionLocal()
                    blob = arch.read() if arch else None
                    nuevo = Finanza(fecha=str(f), tipo=tipo, categoria=cat, monto=m, nota=n, 
                                    usuario=st.session_state['user_role'], evidencia=blob, 
                                    nombre_archivo=arch.name if arch else None)
                    db.add(nuevo); db.commit(); db.close()
                    st.success("Guardado correctamente.")

        with t2:
            df = cargar_datos(Finanza)
            if not df.empty:
                ver_todo = st.toggle("Ver historial completo de otros meses")
                if not ver_todo:
                    df['fecha_dt'] = pd.to_datetime(df['fecha']).dt.date
                    df = df[df['fecha_dt'] >= primer_dia_mes]
                st.dataframe(df[['fecha', 'tipo', 'categoria', 'monto', 'nota']], use_container_width=True)

    # 4. ASISTENCIA
    elif menu == "👥 Asistencia":
        st.header("Asistencia")
        with st.form("a_form"):
            c1, c2 = st.columns(2)
            f = c1.date_input("Fecha")
            s = c1.selectbox("Servicio", ["Dominical", "Oración", "Estudio", "Vigilia"])
            h = c2.number_input("H", 0); m = c2.number_input("M", 0); n = c2.number_input("N", 0)
            if st.form_submit_button("Registrar"):
                db = SessionLocal()
                db.add(Asistencia(fecha=str(f), servicio=s, hombres=h, mujeres=m, ninos=n))
                db.commit(); db.close()
                st.success("Asistencia guardada.")
        
        df_a = cargar_datos(Asistencia)
        if not df_a.empty:
            ver_todo_a = st.toggle("Ver asistencias pasadas")
            if not ver_todo_a:
                df_a['fecha_dt'] = pd.to_datetime(df_a['fecha']).dt.date
                df_a = df_a[df_a['fecha_dt'] >= primer_dia_mes]
            st.dataframe(df_a, use_container_width=True)

    # 5. ACTIVIDADES
    elif menu == "📅 Actividades":
        st.header("Actividades del Mes")
        with st.form("act_form"):
            f = st.date_input("Fecha")
            nom = st.text_input("Actividad")
            enc = st.text_input("Responsable")
            desc = st.text_area("Detalles")
            if st.form_submit_button("Programar"):
                db = SessionLocal()
                db.add(Actividad(fecha=str(f), nombre=nom, encargado=enc, descripcion=desc))
                db.commit(); db.close()
                st.success("Actividad programada.")
        
        df_act = cargar_datos(Actividad)
        if not df_act.empty:
            df_act['fecha_dt'] = pd.to_datetime(df_act['fecha']).dt.date
            # Aquí mostramos lo que viene en el mes para planificar
            df_mes_act = df_act[df_act['fecha_dt'] >= primer_dia_mes].sort_values('fecha_dt')
            st.table(df_mes_act[['fecha', 'nombre', 'encargado']])
            # También se puede mostrar todo el calendario o actividades pasadas con un toggle similar a los anteriores.