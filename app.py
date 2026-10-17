
import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# CONFIGURACIÓN
st.set_page_config(
    page_title="Dólar Perú",
    page_icon="💵",
    layout="wide"
)

st.title("💵 Dólar Perú")
st.subheader("Consolidador del Tipo de Cambio en el Perú")

st.write(
    "Consulta y compara cotizaciones referenciales "
    "del dólar estadounidense frente al sol peruano."
)

st.info(
    "Las cotizaciones son referenciales. "
    "No representan necesariamente los precios de "
    "compra y venta de bancos o casas de cambio."
)

# CONSULTAR DATOS REALES
@st.cache_data(ttl=3600)
def obtener_cotizaciones():
    resultados = []

    # FUENTE 1
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        respuesta = requests.get(url, timeout=12)
        respuesta.raise_for_status()
        datos = respuesta.json()

        if datos.get("result") == "success":
            tasa = float(datos["rates"]["PEN"])
            resultados.append({
                "Fuente": "ExchangeRate-API",
                "Tipo de cambio": tasa,
                "Fecha": datos.get(
                    "time_last_update_utc", "No disponible"
                )
            })
    except (requests.RequestException, KeyError,
            ValueError, TypeError):
        pass

    # FUENTE 2
    try:
        url = (
            "https://cdn.jsdelivr.net/npm/"
            "@fawazahmed0/currency-api@latest/"
            "v1/currencies/usd.json"
        )
        respuesta = requests.get(url, timeout=12)
        respuesta.raise_for_status()
        datos = respuesta.json()

        tasa = float(datos["usd"]["pen"])

        resultados.append({
            "Fuente": "Currency API",
            "Tipo de cambio": tasa,
            "Fecha": datos.get("date", "No disponible")
        })
    except (requests.RequestException, KeyError,
            ValueError, TypeError):
        pass

    return resultados


if st.button("🔄 Actualizar cotizaciones"):
    obtener_cotizaciones.clear()

cotizaciones = obtener_cotizaciones()

if not cotizaciones:
    st.error(
        "No se pudieron obtener cotizaciones. "
        "Revisa tu conexión o intenta más tarde."
    )
    st.stop()

df = pd.DataFrame(cotizaciones)

# RESUMEN
st.divider()
st.header("📊 Cotización del dólar")

promedio = df["Tipo de cambio"].mean()
minimo = df["Tipo de cambio"].min()
maximo = df["Tipo de cambio"].max()

col1, col2, col3 = st.columns(3)

col1.metric(
    "Promedio referencial",
    f"S/ {promedio:.4f}"
)

col2.metric(
    "Cotización mínima",
    f"S/ {minimo:.4f}"
)

col3.metric(
    "Cotización máxima",
    f"S/ {maximo:.4f}"
)

# TABLA COMPARATIVA
st.divider()
st.header("🏦 Comparación entre fuentes")

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True
)

st.caption(
    "Las diferencias pueden deberse a metodologías "
    "y horarios de actualización distintos."
)

# GRÁFICO
st.header("📈 Gráfico comparativo")

grafico = df.set_index("Fuente")[["Tipo de cambio"]]

st.bar_chart(grafico)

# CONVERSOR
st.divider()
st.header("💱 Conversor de monedas")

col1, col2 = st.columns(2)

with col1:
    cantidad = st.number_input(
        "Ingresa una cantidad",
        min_value=0.0,
        value=100.0,
        step=10.0
    )

with col2:
    operacion = st.selectbox(
        "Selecciona la conversión",
        ["Dólares a soles", "Soles a dólares"]
    )

fuente_elegida = st.selectbox(
    "Fuente de cotización",
    ["Promedio de fuentes"] + df["Fuente"].tolist()
)

if fuente_elegida == "Promedio de fuentes":
    tasa_usada = promedio
else:
    tasa_usada = float(
        df.loc[
            df["Fuente"] == fuente_elegida,
            "Tipo de cambio"
        ].iloc[0]
    )

if operacion == "Dólares a soles":
    resultado = cantidad * tasa_usada
    simbolo = "S/"
else:
    resultado = cantidad / tasa_usada
    simbolo = "US$"

st.success(
    f"Resultado estimado: {simbolo} {resultado:,.2f}"
)

st.caption(
    f"Tipo de cambio utilizado: S/ {tasa_usada:.4f} "
    "por USD. No incluye comisiones ni márgenes."
)

# ANÁLISIS DE FUENTES
st.divider()
st.header("🔍 Análisis de cotizaciones")

diferencia = maximo - minimo

st.write(
    f"La diferencia entre las cotizaciones "
    f"disponibles es de S/ {diferencia:.4f} "
    "por dólar."
)

st.write(
    "Este consolidador permite consultar información "
    "de distintas fuentes sin visitar cada página "
    "por separado."
)

# INFORMACIÓN FINAL
st.divider()
st.header("ℹ️ Acerca de la aplicación")

st.write(
    "Dólar Perú es una herramienta informativa "
    "que consolida cotizaciones referenciales "
    "del dólar estadounidense frente al sol peruano."
)

st.write(
    "Su objetivo es facilitar la comparación "
    "de información cambiaria y apoyar "
    "la planificación financiera."
)

st.caption(
    "Proyecto académico desarrollado con "
    "Python, Streamlit y GitHub."
)

st.caption(
    "Consulta realizada: "
    + datetime.now().strftime("%d/%m/%Y %H:%M:%S")
)
