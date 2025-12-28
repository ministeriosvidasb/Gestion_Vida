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

# --- FUNCIONES PDF CON LOGO (PUNTO 5) ---
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
    
    # Encabezados de tabla
    cols = ["Fecha", "Tipo", "Categoria", "Monto", "Nota"]
    anchos = [30, 30, 40, 30, 60] # Ajuste de anchos
    
    for i, col in enumerate(cols):
        pdf.cell(anchos[i], 10, col, 1, 0, 'C')
    pdf.ln()
    
    # Datos
    for index, row in df.iterrows():
        pdf.cell(anchos[0], 10, str(row['fecha']), 1)
        pdf.cell(anchos[1], 10, str(row['tipo']), 1)
        # Decodificar texto para caracteres especiales
        cat_str = str(row['categoria']).encode('latin-1', 'replace').decode('latin-1')
        nota_str = str(row['nota']).encode('latin-1', 'replace').decode('latin-1')
        
        pdf.cell(anchos[2], 10, cat_str[:18], 1)
        pdf.cell(anchos[3], 10, f"${row['monto']}", 1)
        pdf.cell(anchos[4], 10, nota_str[:30], 1)
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
    st.sidebar.warning("Sube un archivo llamado 'logo.jpg' a la carpeta.")

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

    # 1. PANEL (CON GRÁFICOS RESTAURADOS - PUNTO 1)
    if menu == "📊 Panel":
        st.title("Panel de Control")
        df_fin = cargar_datos("finanzas")
        
        if not df_fin.empty:
            # Métricas
            ing = df_fin[df_fin['tipo'] == 'Ingreso']['monto'].sum()
            gas = df_fin[df_fin['tipo'] == 'Gasto']['monto'].sum()
            col1, col2, col3 = st.columns(3)
            col1.metric("Ingresos Totales", f"${ing:,.2f}")
            col2.metric("Gastos Totales", f"${gas:,.2f}")
            col3.metric("Caja Actual", f"${ing - gas:,.2f}", delta_color="normal")
            
            st.divider()
            
            # GRÁFICOS (PUNTO 1: Restaurados)
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
            st.info("Aún no hay datos registrados para mostrar gráficos.")

    # 2. FINANZAS (CON BOTÓN ELIMINAR Y VISTA ARCHIVOS - PUNTOS 2 y 3)
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
                f_archivo = st.file_uploader("Adjuntar Comprobante (Imagen o PDF)", type=['png', 'jpg', 'jpeg', 'pdf'])
                
                submitted = st.form_submit_button("💾 Guardar Registro", use_container_width=True)
                
                if submitted:
                    f_nombre_archivo = f_archivo.name if f_archivo else None
                    guardar_finanza(f_fecha, f_tipo, f_cat, f_monto, f_nota, st.session_state['user_role'], f_archivo, f_nombre_archivo)
                    st.success("¡Registro guardado exitosamente!")

        with pestana2:
            st.subheader("Historial de Movimientos")
            df = cargar_datos("finanzas")
            
            if not df.empty:
                # Ordenar por fecha descendente
                df = df.sort_values(by='fecha', ascending=False)
                
                # Encabezados de la lista
                col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns([2, 2, 3, 2, 1])
                col_h1.markdown("**Fecha**")
                col_h2.markdown("**Tipo/Cat**")
                col_h3.markdown("**Detalle/Evidencia**") # PUNTO 3
                col_h4.markdown("**Monto**")
                col_h5.markdown("**Acción**") # PUNTO 2
                
                st.divider()

                # Loop para crear filas personalizadas
                for index, row in df.iterrows():
                    c1, c2, c3, c4, c5 = st.columns([2, 2, 3, 2, 1])
                    
                    with c1:
                        st.write(row['fecha'])
                    
                    with c2:
                        color = "🟢" if row['tipo'] == "Ingreso" else "🔴"
                        st.write(f"{color} {row['categoria']}")
                    
                    with c3:
                        st.caption(row['nota'])
                        # PUNTO 3: Visualizar adjuntos
                        if row['evidencia']:
                            file_name = row['nombre_archivo'] if row['nombre_archivo'] else "archivo"
                            if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                                # Es imagen, mostrar miniatura
                                try:
                                    image = Image.open(io.BytesIO(row['evidencia']))
                                    st.image(image, width=100)
                                except:
                                    st.error("Error img")
                            else:
                                # Es PDF u otro, botón descarga
                                st.download_button(label="📎 Ver Doc", 
                                                   data=row['evidencia'], 
                                                   file_name=file_name,
                                                   key=f"dl_{row['rowid']}")
                    
                    with c4:
                        st.write(f"**${row['monto']:,.2f}**")
                    
                    with c5:
                        # PUNTO 2: Botón eliminar en lugar de selectbox
                        if st.button("🗑️", key=f"del_{row['rowid']}", help="Eliminar registro permanentemente"):
                            eliminar_registro("finanzas", row['rowid'])
                            st.rerun()
                    
                    st.markdown("---") # Separador entre filas
            else:
                st.info("No hay registros en la base de datos.")

    # 3. ASISTENCIA (CON NUEVOS SERVICIOS Y OBSERVACIONES - PUNTO 4)
    elif menu == "👥 Asistencia":
        st.header("Registro de Asistencia")
        
        with st.form("form_asistencia", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                a_fecha = st.date_input("Fecha")
                # PUNTO 4: Lista exacta de servicios
                servicios_lista = [
                    "Culto Dominical", 
                    "Lunes de Oración", 
                    "Estudio Biblico", 
                    "Vigilia", 
                    "Otras Actividades Especiales"
                ]
                a_serv = st.selectbox("Servicio", servicios_lista)
            
            with col2:
                h = st.number_input("Hombres", min_value=0)
                m = st.number_input("Mujeres", min_value=0)
                n = st.number_input("Niños", min_value=0)
            
            # PUNTO 4: Campo observaciones
            a_nota = st.text_area("Observaciones", placeholder="Ej: Hubo invitados especiales, clima lluvioso, etc.")
            
            total = h + m + n
            st.write(f"**Total Asistentes: {total}**")
            
            submitted_a = st.form_submit_button("💾 Guardar Asistencia", use_container_width=True)
            
            if submitted_a:
                guardar_asistencia(a_fecha, a_serv, h, m, n, a_nota)
                st.success("Asistencia guardada correctamente.")

        # Tabla rápida de historial asistencias
        st.divider()
        st.subheader("Últimas Asistencias")
        df_asis = cargar_datos("asistencia")
        if not df_asis.empty:
            df_asis['Total'] = df_asis['hombres'] + df_asis['mujeres'] + df_asis['ninos']
            st.dataframe(df_asis[['fecha', 'servicio', 'Total', 'nota']].sort_values(by='fecha', ascending=False).head(5))

    # 4. REPORTES
    elif menu == "📂 Reportes":
        st.header("Generar Reportes PDF")
        df = cargar_datos("finanzas")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.info("El reporte incluirá el logo si 'logo.jpg' está en la carpeta del proyecto.")
            
        with col2:
            if not df.empty:
                if st.button("📄 Generar PDF de Finanzas", type="primary"):
                    pdf_bytes = generar_pdf_finanzas(df)
                    st.download_button(
                        label="⬇️ Descargar Reporte PDF",
                        data=pdf_bytes,
                        file_name=f"Reporte_Finanzas_{datetime.now().strftime('%Y-%m-%d')}.pdf",
                        mime="application/pdf"
                    )
            else:
                st.warning("No hay datos para generar reporte.")