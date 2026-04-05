import streamlit as st
import pandas as pd
from datetime import datetime
import io
import os
from fpdf import FPDF
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, LargeBinary, text
from sqlalchemy.orm import sessionmaker, declarative_base

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Ministerios Vida", layout="wide", page_icon="✝️")

# Diccionario para meses en español
MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

try:
    DATABASE_URL = st.secrets["connections"]["postgresql"]["url"]
except:
    st.error("Configura DATABASE_URL en Secrets.")
    st.stop()

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELOS ---
class Finanza(Base):
    __tablename__ = "finanzas"
    id = Column(Integer, primary_key=True)
    fecha = Column(String)
    tipo = Column(String)
    categoria = Column(String)
    monto = Column(Float)
    nota = Column(String)
    usuario = Column(String)

class Diezmo(Base):
    __tablename__ = "diezmos"
    id = Column(Integer, primary_key=True)
    fecha = Column(Date)
    miembro_nombre = Column(String)
    monto = Column(Float)
    mes_contable = Column(String)
    estado = Column(String, default="Pendiente")

class Cobertura(Base):
    __tablename__ = "cobertura"
    id = Column(Integer, primary_key=True)
    fecha = Column(Date)
    mes_correspondiente = Column(String)
    monto_pagado = Column(Float)
    comprobante_n = Column(String)

class Asistencia(Base):
    __tablename__ = "asistencia"
    id = Column(Integer, primary_key=True)
    fecha = Column(String)
    servicio = Column(String)
    hombres = Column(Integer)
    mujeres = Column(Integer)
    ninos = Column(Integer)

class Actividad(Base):
    __tablename__ = "actividades"
    id = Column(Integer, primary_key=True)
    fecha = Column(String)
    nombre = Column(String)
    encargado = Column(String)

Base.metadata.create_all(bind=engine)

# --- FUNCIONES ---
def cargar_datos(modelo_class):
    db = SessionLocal()
    try:
        query = db.query(modelo_class).statement
        df = pd.read_sql(query, db.bind)
        return df
    except:
        return pd.DataFrame()
    finally:
        db.close()

class IglesiaPDF(FPDF):
    def header(self):
        if os.path.exists("logo.jpg"):
            self.image("logo.jpg", 10, 8, 30)
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'MINISTERIOS VIDA', 0, 1, 'C')
        self.ln(15)

    def tabla_datos(self, titulo, headers, data, anchos):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, titulo.upper(), 0, 1, 'L')
        self.set_font('Arial', 'B', 10)
        for i, h in enumerate(headers):
            self.cell(anchos[i], 7, h, 1, 0, 'C')
        self.ln()
        self.set_font('Arial', '', 9)
        for row in data:
            for i, item in enumerate(row):
                self.cell(anchos[i], 7, str(item), 1)
            self.ln()

# --- LOGIN ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("⛪ Acceso Ministerios Vida")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if u == "dfuentes" and p == "Pastordf2026**":
            st.session_state['logged_in'] = True
            st.rerun()
        else: st.error("Acceso denegado")
