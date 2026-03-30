import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date
import json
import plotly.express as px

# ─── CONFIG ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sembra - Ventas",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── ESTILOS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.sembra-header {
    background: #2C1A0E;
    padding: 18px 32px;
    border-radius: 14px;
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.sembra-title {
    font-family: 'Playfair Display', serif;
    color: #D4A96A;
    font-size: 28px;
    margin: 0;
}

.kpi-box {
    background: #FAF6EE;
    border: 1px solid rgba(44,26,14,0.12);
    border-radius: 14px;
    padding: 20px;
    text-align: center;
}
.kpi-value {
    font-family: 'Playfair Display', serif;
    font-size: 28px;
    color: #C07D3A;
    display: block;
    margin-bottom: 4px;
}
.kpi-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: #6B3A1F;
    opacity: 0.7;
}

.stButton > button {
    background: #C07D3A !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
}
.stButton > button:hover {
    background: #6B3A1F !important;
}

.tag {
    display: inline-block;
    background: #F5EFE2;
    border: 1px solid rgba(44,26,14,0.15);
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 13px;
    margin: 3px;
    color: #2C1A0E;
}
</style>
""", unsafe_allow_html=True)

# ─── GOOGLE SHEETS ───────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
SHEET_NAME = "Ventas"
CONFIG_SHEET = "Config"
HEADERS = ["Fecha", "Cliente", "Tipo", "Variedad/Origen", "Presentación",
           "Cantidad", "Precio unitario", "Total", "Canal", "Pago", "Ciudad", "Notas"]

@st.cache_resource
def get_client():
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def get_sheet(name):
    gc = get_client()
    sh = gc.open(st.secrets["sheet_name"])
    try:
        return sh.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=name, rows=1000, cols=20)
        return ws

def cargar_ventas():
    ws = get_sheet(SHEET_NAME)
    data = ws.get_all_records()
    if not data:
        return pd.DataFrame(columns=HEADERS)
    df = pd.DataFrame(data)
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    return df

def guardar_venta(row: list):
    ws = get_sheet(SHEET_NAME)
    if ws.row_count == 0 or ws.cell(1, 1).value != "Fecha":
        ws.insert_row(HEADERS, 1)
    ws.append_row(row)
    st.cache_data.clear()

def cargar_config():
    defaults = {
        "variedades": ["Castillo Natural - Andes", "Variedad 2000 Lavado - Andes", "Geisha Lavado - Andes"],
        "tipos": ["Molido", "En grano"],
        "presentaciones": ["250g", "500g"],
        "canales": ["WhatsApp", "Instagram", "Facebook", "Presencial", "Otro"],
        "pagos": ["Efectivo", "Transferencia", "Otro"]
    }
    try:
        ws = get_sheet(CONFIG_SHEET)
        data = ws.get_all_records()
        if not data:
            return defaults
        cfg = {}
        for row in data:
            key = row.get("campo", "")
            val = row.get("opciones", "")
            if key and val:
                cfg[key] = [v.strip() for v in str(val).split(",") if v.strip()]
        return {k: cfg.get(k, defaults[k]) for k in defaults}
    except Exception:
        return defaults

def guardar_config(cfg: dict):
    ws = get_sheet(CONFIG_SHEET)
    ws.clear()
    ws.append_row(["campo", "opciones"])
    for key, vals in cfg.items():
        ws.append_row([key, ", ".join(vals)])

# ─── ESTADO ──────────────────────────────────────────────────────────────────
if "config" not in st.session_state:
    st.session_state.config = cargar_config()

cfg = st.session_state.config

# ─── HEADER ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="sembra-header">
    <span style="font-size:36px">☕</span>
    <p class="sembra-title">Sembra · Registro de ventas</p>
</div>
""", unsafe_allow_html=True)

