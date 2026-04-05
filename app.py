import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import os
from fpdf import FPDF
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, LargeBinary, text
from sqlalchemy.orm import sessionmaker, declarative_base
from PIL import Image

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Ministerios Vida", layout="wide", page_icon="✝️")

# --- CONEXIÓN A BASE DE DATOS ---
try:
    DATABASE_URL = st.secrets["connections"]["postgresql"]["url"]
except:
    st.error("⚠️ Error: Configura DATABASE_URL en los Secrets de Streamlit.")
    st.stop()

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELOS ---
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
    mes_contable = Column(String)
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

def cargar_datos(modelo_class):
    db = SessionLocal()
    try:
        query = db.query(modelo_class).statement
        return pd.read_sql(query, db.bind)
    except:
        return pd.DataFrame()
    finally:
        db.close()

# --- TIEMPO ---
hoy = datetime.now()
mes_actual_str = hoy.strftime("%Y-%m")
primer_dia_mes = hoy.replace(day=1).date()

# --- LOGIN (Solo dfuentes) ---
users = {"dfuentes": "Pastordf2026**"}

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("⛪ Acceso Ministerios Vida")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if u in users and users[u] == p:
            st.session_state['logged_in'] = True
            st.session_state['user_role'] = u
            st.rerun()
        else:
            st.error("Error de acceso")
else:
    # Sidebar
    if os.path.exists("logo.jpg"):
        st.sidebar.image("logo.jpg", use_container_width=True)
    
    st.sidebar.title("Menú Principal")
    menu = st.sidebar.radio("Ir a:", ["📊 Panel", "🕊️ Diezmos", "💰 Ofrendas y Gastos", "👥 Asistencia", "📅 Actividades"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state['logged_in'] = False
        st.rerun()

    # 1. PANEL (CON CORRECCIÓN DE KEYERROR)
    if menu == "📊 Panel":
        st.title(f"Resumen Mensual: {hoy.strftime('%B %Y')}")
        
        df_f = cargar_datos(Finanza)
        df_d = cargar_datos(Diezmo)
        
        # Procesar Ofrendas/Gastos
        ing, gas = 0.0, 0.0
        if not df_f.empty:
            df_f['fecha_dt'] = pd.to_datetime(df_f['fecha']).dt.date
            df_mes_f = df_f[df_f['fecha_dt'] >= primer_dia_mes]
            ing = df_mes_f[df_mes_f['tipo'] == 'Ingreso']['monto'].sum()
            gas = df_mes_f[df_mes_f['tipo'] == 'Gasto']['monto'].sum()

        # Procesar Diezmos (Evitando el error de columna faltante)
        diez_p = 0.0
        if not df_d.empty:
            df_mes_d = df_d[df_d['mes_contable'] == mes_actual_str]
            if not df_mes_d.empty:
                # Si la columna 'estado' no existe en el DataFrame actual, sumamos todo como pendiente
                if 'estado' in df_mes_d.columns:
                    diez_p = df_mes_d[df_mes_d['estado'] == 'Pendiente']['monto'].sum()
                else:
                    diez_p = df_mes_d['monto'].sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ofrendas Mes", f"${ing:,.2f}")
        c2.metric("Gastos Mes", f"${gas:,.2f}")
        c3.metric("Diezmos Pend.", f"${diez_p:,.2f}")
        c4.metric("Saldo Real", f"${(ing - gas) + diez_p:,.2f}")

        st.divider()
        if not df_f.empty:
            fig = px.pie(df_f[pd.to_datetime(df_f['fecha']).dt.date >= primer_dia_mes], 
                         values='monto', names='categoria', title="Gastos/Ingresos por Categoría")
            st.plotly_chart(fig, use_container_width=True)

    # 2. DIEZMOS
    elif menu == "🕊️ Diezmos":
        st.header("Gestión de Diezmos")
        t1, t2 = st.tabs(["📥 Registro", "📊 Cierre"])
        with t1:
            with st.form("d_f", clear_on_submit=True):
                dfec = st.date_input("Fecha", hoy)
                dnom = st.text_input("Miembro")
                dmon = st.number_input("Monto", 0.0)
                if st.form_submit_button("Guardar"):
                    db = SessionLocal()
                    nuevo = Diezmo(fecha=dfec, miembro_nombre=dnom, monto=dmon, 
                                   mes_contable=dfec.strftime("%Y-%m"), estado="Pendiente")
                    db.add(nuevo); db.commit(); db.close()
                    st.success("Guardado")
        with t2:
            df_d = cargar_datos(Diezmo)
            if not df_d.empty:
                mes_s = st.selectbox("Mes", df_d['mes_contable'].unique()[::-1])
                res = df_d[df_d['mes_contable'] == mes_s]
                st.dataframe(res, use_container_width=True)
                if 'estado' in res.columns:
                    p_monto = res[res['estado'] == 'Pendiente']['monto'].sum()
                    if p_monto > 0 and st.button(f"Liquidar ${p_monto:,.2f}"):
                        db = SessionLocal()
                        db.execute(text(f"UPDATE diezmos SET estado = 'Entregado' WHERE mes_contable = '{mes_s}' AND estado = 'Pendiente'"))
                        db.commit(); db.close()
                        st.rerun()

    # 3. OFRENDAS Y GASTOS
    elif menu == "💰 Ofrendas y Gastos":
        st.header("Ofrendas y Gastos")
        t1, t2 = st.tabs(["➕ Nuevo", "📋 Historial"])
        with t1:
            tipo = st.radio("Tipo", ["Ingreso", "Gasto"], horizontal=True)
            with st.form("f_f"):
                f = st.date_input("Fecha")
                c = st.selectbox("Categoría", ["Ofrendas", "Otros"] if tipo=="Ingreso" else ["Renta", "Luz", "Agua", "Otros"])
                m = st.number_input("Monto", 0.0)
                if st.form_submit_button("Guardar"):
                    db = SessionLocal()
                    db.add(Finanza(fecha=str(f), tipo=tipo, categoria=c, monto=m, usuario="dfuentes"))
                    db.commit(); db.close()
                    st.success("Guardado")
        with t2:
            df = cargar_datos(Finanza)
            if not df.empty:
                st.dataframe(df.sort_values("fecha", ascending=False), use_container_width=True)

    # 4. ASISTENCIA
    elif menu == "👥 Asistencia":
        st.header("Asistencia")
        with st.form("a_f"):
            f = st.date_input("Fecha")
            s = st.selectbox("Servicio", ["Dominical", "Oración", "Estudio"])
            h = st.number_input("H", 0); m = st.number_input("M", 0); n = st.number_input("N", 0)
            if st.form_submit_button("Guardar"):
                db = SessionLocal()
                db.add(Asistencia(fecha=str(f), servicio=s, hombres=h, mujeres=m, ninos=n))
                db.commit(); db.close()
                st.success("Registrado")
        df_a = cargar_datos(Asistencia)
        if not df_a.empty: st.dataframe(df_a, use_container_width=True)

    # 5. ACTIVIDADES
    elif menu == "📅 Actividades":
        st.header("Actividades")
        with st.form("ac_f"):
            f = st.date_input("Fecha")
            n = st.text_input("Actividad")
            e = st.text_input("Líder")
            if st.form_submit_button("Guardar"):
                db = SessionLocal()
                db.add(Actividad(fecha=str(f), nombre=n, encargado=e))
                db.commit(); db.close()
                st.success("Programado")
        df_ac = cargar_datos(Actividad)
        if not df_ac.empty: st.table(df_ac)