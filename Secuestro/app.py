import pandas as pd
import plotly.express as px
import streamlit as st

# ==================================================
# TITULO
# ==================================================

st.title("Observatorio Presidencial")

st.subheader(
    "Secuestro en Colombia"
)

st.markdown(
    """
Análisis comparativo presidencial utilizando datos abiertos oficiales
de Colombia y tasas por cada 100.000 habitantes.
"""
)

# ==================================================
# FUENTES
# ==================================================

st.markdown(
    """
### Fuente de datos abiertos

Datos Abiertos Colombia:

https://www.datos.gov.co/Seguridad-y-Defensa/SECUESTRO/d7zw-hpf4/about_data
"""
)

st.markdown(
    """
### Fuente población DANE

Proyecciones oficiales de población:

https://www.dane.gov.co/index.php/estadisticas-por-tema/demografia-y-poblacion/proyecciones-de-poblacion
"""
)

# ==================================================
# REVISION METODOLOGICA
# ==================================================

st.markdown(
    """
### Revisión metodológica

El dataset oficial de secuestro utilizado en este análisis
contiene información desde el año 2003.

Con el fin de garantizar comparabilidad homogénea entre
periodos presidenciales completos, el análisis inicia
desde el segundo periodo presidencial de Álvaro Uribe Vélez
(07/agosto/2006).

Los periodos incluidos son:

- Álvaro Uribe Vélez (segundo periodo)
- Juan Manuel Santos (primer periodo)
- Juan Manuel Santos (segundo periodo)
- Iván Duque Márquez
- Gustavo Petro Urrego

Las comparaciones utilizan ventanas equivalentes
de tiempo presidencial.

Las tasas por cada 100.000 habitantes son calculadas
utilizando proyecciones oficiales de población del DANE
interpoladas mensualmente.
"""
)

# ==================================================
# DESCARGAR TODOS LOS DATOS API
# ==================================================

offset = 0
limit = 50000

dfs = []

while True:

    url = (
        f"https://www.datos.gov.co/resource/d7zw-hpf4.csv?"
        f"$limit={limit}&$offset={offset}"
    )

    temp = pd.read_csv(url)

    if temp.empty:
        break

    dfs.append(temp)

    print(f"Descargadas {len(temp)} filas...")

    offset += limit

# ==================================================
# UNIR TODO
# ==================================================

df = pd.concat(dfs, ignore_index=True)

# ==================================================
# CARGAR PRESIDENTES
# ==================================================

presidentes = pd.read_excel(
    "tabla_presidentes_gobierno_2000_2026.xlsx"
)

# ==================================================
# CARGAR POBLACION
# ==================================================

poblacion = pd.read_excel(
    "poblacion_interpolada_mensual_colombia.xlsx"
)

# ==================================================
# CONVERTIR FECHAS
# ==================================================

df["Fecha"] = pd.to_datetime(
    df["fecha_hecho"]
)

presidentes["Fecha"] = pd.to_datetime(
    presidentes["Fecha"]
)

poblacion["Fecha"] = pd.to_datetime(
    poblacion["Fecha"]
)

# ==================================================
# REDONDEAR AL MES
# ==================================================

df["Fecha"] = (
    df["Fecha"]
    .dt.to_period("M")
    .dt.to_timestamp()
)

presidentes["Fecha"] = (
    presidentes["Fecha"]
    .dt.to_period("M")
    .dt.to_timestamp()
)

poblacion["Fecha"] = (
    poblacion["Fecha"]
    .dt.to_period("M")
    .dt.to_timestamp()
)

# ==================================================
# MERGE PRESIDENTES
# ==================================================

final = df.merge(
    presidentes,
    on="Fecha",
    how="left"
)

# ==================================================
# MERGE POBLACION
# ==================================================

final = final.merge(
    poblacion,
    on="Fecha",
    how="left"
)

# ==================================================
# FILTRAR DESDE SEGUNDO GOBIERNO URIBE
# ==================================================

final = final[
    final["Fecha"] >= pd.Timestamp("2006-08-07")
]

# ==================================================
# FILTRO TIPO DELITO
# ==================================================

tipos = sorted(
    final["tipo_delito"]
    .dropna()
    .unique()
)

tipo_delito = st.selectbox(
    "Selecciona tipo delito:",
    ["TODOS"] + tipos
)

# ==================================================
# FILTRAR DELITO
# ==================================================

if tipo_delito != "TODOS":

    final = final[
        final["tipo_delito"] == tipo_delito
    ]

# ==================================================
# SELECTOR TEMPORAL
# ==================================================

eje_x = st.selectbox(
    "Selecciona periodo:",
    [
        "Mes Gobierno",
        "Trimestre Gobierno",
        "Año Gobierno"
    ]
)

# ==================================================
# AGRUPAR CASOS
# ==================================================

grafica = (
    final.groupby(
        ["Presidente", eje_x]
    )["cantidad"]
    .sum()
    .reset_index()
)

# ==================================================
# CREAR ACUMULADO
# ==================================================

grafica["Acumulado"] = (
    grafica.groupby("Presidente")["cantidad"]
    .cumsum()
)

# ==================================================
# POBLACION PROMEDIO
# ==================================================

pob = (
    final.groupby(
        ["Presidente", eje_x]
    )["Poblacion_Interpolada"]
    .mean()
    .reset_index()
)

grafica = grafica.merge(
    pob,
    on=["Presidente", eje_x],
    how="left"
)

# ==================================================
# CALCULAR TASA 100K
# ==================================================

grafica["Tasa_100k"] = (
    grafica["cantidad"] /
    grafica["Poblacion_Interpolada"]
) * 100000

# ==================================================
# SELECTOR GRAFICA
# ==================================================

tipo_grafica = st.selectbox(
    "Tipo gráfica:",
    [
        "cantidad",
        "Acumulado",
        "Tasa_100k"
    ]
)

# ==================================================
# GRAFICA COMPARATIVA
# ==================================================

fig1 = px.line(
    grafica,
    x=eje_x,
    y=tipo_grafica,
    color="Presidente",
    markers=True,
    title=f"Comparativo presidencial - {tipo_grafica}"
)

fig1.update_layout(
    hovermode="x unified"
)

st.plotly_chart(fig1)

# ==================================================
# GRAFICA ACUMULADA
# ==================================================

fig2 = px.line(
    grafica,
    x=eje_x,
    y="Acumulado",
    color="Presidente",
    markers=True,
    title="Acumulado presidencial"
)

fig2.update_layout(
    hovermode="x unified"
)

st.plotly_chart(fig2)