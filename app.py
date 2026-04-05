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
    tipo = Column(String) # Ingreso / Gasto
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

Base.metadata.create_all(bind=engine)

# --- FUNCIONES DE APOYO ---
def cargar_datos(modelo_class):
    db = SessionLocal()
    try:
        query = db.query(modelo_class).statement
        return pd.read_sql(query, db.bind)
    except: return pd.DataFrame()
    finally: db.close()

# --- CLASE PDF PROFESIONAL ---
class IglesiaPDF(FPDF):
    def header(self):
        if os.path.exists("logo.jpg"):
            self.image("logo.jpg", 10, 8, 30)
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'MINISTERIOS VIDA', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 5, 'Reporte Administrativo Oficial', 0, 1, 'C')
        self.ln(20)

    def tabla_datos(self, titulo, headers, data, anchos):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, titulo, 0, 1, 'L')
        self.set_font('Arial', 'B', 10)
        self.set_fill_color(230, 230, 230)
        for i, h in enumerate(headers):
            self.cell(anchos[i], 7, h, 1, 0, 'C', True)
        self.ln()
        self.set_font('Arial', '', 9)
        for row in data:
            for i, item in enumerate(row):
                self.cell(anchos[i], 7, str(item), 1)
            self.ln()
        self.ln(5)

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
else:
    if os.path.exists("logo.jpg"): st.sidebar.image("logo.jpg")
    menu = st.sidebar.radio("Navegación", ["📊 Panel", "🕊️ Diezmos Recibidos", "🛡️ Diezmo a Misión (Cobertura)", "💰 Ofrendas y Gastos", "📂 Reportes PDF"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state['logged_in'] = False
        st.rerun()

    hoy = datetime.now()
    mes_actual = hoy.strftime("%Y-%m")

    # 1. PANEL
    if menu == "📊 Panel":
        st.title(f"Resumen Mensual: {hoy.strftime('%B %Y')}")
        df_f = cargar_datos(Finanza)
        df_d = cargar_datos(Diezmo)
        df_c = cargar_datos(Cobertura)

        col1, col2, col3, col4 = st.columns(4)
        
        # Cálculos rápidos
        ofrendas = df_f[(df_f['tipo'] == 'Ingreso') & (pd.to_datetime(df_f['fecha']).dt.strftime('%Y-%m') == mes_actual)]['monto'].sum()
        gastos = df_f[(df_f['tipo'] == 'Gasto') & (pd.to_datetime(df_f['fecha']).dt.strftime('%Y-%m') == mes_actual)]['monto'].sum()
        diezmos_r = df_d[df_d['mes_contable'] == mes_actual]['monto'].sum()
        cobertura_p = df_c[df_c['mes_correspondiente'] == mes_actual]['monto_pagado'].sum()

        col1.metric("Ofrendas Mes", f"${ofrendas:,.2f}")
        col2.metric("Diezmos Miembros", f"${diezmos_r:,.2f}")
        col3.metric("Pagado a Misión", f"${cobertura_p:,.2f}")
        col4.metric("Saldo Caja", f"${(ofrendas + diezmos_r) - (gastos + cobertura_p):,.2f}")

    # 2. DIEZMOS RECIBIDOS (MIEMBROS)
    elif menu == "🕊️ Diezmos Recibidos":
        st.header("Diezmos de la Congregación")
        with st.form("f_diezmo"):
            c1, c2 = st.columns(2)
            f = c1.date_input("Fecha")
            n = c1.text_input("Nombre del Miembro")
            m = c2.number_input("Monto", 0.0)
            if st.form_submit_button("Registrar Diezmo"):
                db = SessionLocal()
                db.add(Diezmo(fecha=f, miembro_nombre=n, monto=m, mes_contable=f.strftime("%Y-%m"), estado="Pendiente"))
                db.commit(); db.close()
                st.success("Diezmo guardado")
        st.dataframe(cargar_datos(Diezmo), use_container_width=True)

    # 3. DIEZMO A LA MISIÓN (COBERTURA)
    elif menu == "🛡️ Diezmo a Misión (Cobertura)":
        st.header("Diezmos Enviados a la Misión (Cobertura)")
        st.info("Aquí registramos el 10% (o monto correspondiente) que la iglesia envía a la misión superior.")
        with st.form("f_cobertura"):
            c1, c2 = st.columns(2)
            f_pago = c1.date_input("Fecha de Envío")
            mes_p = c1.selectbox("Mes que se está pagando", [hoy.strftime("%Y-%m"), (hoy.replace(month=hoy.month-1)).strftime("%Y-%m")])
            monto_p = c2.number_input("Monto Enviado", 0.0)
            ref = c2.text_input("Número de Comprobante / Referencia")
            if st.form_submit_button("Registrar Pago a Misión"):
                db = SessionLocal()
                db.add(Cobertura(fecha=f_pago, mes_correspondiente=mes_p, monto_pagado=monto_p, comprobante_n=ref))
                db.commit(); db.close()
                st.success("Pago a cobertura registrado")
        st.dataframe(cargar_datos(Cobertura), use_container_width=True)

    # 4. REPORTES PDF
    elif menu == "📂 Reportes PDF":
        st.header("Centro de Reportes")
        st.write("Seleccione el tipo de reporte y el mes para generar el documento imprimible.")
        
        col_r1, col_r2 = st.columns(2)
        tipo_r = col_r1.selectbox("Tipo de Reporte", ["Finanzas Generales", "Diezmos de Miembros", "Pagos a Cobertura"])
        mes_r = col_r2.selectbox("Mes del Reporte", pd.date_range(end=hoy, periods=12, freq='MS').strftime("%Y-%m"))

        if st.button("Generar Reporte PDF"):
            pdf = IglesiaPDF()
            pdf.add_page()
            
            if tipo_r == "Finanzas Generales":
                df = cargar_datos(Finanza)
                df = df[pd.to_datetime(df['fecha']).dt.strftime('%Y-%m') == mes_r]
                datos = df[['fecha', 'tipo', 'categoria', 'monto']].values.tolist()
                pdf.tabla_datos(f"Reporte de Ofrendas y Gastos - {mes_r}", ["Fecha", "Tipo", "Cat.", "Monto"], datos, [30, 40, 80, 40])
            
            elif tipo_r == "Diezmos de Miembros":
                df = cargar_datos(Diezmo)
                df = df[df['mes_contable'] == mes_r]
                datos = df[['fecha', 'miembro_nombre', 'monto']].values.tolist()
                pdf.tabla_datos(f"Diezmos Recibidos - {mes_r}", ["Fecha", "Miembro", "Monto"], datos, [40, 100, 50])

            elif tipo_r == "Pagos a Cobertura":
                df = cargar_datos(Cobertura)
                df = df[df['mes_correspondiente'] == mes_r]
                datos = df[['fecha', 'monto_pagado', 'comprobante_n']].values.tolist()
                pdf.tabla_datos(f"Pagos Enviados a Misión - {mes_r}", ["Fecha Envío", "Monto", "Referencia"], datos, [40, 60, 90])

            html = pdf.output(dest='S').encode('latin-1')
            st.download_button(f"⬇️ Descargar PDF {tipo_r}", data=html, file_name=f"Reporte_{tipo_r}_{mes_r}.pdf", mime="application/pdf")