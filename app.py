
import math
import re
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# ==========================================
# CONFIGURACION GENERAL
# ==========================================

st.set_page_config(
    page_title="Dolar Peru | Centro cambiario",
    page_icon="💵",
    layout="wide"
)

# ==========================================
# DISENO VISUAL
# ==========================================

st.markdown("""
<style>
:root {
    color-scheme: dark;
}

.stApp {
    background: #091321;
    color: #e8f0fa;
}

[data-testid="stSidebar"] {
    background: #101f31;
}

h1, h2, h3 {
    letter-spacing: -.035em;
}

.hero {
    background: linear-gradient(
        120deg,
        #113748 0%,
        #112137 60%,
        #17203b 100%
    );
    border: 1px solid #2f6371;
    padding: 28px 30px;
    border-radius: 22px;
    margin: 12px 0 24px 0;
}

.eyebrow {
    font-weight: 700;
    letter-spacing: .18em;
    font-size: 12px;
    color: #68e4ca;
}

.hero h1 {
    font-size: clamp(34px,5vw,52px);
    margin: 8px 0 7px;
    line-height: 1.13;
}

.hero p {
    color: #b8cadd;
    margin: 0;
    font-size: 16px;
}

[data-testid="stMetric"] {
    background: #122539;
    border: 1px solid #284254;
    border-radius: 16px;
    padding: 16px 19px;
    min-height: 120px;
}

[data-testid="stMetricValue"] {
    color: #e9fff8;
}

.stButton button[kind="primary"] {
    background: #4bdec0;
    color: #06262c;
    border: 0;
    font-weight: 800;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    flex-wrap: wrap;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    background: #13263a;
    padding: 9px 15px;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# FUENTES Y MONEDAS
# ==========================================

BCRP_CODES = [
    "PD04637PD",
    "PD04638PD",
    "PD04639PD",
    "PD04640PD"
]

COUNTRIES = {
    "EUR": "Euro",
    "GBP": "Libra esterlina",
    "JPY": "Yen japones",
    "BRL": "Real brasileno",
    "CLP": "Peso chileno",
    "COP": "Peso colombiano",
    "MXN": "Peso mexicano",
    "ARS": "Peso argentino",
    "CAD": "Dolar canadiense",
    "CHF": "Franco suizo",
    "CNY": "Yuan chino",
    "AUD": "Dolar australiano",
    "UYU": "Peso uruguayo",
    "BOB": "Boliviano",
    "KRW": "Won surcoreano"
}


# ==========================================
# FUNCIONES DE DATOS
# ==========================================

def positive_number(value):
    try:
        number = float(str(value).replace(",", "."))
        if math.isfinite(number) and number > 0:
            return number
    except (TypeError, ValueError):
        pass
    return None


def get_json(url):
    response = requests.get(
        url,
        timeout=9,
        headers={
            "User-Agent": "DolarPeruAcademico/1.0"
        }
    )
    response.raise_for_status()

    result = response.json()

    if not isinstance(result, dict):
        raise ValueError("Formato JSON inesperado")

    return result


@st.cache_data(ttl=900, show_spinner=False)
def exchange_rates():

    providers = [
        (
            "Currency API (jsDelivr)",
            "https://cdn.jsdelivr.net/npm/"
            "@fawazahmed0/currency-api@latest/"
            "v1/currencies/usd.json",
            "fawaz"
        ),
        (
            "Currency API (Cloudflare)",
            "https://latest.currency-api.pages.dev/"
            "v1/currencies/usd.json",
            "fawaz"
        ),
        (
            "ExchangeRate-API",
            "https://open.er-api.com/v6/latest/USD",
            "er"
        )
    ]

    for source, url, kind in providers:
        try:
            data = get_json(url)

            if kind == "fawaz":
                all_rates = data["usd"]
                day = str(data["date"])

            else:
                if data.get("result") != "success":
                    continue

                all_rates = data["rates"]

                day = data.get(
                    "time_last_update_utc",
                    "Fecha indicada por proveedor"
                )

            rates = {
                str(k).upper(): v
                for k, v in all_rates.items()
            }

            pen = positive_number(
                rates.get("PEN")
            )

            if not pen or not 1 < pen < 15:
                continue

            clean = {
                k: positive_number(v)
                for k, v in rates.items()
            }

            clean = {
                k: v
                for k, v in clean.items()
                if v is not None
            }

            clean["USD"] = 1.0

            return {
                "rates": clean,
                "date": day,
                "source": source
            }

        except (
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError
        ):
            continue

    return None


# ==========================================
# HISTORIAL OFICIAL BCRP
# ==========================================

SPANISH_MONTHS = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "set": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
    "dec": 12
}


def parse_bcrp_date(period):

    text = str(period).strip().lower()

    match = re.match(
        r"^(\d{1,2})[./ -]+"
        r"([a-záéíóú]+|\d{1,2})"
        r"[./ -]+(\d{2,4})$",
        text
    )

    if match:
        day, month, year = match.groups()

        if month.isdigit():
            month = int(month)
        else:
            month = SPANISH_MONTHS.get(
                month[:3]
            )

        year = int(year)

        if year < 100:
            year += 2000 if year <= 69 else 1900

        if month:
            try:
                return date(
                    year,
                    month,
                    int(day)
                )
            except ValueError:
                return None

    parsed = pd.to_datetime(
        period,
        dayfirst=not bool(
            re.match(
                r"^\d{4}-",
                str(period)
            )
        ),
        errors="coerce"
    )

    if pd.isna(parsed):
        return None

    return parsed.date()


@st.cache_data(ttl=1800, show_spinner=False)
def bcrp_history():

    start = (
        date.today() - timedelta(days=380)
    ).isoformat()

    end = date.today().isoformat()

    codes = "-".join(BCRP_CODES)

    url = (
        "https://estadisticas.bcrp.gob.pe/"
        "estadisticas/series/api/"
        f"{codes}/json/{start}/{end}/esp"
    )

    try:
        data = get_json(url)

        entries = data.get(
            "periods", []
        )

        records = []

        for entry in entries:

            day = parse_bcrp_date(
                entry.get("name", "")
            )

            nums = entry.get(
                "values", []
            )

            if not day or len(nums) < 4:
                continue

            record = {
                "Fecha": day
            }

            keys = [
                "Interbancario compra",
                "Interbancario venta",
                "Bancario compra",
                "Bancario venta"
            ]

            for index, key in enumerate(keys):
                record[key] = positive_number(
                    nums[index]
                )

            records.append(record)

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)

        df = df.drop_duplicates(
            subset=["Fecha"]
        ).sort_values("Fecha")

        if len(df) < 2:
            return pd.DataFrame()

        return df.reset_index(drop=True)

    except (
        requests.RequestException,
        ValueError,
        KeyError,
        TypeError
    ):
        return pd.DataFrame()


def official_pair(df, prefix):

    if df.empty:
        return None

    buy = prefix + " compra"
    sell = prefix + " venta"

    if buy not in df.columns:
        return None

    if sell not in df.columns:
        return None

    valid = df.dropna(
        subset=[buy, sell]
    )

    valid = valid[
        (valid[buy] > 0)
        & (valid[sell] > 0)
    ]

    if valid.empty:
        return None

    row = valid.iloc[-1]

    return {
        "compra": float(row[buy]),
        "venta": float(row[sell]),
        "fecha": row["Fecha"]
    }


# ==========================================
# HISTORIAL ALTERNATIVO
# ==========================================

def dated_rate(day):

    d = day.isoformat()

    urls = [
        (
            f"https://{d}.currency-api.pages.dev/"
            "v1/currencies/usd.json"
        ),
        (
            "https://cdn.jsdelivr.net/npm/"
            f"@fawazahmed0/currency-api@{d}/"
            "v1/currencies/usd.json"
        )
    ]

    for url in urls:
        try:
            data = get_json(url)

            rate = positive_number(
                data["usd"]["pen"]
            )

            if rate and 1 < rate < 15:
                return (
                    str(data.get("date", d)),
                    rate
                )

        except (
            requests.RequestException,
            ValueError,
            TypeError,
            KeyError
        ):
            continue

    return None


@st.cache_data(ttl=3600, show_spinner=False)
def alternative_history(days):

    today = date.today()

    sample_days = sorted({
        today - timedelta(
            days=round(i * days / 9)
        )
        for i in range(10)
    })

    result = {}

    with ThreadPoolExecutor(
        max_workers=5
    ) as executor:

        futures = [
            executor.submit(
                dated_rate, d
            )
            for d in sample_days
        ]

        for future in as_completed(futures):
            try:
                item = future.result()

                if item:
                    fecha = pd.to_datetime(
                        item[0],
                        errors="coerce"
                    )

                    if not pd.isna(fecha):
                        result[fecha.date()] = item[1]

            except Exception:
                pass

    if len(result) < 2:
        return pd.DataFrame()

    return pd.DataFrame([
        {
            "Fecha": d,
            "Referencial": r
        }
        for d, r in sorted(result.items())
    ])


# ==========================================
# FUNCION PARA GRAFICOS
# ==========================================

def plot_lines(frame, columns, title):

    fig = go.Figure()

    colors = [
        "#40d8b6",
        "#f7bb69",
        "#7aa9ff"
    ]

    for i, col in enumerate(columns):

        if (
            col in frame
            and frame[col].notna().any()
        ):

            fig.add_trace(
                go.Scatter(
                    x=frame["Fecha"],
                    y=frame[col],
                    mode="lines+markers",
                    name=col,
                    line={
                        "color": colors[
                            i % len(colors)
                        ],
                        "width": 3
                    },
                    marker={"size": 4},
                    hovertemplate=(
                        "%{x}<br>"
                        "S/ %{y:.4f}"
                        "<extra></extra>"
                    )
                )
            )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=420,
        margin=dict(
            l=10,
            r=10,
            b=15,
            t=55
        ),
        paper_bgcolor="#101f31",
        plot_bgcolor="#101f31",
        xaxis_title="Fecha",
        yaxis_title="Soles por dolar",
        hovermode="x unified",
        legend={
            "orientation": "h",
            "y": 1.13
        }
    )

    fig.update_yaxes(
        autorange=True
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ==========================================
# MENU LATERAL
# ==========================================

with st.sidebar:

    st.title("💵 DOLAR PERU")
    st.caption(
        "CENTRO DE INTELIGENCIA CAMBIARIA"
    )

    st.divider()

    if st.button(
        "🔄 Actualizar fuentes",
        type="primary",
        use_container_width=True
    ):

        exchange_rates.clear()
        bcrp_history.clear()
        alternative_history.clear()

        st.rerun()

    st.markdown("**Fuentes verificables**")

    st.markdown(
        "[BCRPData]"
        "(https://estadisticas.bcrp.gob.pe/"
        "estadisticas/series/diarias/"
        "tipo-de-cambio-nominal)"
    )

    st.markdown(
        "[Currency API]"
        "(https://github.com/"
        "fawazahmed0/exchange-api)"
    )

    st.markdown(
        "[ExchangeRate-API]"
        "(https://www.exchangerate-api.com/)"
    )

    st.divider()

    st.caption(
        "Cotizaciones referenciales y "
        "series estadisticas."
    )

    st.caption(
        "No realizamos compras ni ventas."
    )


# ==========================================
# ENCABEZADO
# ==========================================

st.markdown("""
<div class="hero">
    <div class="eyebrow">
        ● PLATAFORMA FINANCIERA · PERÚ
    </div>
    <h1>
        Dólar Perú
        <span style="color:#53e0bf">
            PRO
        </span>
    </h1>
    <p>
        Consulta datos reales, compara tipos
        de cambio y simula operaciones.
        Todo desde una sola aplicación.
    </p>
</div>
""", unsafe_allow_html=True)


# ==========================================
# CARGAR COTIZACIONES
# ==========================================

with st.spinner(
    "Consultando fuentes cambiarias..."
):

    info = exchange_rates()
    oficial = bcrp_history()


if info is not None:

    st.session_state["last_rate"] = info

elif "last_rate" in st.session_state:

    info = st.session_state["last_rate"]

    st.warning(
        "Mostrando la ultima cotizacion "
        "consultada durante esta sesion."
    )


if not oficial.empty:

    st.session_state["last_bcrp"] = oficial

elif "last_bcrp" in st.session_state:

    oficial = st.session_state["last_bcrp"]


banco = official_pair(
    oficial, "Bancario"
)

inter = official_pair(
    oficial, "Interbancario"
)


if (
    info is None
    and banco is None
    and inter is None
):

    st.error(
        "Las fuentes no respondieron. "
        "Comprueba la conexion y pulsa "
        "'Actualizar fuentes'. "
        "No se mostraran cifras inventadas."
    )

    st.stop()


rate_ref = (
    float(info["rates"]["PEN"])
    if info else None
)

pair = banco or inter

buy = (
    pair["compra"]
    if pair else rate_ref
)

sell = (
    pair["venta"]
    if pair else rate_ref
)


if banco:
    source_pair = "Sistema bancario SBS - BCRP"
elif inter:
    source_pair = "Mercado interbancario - BCRP"
else:
    source_pair = "Tipo de cambio referencial"


# ==========================================
# PANEL PRINCIPAL
# ==========================================

st.markdown("### 📊 Resumen del dolar")

if pair:

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Compra USD",
        f"S/ {buy:.4f}"
    )

    c2.metric(
        "Venta USD",
        f"S/ {sell:.4f}"
    )

    c3.metric(
        "Diferencia compra/venta",
        f"S/ {sell - buy:.4f}"
    )

    c4.metric(
        "Por US$ 1,000 vendidos",
        f"S/ {1000 * buy:,.2f}"
    )

else:

    c1, c2 = st.columns(2)

    c1.metric(
        "USD/PEN referencial",
        f"S/ {rate_ref:.4f}"
    )

    c2.metric(
        "US$ 1,000 de referencia",
        f"S/ {1000 * rate_ref:,.2f}"
    )


texto_fuente = f"Fuente: {source_pair}. "

if pair:
    texto_fuente += (
        f"Fecha oficial: "
        f"{pair['fecha']:%d/%m/%Y}. "
    )

if info:
    texto_fuente += (
        f"Referencia internacional: "
        f"{info['source']} - "
        f"{info['date']}."
    )

st.caption(texto_fuente)

st.info(
    "Compra: la entidad compra tus dolares. "
    "Venta: la entidad te vende dolares. "
    "Los valores son estadisticos o "
    "referenciales, no ofertas comerciales."
)


# ==========================================
# CREACION DE PESTANAS
# ==========================================

names = [
    "💸 Conversor y simulador"
]

if banco or inter:
    names.append(
        "🏦 Comparar mercados"
    )

names.append(
    "📈 Evolucion historica"
)

if (
    info
    and any(
        code in info["rates"]
        for code in COUNTRIES
    )
):
    names.append(
        "🌎 15 monedas"
    )

names.append(
    "🎯 Meta de ahorro"
)

tabs = dict(
    zip(
        names,
        st.tabs(names)
    )
)


# ==========================================
# PESTANA 1: CONVERSOR Y SIMULADOR
# ==========================================

with tabs["💸 Conversor y simulador"]:

    st.subheader(
        "💸 Calcula una operacion de cambio"
    )

    side1, side2 = st.columns(2)

    with side1:

        op = st.radio(
            "¿Que quieres hacer?",
            [
                "Tengo dolares y quiero soles",
                "Tengo soles y quiero dolares"
            ]
        )

        amount = st.number_input(
            "Monto que entregas",
            min_value=0.0,
            value=1000.0,
            step=50.0
        )

        fee = st.number_input(
            "Comision hipotetica (S/)",
            min_value=0.0,
            value=0.0,
            step=1.0
        )

        margin = st.slider(
            "Margen adicional supuesto (%)",
            0.0,
            3.0,
            0.0,
            0.1
        )

    if op.startswith("Tengo dolares"):

        adjusted = buy * (
            1 - margin / 100
        )

        gross = amount * adjusted

        result = max(
            gross - fee, 0
        )

        currency = "S/"

        base = amount * buy

    else:

        adjusted = sell * (
            1 + margin / 100
        )

        result = (
            max(amount - fee, 0)
            / adjusted
        )

        currency = "US$"

        base = amount / sell

    with side2:

        st.metric(
            "Recibirias aproximadamente",
            f"{currency} {result:,.2f}"
        )

        st.metric(
            "Tipo de cambio aplicado",
            f"S/ {adjusted:.4f}"
        )

        st.metric(
            "Diferencia por costos supuestos",
            f"{currency} "
            f"{max(base - result, 0):,.2f}"
        )

        st.caption(
            "El resultado se actualiza "
            "al modificar los valores."
        )

    st.markdown(
        "### 📋 Detalle de la simulacion"
    )

    detalle = pd.DataFrame([
        {
            "Concepto": "Monto ingresado",
            "Valor": f"{amount:,.2f}"
        },
        {
            "Concepto": "Tipo de cambio",
            "Valor": f"S/ {adjusted:.4f}"
        },
        {
            "Concepto": "Comision",
            "Valor": f"S/ {fee:.2f}"
        },
        {
            "Concepto": "Resultado final",
            "Valor": (
                f"{currency} {result:,.2f}"
            )
        }
    ])

    st.dataframe(
        detalle,
        hide_index=True,
        use_container_width=True
    )

    st.caption(
        "Las comisiones y margenes son "
        "escenarios hipoteticos."
    )


# ==========================================
# PESTANA 2: COMPARADOR
# ==========================================

if "🏦 Comparar mercados" in tabs:

    with tabs["🏦 Comparar mercados"]:

        st.subheader(
            "🏦 Comparador de mercados"
        )

        records = []

        for name, p in [
            ("Sistema bancario SBS", banco),
            ("Interbancario", inter)
        ]:

            if p:

                records.append({
                    "Mercado": name,
                    "Fecha": p["fecha"].strftime(
                        "%d/%m/%Y"
                    ),
                    "Compra (S/)": p["compra"],
                    "Venta (S/)": p["venta"],
                    "Spread (S/)": (
                        p["venta"] - p["compra"]
                    )
                })

        comparison = pd.DataFrame(records)

        st.dataframe(
            comparison,
            hide_index=True,
            use_container_width=True
        )

        budget = st.number_input(
            "Dolares que quieres comparar",
            min_value=1.0,
            value=1000.0,
            step=100.0
        )

        st.subheader(
            "¿Cuantos soles recibirias al vender?"
        )

        chart_data = pd.DataFrame({
            "Mercado": comparison["Mercado"],
            "Soles": [
                budget * row["Compra (S/)"]
                for _, row in comparison.iterrows()
            ]
        }).set_index("Mercado")

        st.bar_chart(chart_data)

        st.caption(
            "Comparacion estadistica. "
            "No representa ofertas de "
            "bancos especificos."
        )

        st.download_button(
            "⬇️ Descargar comparacion CSV",
            comparison.to_csv(
                index=False
            ).encode("utf-8-sig"),
            "comparacion_bcrp.csv",
            "text/csv"
        )


# ==========================================
# PESTANA 3: HISTORICO
# ==========================================

with tabs["📈 Evolucion historica"]:

    st.subheader(
        "📈 Historico del tipo de cambio"
    )

    days = st.select_slider(
        "Selecciona el periodo",
        options=[
            7, 30, 90, 180, 365
        ],
        value=30,
        format_func=lambda n: f"{n} dias"
    )

    show_official = not oficial.empty

    if show_official:

        hist = oficial[
            oficial["Fecha"]
            >= date.today()
            - timedelta(days=days)
        ].copy()

        lines = [
            key
            for key in [
                "Bancario compra",
                "Bancario venta"
            ]
            if (
                key in hist
                and hist[key].notna().any()
            )
        ]

        if not lines:

            lines = [
                key
                for key in [
                    "Interbancario compra",
                    "Interbancario venta"
                ]
                if (
                    key in hist
                    and hist[key].notna().any()
                )
            ]

        if lines:

            hist = hist.dropna(
                subset=lines,
                how="all"
            )

        else:
            hist = pd.DataFrame()

        kind = (
            "Fuente: BCRPData. "
            "Datos publicados en dias "
            "de operacion."
        )

    else:

        with st.spinner(
            "Recuperando historial alternativo..."
        ):

            hist = alternative_history(days)

        lines = ["Referencial"]

        kind = (
            "Fuente: Currency API. "
            "Muestreo de fechas."
        )

    if len(hist) >= 2:

        plot_lines(
            hist,
            lines,
            "Evolucion USD/PEN"
        )

        usable = hist[
            lines[0]
        ].dropna()

        x1, x2, x3 = st.columns(3)

        x1.metric(
            "Promedio del periodo",
            f"S/ {usable.mean():.4f}"
        )

        x2.metric(
            "Minimo observado",
            f"S/ {usable.min():.4f}"
        )

        x3.metric(
            "Maximo observado",
            f"S/ {usable.max():.4f}"
        )

        st.caption(kind)

        st.dataframe(
            hist.sort_values(
                "Fecha",
                ascending=False
            ),
            hide_index=True,
            use_container_width=True
        )

        st.download_button(
            "⬇️ Descargar historico CSV",
            hist.to_csv(
                index=False
            ).encode("utf-8-sig"),
            "historico_dolar.csv",
            "text/csv"
        )

    else:

        st.warning(
            "La fuente historica no devolvio "
            "suficientes registros. "
            "Pulsa Actualizar fuentes "
            "para intentarlo nuevamente."
        )


# ==========================================
# PESTANA 4: MONEDAS INTERNACIONALES
# ==========================================

if "🌎 15 monedas" in tabs:

    with tabs["🌎 15 monedas"]:

        st.subheader(
            "🌎 Conversor internacional"
        )

        st.write(
            "Convierte soles a monedas "
            "de diferentes paises."
        )

        pen_amount = st.number_input(
            "Monto en soles",
            min_value=0.0,
            value=1000.0,
            step=50.0,
            key="global_amount"
        )

        rows = []

        for code, name in COUNTRIES.items():

            target = positive_number(
                info["rates"].get(code)
            )

            if target:

                per_pen = (
                    target / rate_ref
                )

                rows.append({
                    "Moneda": code,
                    "Pais / divisa": name,
                    "Por S/ 1": round(
                        per_pen, 6
                    ),
                    "Recibirias": round(
                        pen_amount * per_pen,
                        2
                    )
                })

        world = pd.DataFrame(rows)

        st.dataframe(
            world,
            hide_index=True,
            use_container_width=True
        )

        chosen = st.selectbox(
            "Ver una moneda en detalle",
            world["Moneda"].tolist()
        )

        one = world[
            world["Moneda"] == chosen
        ].iloc[0]

        st.metric(
            f"Equivalente en {chosen}",
            f"{one['Recibirias']:,.2f} "
            f"{chosen}"
        )

        st.caption(
            f"Fuente: {info['source']}. "
            "Cotizaciones referenciales "
            "sin comisiones."
        )

        st.download_button(
            "⬇️ Descargar monedas CSV",
            world.to_csv(
                index=False
            ).encode("utf-8-sig"),
            "15_monedas.csv",
            "text/csv"
        )


# ==========================================
# PESTANA 5: META DE AHORRO
# ==========================================

with tabs["🎯 Meta de ahorro"]:

    st.subheader(
        "🎯 Planificador de ahorro en dolares"
    )

    st.write(
        "Calcula cuanto necesitas ahorrar "
        "para alcanzar una meta en USD."
    )

    target_usd = st.number_input(
        "Meta en dolares (USD)",
        min_value=1.0,
        value=1500.0,
        step=100.0
    )

    saved_pen = st.number_input(
        "Soles que ya tienes",
        min_value=0.0,
        value=500.0,
        step=50.0
    )

    monthly_pen = st.number_input(
        "Ahorro mensual en soles",
        min_value=1.0,
        value=250.0,
        step=50.0
    )

    cost = target_usd * sell

    pending = max(
        cost - saved_pen, 0
    )

    months = math.ceil(
        pending / monthly_pen
    )

    a, b, c = st.columns(3)

    a.metric(
        "Costo referencial de la meta",
        f"S/ {cost:,.2f}"
    )

    b.metric(
        "Falta ahorrar",
        f"S/ {pending:,.2f}"
    )

    c.metric(
        "Meses estimados",
        months
    )

    progress = min(
        saved_pen / cost,
        1.0
    )

    st.progress(progress)

    st.caption(
        "Proyeccion con tipo de cambio "
        "constante. No constituye "
        "un pronostico financiero."
    )


# ==========================================
# PIE DE PAGINA
# ==========================================

st.divider()

st.markdown("""
### 💵 Dólar Perú PRO

**Tu centro de información cambiaria.**

Aplicación académica creada utilizando
Python, Streamlit y GitHub.
""")

st.caption(
    "Los proveedores publican datos "
    "en horarios distintos. "
    "La aplicación no realiza "
    "transacciones financieras."
)