else:
    if os.path.exists("logo.jpg"): st.sidebar.image("logo.jpg")
    menu = st.sidebar.radio("Navegación", ["📊 Panel", "🕊️ Diezmos Recibidos", "🛡️ Diezmo a Misión", "💰 Ofrendas y Gastos", "👥 Asistencia", "📅 Actividades", "📂 Reportes PDF"])
    
    hoy = datetime.now()
    nombre_mes_actual = MESES_ES[hoy.month]
    mes_actual_idx = hoy.strftime("%Y-%m")

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state['logged_in'] = False
        st.rerun()

    # 1. PANEL
    if menu == "📊 Panel":
        st.title(f"Resumen de {nombre_mes_actual} {hoy.year}")
        df_f = cargar_datos(Finanza)
        df_d = cargar_datos(Diezmo)
        df_c = cargar_datos(Cobertura)

        col1, col2, col3, col4 = st.columns(4)
        
        o_mes = 0.0; g_mes = 0.0; d_mes = 0.0; c_mes = 0.0
        
        if not df_f.empty:
            df_f['mes'] = pd.to_datetime(df_f['fecha']).dt.strftime('%Y-%m')
            o_mes = df_f[(df_f['tipo'] == 'Ingreso') & (df_f['mes'] == mes_actual_idx)]['monto'].sum()
            g_mes = df_f[(df_f['tipo'] == 'Gasto') & (df_f['mes'] == mes_actual_idx)]['monto'].sum()
        
        if not df_d.empty:
            d_mes = df_d[df_d['mes_contable'] == mes_actual_idx]['monto'].sum()
        
        if not df_c.empty:
            c_mes = df_c[df_c['mes_correspondiente'] == mes_actual_idx]['monto_pagado'].sum()

        col1.metric("Ofrendas", f"${o_mes:,.2f}")
        col2.metric("Diezmos", f"${d_mes:,.2f}")
        col3.metric("Gastos", f"${g_mes:,.2f}")
        col4.metric("Saldo Real", f"${(o_mes + d_mes) - (g_mes + c_mes):,.2f}")

    # 2. DIEZMOS RECIBIDOS
    elif menu == "🕊️ Diezmos Recibidos":
        st.header("Diezmos Recibidos")
        with st.form("d_r"):
            c1, c2 = st.columns(2)
            f = c1.date_input("Fecha")
            n = c1.text_input("Miembro")
            m = c2.number_input("Monto", 0.0)
            if st.form_submit_button("Guardar"):
                db = SessionLocal()
                db.add(Diezmo(fecha=f, miembro_nombre=n, monto=m, mes_contable=f.strftime("%Y-%m")))
                db.commit(); db.close(); st.success("Guardado"); st.rerun()
        st.dataframe(cargar_datos(Diezmo), use_container_width=True)

    # 3. DIEZMO A MISIÓN
    elif menu == "🛡️ Diezmo a Misión":
        st.header("Pagos a la Misión (Cobertura)")
        with st.form("d_m"):
            c1, c2 = st.columns(2)
            f = c1.date_input("Fecha de Pago")
            mes_p = c1.selectbox("Mes Correspondiente", [mes_actual_idx])
            m = c2.number_input("Monto", 0.0)
            if st.form_submit_button("Registrar Pago"):
                db = SessionLocal()
                db.add(Cobertura(fecha=f, mes_correspondiente=mes_p, monto_pagado=m))
                db.commit(); db.close(); st.success("Registrado"); st.rerun()
        st.dataframe(cargar_datos(Cobertura), use_container_width=True)

    # 4. OFRENDAS Y GASTOS (CORREGIDO)
    elif menu == "💰 Ofrendas y Gastos":
        st.header("Gestión de Ofrendas y Gastos")
        t1, t2 = st.tabs(["➕ Nuevo", "📋 Historial"])
        with t1:
            with st.form("o_g"):
                tipo = st.radio("Tipo", ["Ingreso", "Gasto"], horizontal=True)
                c1, c2 = st.columns(2)
                f = c1.date_input("Fecha")
                cat = c2.selectbox("Categoría", ["Ofrenda General", "Donación", "Especial"] if tipo=="Ingreso" else ["Luz/Agua", "Renta", "Limpieza", "Otros"])
                m = c1.number_input("Monto", 0.0)
                n = st.text_area("Nota")
                if st.form_submit_button("Guardar"):
                    db = SessionLocal()
                    db.add(Finanza(fecha=str(f), tipo=tipo, categoria=cat, monto=m, nota=n, usuario="dfuentes"))
                    db.commit(); db.close(); st.success("Guardado"); st.rerun()
        with t2:
            df_fin_view = cargar_datos(Finanza)
            if not df_fin_view.empty:
                st.dataframe(df_fin_view.sort_values("fecha", ascending=False), use_container_width=True)
            else: st.info("No hay registros financieros.")

    # 5. ASISTENCIA
    elif menu == "👥 Asistencia":
        st.header("Asistencia")
        with st.form("asis"):
            f = st.date_input("Fecha")
            s = st.selectbox("Servicio", ["Dominical", "Oración", "Estudio"])
            c1, c2, c3 = st.columns(3)
            h = c1.number_input("H", 0); m = c2.number_input("M", 0); n = c3.number_input("N", 0)
            if st.form_submit_button("Guardar"):
                db = SessionLocal()
                db.add(Asistencia(fecha=str(f), servicio=s, hombres=h, mujeres=m, ninos=n))
                db.commit(); db.close(); st.success("Registrado"); st.rerun()
        st.dataframe(cargar_datos(Asistencia), use_container_width=True)

    # 6. ACTIVIDADES
    elif menu == "📅 Actividades":
        st.header("Actividades")
        with st.form("act"):
            f = st.date_input("Fecha")
            nom = st.text_input("Actividad")
            e = st.text_input("Líder")
            if st.form_submit_button("Guardar"):
                db = SessionLocal()
                db.add(Actividad(fecha=str(f), nombre=nom, encargado=e))
                db.commit(); db.close(); st.success("Programado"); st.rerun()
        st.table(cargar_datos(Actividad))

    # 7. REPORTES PDF
    elif menu == "📂 Reportes PDF":
        st.header("Reportes Mensuales")
        col_a, col_b = st.columns(2)
        tipo_rep = col_a.selectbox("Seleccione Reporte", ["Finanzas", "Diezmos Miembros", "Pagos Misión"])
        
        # Generar lista de meses en español para el selector
        lista_meses = []
        for i in range(1, 13): lista_meses.append(f"{MESES_ES[i]} {hoy.year}")
        mes_rep_nom = col_b.selectbox("Seleccione Mes", lista_meses)
        
        if st.button("Generar PDF"):
            # Obtener el índice YYYY-MM del mes seleccionado
            mes_num = [k for k, v in MESES_ES.items() if v == mes_rep_nom.split()[0]][0]
            mes_idx = f"{hoy.year}-{mes_num:02d}"
            
            pdf = IglesiaPDF()
            pdf.add_page()
            
            if tipo_rep == "Finanzas":
                df = cargar_datos(Finanza)
                if not df.empty:
                    df = df[pd.to_datetime(df['fecha']).dt.strftime('%Y-%m') == mes_idx]
                    data = df[['fecha', 'tipo', 'categoria', 'monto']].values.tolist()
                    pdf.tabla_datos(f"Reporte Finanzas - {mes_rep_nom}", ["Fecha", "Tipo", "Cat.", "Monto"], data, [30, 30, 90, 40])
            
            elif tipo_rep == "Diezmos Miembros":
                df = cargar_datos(Diezmo)
                if not df.empty:
                    df = df[df['mes_contable'] == mes_idx]
                    data = df[['fecha', 'miembro_nombre', 'monto']].values.tolist()
                    pdf.tabla_datos(f"Diezmos Recibidos - {mes_rep_nom}", ["Fecha", "Miembro", "Monto"], data, [40, 100, 50])
            
            # Generación y descarga
            try:
                res_pdf = pdf.output(dest='S').encode('latin-1')
                st.download_button(f"Descargar {tipo_rep}", res_pdf, f"{tipo_rep}_{mes_idx}.pdf", "application/pdf")
            except: st.error("No hay datos suficientes para generar este reporte.")