# ─── TABS ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📦 Registrar venta", "📋 Mis ventas", "📊 Resumen", "⚙️ Configuración"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — REGISTRAR VENTA
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### Nueva venta")

    with st.form("form_venta", clear_on_submit=True):
        c1, c2 = st.columns(2)

        with c1:
            tipo = st.selectbox("Tipo de café *", cfg["tipos"])
            variedad = st.selectbox("Variedad / origen *", cfg["variedades"])
            presentacion = st.selectbox("Presentación *", cfg["presentaciones"])
            cantidad = st.number_input("Cantidad *", min_value=1, value=1, step=1)

        with c2:
            precio = st.number_input("Precio unitario (COP) *", min_value=0, step=500, value=)
            total = precio * cantidad
            st.markdown(f"""
            <div style="background:#2C1A0E;border-radius:12px;padding:14px 20px;text-align:center;margin-top:8px">
                <div style="font-size:11px;color:#D4A96A;opacity:0.7;margin-bottom:2px;">TOTAL VENTA</div>
                <div style="font-family:'Playfair Display',serif;font-size:28px;color:#C07D3A;">
                    $ {total:,.0f}
                </div>
            </div>
            """, unsafe_allow_html=True)
            cliente = st.text_input("Cliente *")
            ciudad = st.text_input("Ciudad / envío")

        c3, c4 = st.columns(2)
        with c3:
            canal = st.selectbox("Canal de venta *", cfg["canales"])
            pago = st.selectbox("Método de pago *", cfg["pagos"])
        with c4:
            fecha = st.date_input("Fecha *", value=date.today())
            notas = st.text_area("Notas (opcional)", height=80)

        submitted = st.form_submit_button("📦 Registrar venta", use_container_width=True)

        if submitted:
            if not cliente:
                st.error("Por favor completa todos los campos obligatorios.")
            elif precio == 0:
                st.error("El precio no puede ser cero.")
            else:
                row = [
                    str(fecha), cliente, tipo, variedad, presentacion,
                    cantidad, precio, total, canal, pago, ciudad, notas
                ]
                try:
                    guardar_venta(row)
                    st.success(f"✅ Venta registrada — ${total:,.0f} COP")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — MIS VENTAS
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Ventas registradas")

    try:
        df = cargar_ventas()

        if df.empty:
            st.info("Aún no hay ventas registradas.")
        else:
            # Filtros
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                meses_disp = ["Todos"] + sorted(
                    df["Fecha"].dropna().dt.strftime("%Y-%m").unique().tolist(), reverse=True
                ) if "Fecha" in df.columns else ["Todos"]
                mes_fil = st.selectbox("Mes", meses_disp)
            with fc2:
                tipo_fil = st.selectbox("Tipo", ["Todos"] + cfg["tipos"])
            with fc3:
                cliente_fil = st.text_input("Buscar cliente")

            dff = df.copy()
            if mes_fil != "Todos" and "Fecha" in dff.columns:
                dff = dff[dff["Fecha"].dt.strftime("%Y-%m") == mes_fil]
            if tipo_fil != "Todos" and "Tipo" in dff.columns:
                dff = dff[dff["Tipo"] == tipo_fil]
            if cliente_fil and "Cliente" in dff.columns:
                dff = dff[dff["Cliente"].str.contains(cliente_fil, case=False, na=False)]

            # Tabla
            cols_show = [c for c in HEADERS if c in dff.columns]
            st.dataframe(
                dff[cols_show].sort_values("Fecha", ascending=False) if "Fecha" in dff.columns else dff[cols_show],
                use_container_width=True,
                hide_index=True
            )

            # Export CSV
            csv = dff[cols_show].to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇ Exportar CSV",
                data=csv,
                file_name=f"sembra_ventas_{date.today()}.csv",
                mime="text/csv"
            )
    except Exception as e:
        st.error(f"No se pudo cargar la hoja de ventas: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — RESUMEN
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### Resumen de ventas")

    try:
        df = cargar_ventas()

        if df.empty:
            st.info("Aún no hay datos para mostrar.")
        else:
            # Filtro mes
            meses_r = ["Todos"] + sorted(
                df["Fecha"].dropna().dt.strftime("%Y-%m").unique().tolist(), reverse=True
            ) if "Fecha" in df.columns else ["Todos"]
            mes_r = st.selectbox("Filtrar por mes", meses_r, key="res_mes")

            dfr = df.copy()
            if mes_r != "Todos" and "Fecha" in dfr.columns:
                dfr = dfr[dfr["Fecha"].dt.strftime("%Y-%m") == mes_r]

            total_col = "Total" if "Total" in dfr.columns else None
            cant_col  = "Cantidad" if "Cantidad" in dfr.columns else None

            total_ing   = dfr[total_col].sum() if total_col else 0
            num_ventas  = len(dfr)
            total_units = dfr[cant_col].sum() if cant_col else 0
            ticket_prom = total_ing / num_ventas if num_ventas else 0

            # KPIs
            k1, k2, k3, k4 = st.columns(4)
            for col, val, label in [
                (k1, f"${total_ing:,.0f}", "Ingresos totales"),
                (k2, str(num_ventas), "Ventas"),
                (k3, str(int(total_units)), "Unidades vendidas"),
                (k4, f"${ticket_prom:,.0f}", "Ticket promedio"),
            ]:
                col.markdown(f"""
                <div class="kpi-box">
                    <span class="kpi-value">{val}</span>
                    <span class="kpi-label">{label}</span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")

            # Gráficas
            COLORS = ["#C07D3A", "#6B3A1F", "#D4A96A", "#2C1A0E", "#F5EFE2"]

            g1, g2 = st.columns(2)
            with g1:
                if "Canal" in dfr.columns and total_col:
                    canal_df = dfr.groupby("Canal")[total_col].sum().reset_index().sort_values(total_col, ascending=True)
                    fig = px.bar(canal_df, x=total_col, y="Canal", orientation="h",
                                 title="Ventas por canal", color_discrete_sequence=COLORS)
                    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                      font_family="DM Sans", title_font_family="Playfair Display",
                                      showlegend=False, margin=dict(l=0,r=0,t=40,b=0))
                    st.plotly_chart(fig, use_container_width=True)

            with g2:
                if "Variedad" in dfr.columns and total_col:
                    var_df = dfr.groupby("Variedad")[total_col].sum().reset_index().sort_values(total_col, ascending=True)
                    fig2 = px.bar(var_df, x=total_col, y="Variedad", orientation="h",
                                  title="Ventas por variedad", color_discrete_sequence=COLORS)
                    fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                       font_family="DM Sans", title_font_family="Playfair Display",
                                       showlegend=False, margin=dict(l=0,r=0,t=40,b=0))
                    st.plotly_chart(fig2, use_container_width=True)

            g3, g4 = st.columns(2)
            with g3:
                if "Pago" in dfr.columns and total_col:
                    pago_df = dfr.groupby("Pago")[total_col].sum().reset_index()
                    fig3 = px.pie(pago_df, values=total_col, names="Pago",
                                  title="Por método de pago", color_discrete_sequence=COLORS,
                                  hole=0.45)
                    fig3.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                       font_family="DM Sans", title_font_family="Playfair Display",
                                       margin=dict(l=0,r=0,t=40,b=0))
                    st.plotly_chart(fig3, use_container_width=True)

            with g4:
                if "Fecha" in dfr.columns and total_col:
                    dfr["Mes"] = dfr["Fecha"].dt.strftime("%Y-%m")
                    mes_df = dfr.groupby("Mes")[total_col].sum().reset_index().sort_values("Mes")
                    fig4 = px.line(mes_df, x="Mes", y=total_col, title="Ingresos por mes",
                                   color_discrete_sequence=[COLORS[0]], markers=True)
                    fig4.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                       font_family="DM Sans", title_font_family="Playfair Display",
                                       showlegend=False, margin=dict(l=0,r=0,t=40,b=0))
                    st.plotly_chart(fig4, use_container_width=True)

    except Exception as e:
        st.error(f"Error al cargar resumen: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### Configuración de campos")
    st.caption("Agrega o elimina opciones de los campos del formulario. Los cambios se guardan en Google Sheets.")

    campos = {
        "variedades":     ("☕ Variedades de café", "ej. Geisha, Pink Bourbon..."),
        "tipos":          ("🫘 Tipos de café",      "ej. Cold Brew, Espresso..."),
        "presentaciones": ("📦 Presentaciones",     "ej. 125g, 1kg..."),
        "canales":        ("📣 Canales de venta",   "ej. TikTok, Mercado Libre..."),
        "pagos":          ("💳 Métodos de pago",    "ej. PSE, Tarjeta..."),
    }

    cfg_editado = {k: list(v) for k, v in cfg.items()}
    changed = False

    for key, (titulo, placeholder) in campos.items():
        st.markdown(f"**{titulo}**")
        opciones = cfg_editado[key]

        # Mostrar tags actuales
        tags_html = "".join([f'<span class="tag">{o}</span>' for o in opciones])
        st.markdown(tags_html, unsafe_allow_html=True)

        col_input, col_btn, col_del = st.columns([3, 1, 2])
        with col_input:
            nueva = st.text_input("", placeholder=placeholder, key=f"input_{key}", label_visibility="collapsed")
        with col_btn:
            if st.button("+ Agregar", key=f"add_{key}"):
                if nueva and nueva not in opciones:
                    cfg_editado[key].append(nueva)
                    changed = True
        with col_del:
            if opciones:
                eliminar = st.selectbox("Eliminar", ["— selecciona —"] + opciones, key=f"del_{key}", label_visibility="collapsed")
                if eliminar != "— selecciona —":
                    if st.button("🗑 Quitar", key=f"rm_{key}"):
                        cfg_editado[key].remove(eliminar)
                        changed = True

        st.markdown("---")

    if changed:
        try:
            guardar_config(cfg_editado)
            st.session_state.config = cfg_editado
            st.success("✅ Configuración guardada")
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar configuración: {e}")
