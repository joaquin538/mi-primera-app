
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# CONFIGURACIÓN GENERAL
st.set_page_config(
    page_title="Dólar Perú PRO",
    page_icon="💵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# DISEÑO VISUAL
st.markdown("""
<style>
.stApp {
    background: #0B1220;
    color: #F1F5F9;
}

[data-testid="stSidebar"] {
    background: #111D30;
}

h1, h2, h3 {
    color: #F8FAFC !important;
}

.hero {
    padding: 32px;
    border-radius: 20px;
    background: linear-gradient(
        120deg, #123B49, #132239
    );
    border: 1px solid #285266;
    margin-bottom: 25px;
}

.hero h1 {
    font-size: 44px;
    margin-bottom: 8px;
}

.hero p {
    color: #BDCDD9;
    font-size: 17px;
}

.label {
    color: #50E3C2;
    font-weight: bold;
    letter-spacing: 2px;
    font-size: 12px;
}

[data-testid="stMetric"] {
    background: #16263A;
    padding: 20px;
    border-radius: 15px;
    border: 1px solid #2A4358;
}

.stButton > button[kind="primary"] {
    background: #35D6AF;
    color: #061420;
    font-weight: bold;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)


# OBTENER DATOS DE INTERNET
@st.cache_data(ttl=1800)
def obtener_dolar():
    url = "https://open.er-api.com/v6/latest/USD"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()

    if data.get("result") != "success":
        raise ValueError("Respuesta no válida")

    return (
        data["rates"],
        data.get("time_last_update_utc", "No disponible")
    )


@st.cache_data(ttl=3600)
def obtener_historial(dias):
    fecha_final = datetime.now().date()
    fecha_inicio = fecha_final - timedelta(days=dias)

    url = (
        "https://api.frankfurter.dev/v1/"
        f"{fecha_inicio}..{fecha_final}"
    )

    r = requests.get(
        url,
        params={
            "base": "USD",
            "symbols": "PEN"
        },
        timeout=20
    )

    r.raise_for_status()
    datos = r.json()

    registros = []

    for fecha, monedas in datos.get("rates", {}).items():
        if "PEN" in monedas:
            registros.append({
                "Fecha": pd.to_datetime(fecha),
                "Tipo de cambio": float(monedas["PEN"])
            })

    return pd.DataFrame(registros).sort_values(
        "Fecha"
    ) if registros else pd.DataFrame()


# SIDEBAR
with st.sidebar:
    st.title("💵 DÓLAR PERÚ PRO")
    st.caption("CENTRO DE INTELIGENCIA CAMBIARIA")

    st.divider()

    st.markdown("### ⚙️ Configuración")

    periodo = st.selectbox(
        "Período histórico",
        [7, 15, 30, 60, 90, 180, 365],
        index=4,
        format_func=lambda x: f"{x} días"
    )

    if st.button(
        "🔄 Actualizar datos",
        use_container_width=True,
        type="primary"
    ):
        obtener_dolar.clear()
        obtener_historial.clear()
        st.rerun()

    st.divider()

    st.markdown("### 📚 Fuentes")
    st.markdown(
        "[ExchangeRate-API]"
        "(https://www.exchangerate-api.com/)"
    )
    st.markdown(
        "[Frankfurter]"
        "(https://frankfurter.dev/)"
    )
    st.markdown(
        "[BCRP]"
        "(https://www.bcrp.gob.pe/)"
    )

    st.caption(
        "Los valores son referenciales y "
        "no constituyen ofertas comerciales."
    )

    st.divider()
    st.caption("Proyecto académico | Python + Streamlit")


# ENCABEZADO
st.markdown("""
<div class="hero">
    <div class="label">
        ● MERCADO CAMBIARIO · PERÚ
    </div>
    <h1>💵 Dólar Perú PRO</h1>
    <p>
        Información cambiaria en un solo lugar.
        Analiza el dólar, convierte monedas y
        toma decisiones financieras mejor informadas.
    </p>
</div>
""", unsafe_allow_html=True)


# CARGA DE INFORMACIÓN
try:
    monedas, fecha_actualizacion = obtener_dolar()
    dolar = float(monedas["PEN"])
except Exception:
    monedas = None
    dolar = None
    fecha_actualizacion = None

try:
    historial = obtener_historial(periodo)
except Exception:
    historial = pd.DataFrame()

if dolar is None:
    st.error(
        "No se pudo consultar el tipo de cambio. "
        "Intenta actualizar los datos."
    )
    st.stop()


# INDICADORES PRINCIPALES
st.subheader("📊 Resumen del mercado")

anterior = None
variacion = None

if len(historial) >= 2:
    anterior = float(
        historial["Tipo de cambio"].iloc[-2]
    )
    variacion = ((dolar / anterior) - 1) * 100

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "💵 Dólar referencial",
    f"S/ {dolar:.4f}"
)

col2.metric(
    "📈 Variación referencial",
    f"{variacion:+.2f}%" if variacion is not None
    else "No disponible"
)

col3.metric(
    "📉 Mínimo del período",
    f"S/ {historial['Tipo de cambio'].min():.4f}"
    if not historial.empty else "No disponible"
)

col4.metric(
    "📊 Máximo del período",
    f"S/ {historial['Tipo de cambio'].max():.4f}"
    if not historial.empty else "No disponible"
)

st.caption(
    f"Última actualización reportada por la API: "
    f"{fecha_actualizacion}"
)

st.info(
    "La cotización principal es referencial. "
    "El histórico proviene de otra fuente y puede "
    "tener fechas o metodologías diferentes."
)

st.divider()


# NAVEGACIÓN INTERACTIVA
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Evolución del dólar",
    "💸 Simulador de cambio",
    "🌎 Monedas del mundo",
    "📊 Análisis financiero"
])


# PESTAÑA 1: EVOLUCIÓN HISTÓRICA
with tab1:

    st.header("📈 Evolución histórica del dólar")

    st.write(
        "Explora el comportamiento del tipo de cambio "
        "USD/PEN durante el período seleccionado."
    )

    if not historial.empty:

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=historial["Fecha"],
            y=historial["Tipo de cambio"],
            mode="lines",
            name="USD/PEN",
            line=dict(
                color="#35D6AF",
                width=3
            ),
            fill="tozeroy",
            fillcolor="rgba(53,214,175,0.08)",
            hovertemplate=(
                "%{x|%d/%m/%Y}"
                "<br>S/ %{y:.4f}<extra></extra>"
            )
        ))

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#111D30",
            plot_bgcolor="#111D30",
            height=430,
            xaxis_title="Fecha",
            yaxis_title="Soles por dólar",
            hovermode="x unified",
            margin=dict(l=20, r=20, t=30, b=20)
        )

        fig.update_yaxes(
            range=[
                historial["Tipo de cambio"].min() * 0.995,
                historial["Tipo de cambio"].max() * 1.005
            ]
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.subheader("📋 Datos históricos")

        st.dataframe(
            historial.sort_values(
                "Fecha", ascending=False
            ),
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "⬇️ Descargar histórico CSV",
            historial.to_csv(
                index=False
            ).encode("utf-8-sig"),
            file_name="historico_dolar_peru.csv",
            mime="text/csv"
        )

    else:
        st.warning(
            "No hay datos históricos disponibles "
            "en este momento."
        )


# PESTAÑA 2: SIMULADOR
with tab2:

    st.header("💸 Simulador de cambio")

    st.write(
        "Calcula cuánto dinero recibirías al "
        "convertir dólares y soles."
    )

    operacion = st.radio(
        "¿Qué deseas hacer?",
        [
            "Convertir dólares a soles",
            "Convertir soles a dólares"
        ],
        horizontal=True
    )

    cantidad = st.number_input(
        "💰 Cantidad a convertir",
        min_value=0.0,
        value=1000.0,
        step=100.0
    )

    st.markdown("### ⚙️ Ajustes de la operación")

    ajuste = st.slider(
        "Margen adicional de la operación (%)",
        min_value=0.0,
        max_value=5.0,
        value=0.5,
        step=0.1
    )

    comision = st.number_input(
        "Comisión fija estimada (S/)",
        min_value=0.0,
        value=0.0,
        step=1.0
    )

    if operacion == "Convertir dólares a soles":

        tasa_efectiva = dolar * (1 - ajuste / 100)
        bruto = cantidad * tasa_efectiva
        resultado = max(bruto - comision, 0)

        simbolo = "S/"

    else:

        tasa_efectiva = dolar * (1 + ajuste / 100)
        resultado = (
            max(cantidad - comision, 0)
            / tasa_efectiva
        )

        simbolo = "US$"

    st.divider()

    st.markdown("### ✅ Resultado de la simulación")

    c1, c2 = st.columns(2)

    c1.metric(
        "Monto estimado a recibir",
        f"{simbolo} {resultado:,.2f}"
    )

    c2.metric(
        "Tipo de cambio simulado",
        f"S/ {tasa_efectiva:.4f}"
    )

    if st.button(
        "📋 Mostrar detalle",
        type="primary"
    ):

        st.success(
            f"Recibirías aproximadamente "
            f"{simbolo} {resultado:,.2f}"
        )

        st.write(
            f"Tipo de cambio referencial: "
            f"S/ {dolar:.4f}"
        )

        st.write(
            f"Margen supuesto: {ajuste:.2f}%"
        )

        st.write(
            f"Comisión estimada: S/ {comision:.2f}"
        )

    st.caption(
        "Los márgenes y comisiones son supuestos "
        "configurados por el usuario. "
        "No son tarifas reales de una entidad."
    )


# PESTAÑA 3: MONEDAS INTERNACIONALES
with tab3:

    st.header("🌎 Conversor internacional")

    st.write(
        "Compara el valor del sol peruano frente "
        "a 15 monedas de diferentes países."
    )

    catalogo = {
        "USD": "Estados Unidos",
        "EUR": "Zona euro",
        "GBP": "Reino Unido",
        "JPY": "Japón",
        "BRL": "Brasil",
        "MXN": "México",
        "CLP": "Chile",
        "COP": "Colombia",
        "ARS": "Argentina",
        "CAD": "Canadá",
        "CHF": "Suiza",
        "CNY": "China",
        "AUD": "Australia",
        "UYU": "Uruguay",
        "BOB": "Bolivia"
    }

    soles = st.number_input(
        "Cantidad en soles (PEN)",
        min_value=0.0,
        value=1000.0,
        step=100.0,
        key="soles_internacionales"
    )

    registros = []

    for codigo, pais in catalogo.items():

        if codigo in monedas:

            tasa = float(monedas[codigo]) / dolar

            registros.append({
                "País / región": pais,
                "Moneda": codigo,
                "Valor de 1 PEN": round(tasa, 6),
                "Monto convertido": round(
                    soles * tasa, 2
                )
            })

    tabla = pd.DataFrame(registros)

    st.dataframe(
        tabla,
        use_container_width=True,
        hide_index=True
    )

    seleccion = st.selectbox(
        "Selecciona una moneda",
        tabla["Moneda"].tolist()
    )

    registro = tabla[
        tabla["Moneda"] == seleccion
    ].iloc[0]

    st.metric(
        f"Equivalente en {seleccion}",
        f"{registro['Monto convertido']:,.2f} "
        f"{seleccion}"
    )

    st.download_button(
        "⬇️ Descargar comparación CSV",
        tabla.to_csv(
            index=False
        ).encode("utf-8-sig"),
        file_name="monedas_internacionales.csv",
        mime="text/csv"
    )


# PESTAÑA 4: ANÁLISIS FINANCIERO
with tab4:

    st.header("📊 Centro de análisis")

    st.write(
        "Analiza los principales indicadores "
        "del tipo de cambio histórico."
    )

    if not historial.empty:

        valores = historial["Tipo de cambio"]

        promedio = valores.mean()
        minimo = valores.min()
        maximo = valores.max()
        rango = maximo - minimo

        a, b = st.columns(2)

        a.metric(
            "Promedio histórico del período",
            f"S/ {promedio:.4f}"
        )

        b.metric(
            "Rango de variación",
            f"S/ {rango:.4f}"
        )

        st.markdown("### Comparación con el promedio")

        diferencia = dolar - promedio
        porcentaje = diferencia / promedio * 100

        st.metric(
            "Diferencia frente al promedio",
            f"S/ {diferencia:+.4f}",
            f"{porcentaje:+.2f}%"
        )

        if dolar > promedio:
            st.info(
                "La cotización referencial actual "
                "se encuentra por encima del "
                "promedio histórico seleccionado."
            )
        elif dolar < promedio:
            st.info(
                "La cotización referencial actual "
                "se encuentra por debajo del "
                "promedio histórico seleccionado."
            )
        else:
            st.info(
                "La cotización referencial coincide "
                "con el promedio histórico."
            )

        st.warning(
            "Este análisis es descriptivo. "
            "No predice si el dólar subirá o bajará."
        )

    else:
        st.warning(
            "No se dispone de información "
            "histórica para realizar el análisis."
        )


# PIE DE PÁGINA
st.divider()

st.markdown("""
### 💵 Dólar Perú PRO

**Tu centro de información cambiaria.**

Aplicación académica desarrollada con
Python, Streamlit y GitHub.
""")

st.caption(
    "Los datos están sujetos a la disponibilidad "
    "y actualización de los proveedores. "
    "No se realizan transacciones financieras."
)
