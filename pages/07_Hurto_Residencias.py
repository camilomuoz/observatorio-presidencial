import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent


def ruta_tabla_presidentes() -> Path:
    candidatos = [
        ROOT / "tabla_presidentes_gobierno_2000_2026.xlsx",
        ROOT / "Secuestro" / "tabla_presidentes_gobierno_2000_2026.xlsx",
        ROOT / "Fuerza Publica" / "tabla_presidentes_gobierno_2000_2026.xlsx",
    ]
    for ruta in candidatos:
        if ruta.exists():
            return ruta
    raise FileNotFoundError(
        "No se encontro 'tabla_presidentes_gobierno_2000_2026.xlsx' en raiz/Secuestro/Fuerza Publica."
    )


@st.cache_data
def cargar_datos():
    offset = 0
    limit = 50000
    dfs = []

    while True:
        url = (
            f"https://www.datos.gov.co/resource/7mn7-vzqp.csv?"
            f"$limit={limit}&$offset={offset}"
        )
        temp = pd.read_csv(url)
        if temp.empty:
            break
        dfs.append(temp)
        offset += limit

    return pd.concat(dfs, ignore_index=True)


st.set_page_config(page_title="Hurto a Residencias", layout="wide")

st.title("Observatorio Presidencial")
st.subheader("Hurto a Residencias en Colombia")

df = cargar_datos()
presidentes = pd.read_excel(ruta_tabla_presidentes())
poblacion = pd.read_excel(ROOT / "Secuestro" / "poblacion_interpolada_mensual_colombia.xlsx")

df["fecha_hecho"] = pd.to_datetime(df["fecha_hecho"], errors="coerce")
presidentes["Fecha"] = pd.to_datetime(presidentes["Fecha"], errors="coerce")
poblacion["Fecha"] = pd.to_datetime(poblacion["Fecha"], errors="coerce")

df["Fecha"] = df["fecha_hecho"].dt.to_period("M").dt.to_timestamp()
presidentes["Fecha"] = presidentes["Fecha"].dt.to_period("M").dt.to_timestamp()
poblacion["Fecha"] = poblacion["Fecha"].dt.to_period("M").dt.to_timestamp()

final = df.merge(presidentes, on="Fecha", how="left")
final = final.merge(poblacion, on="Fecha", how="left")
final = final[final["Fecha"] >= pd.Timestamp("2006-08-07")]
final["cantidad"] = pd.to_numeric(final["cantidad"], errors="coerce")

if "res_periodo" not in st.session_state:
    st.session_state["res_periodo"] = "Año Gobierno"
eje_x = st.selectbox(
    "Selecciona periodo:",
    ["Año Gobierno", "Trimestre Gobierno", "Mes Gobierno"],
    key="res_periodo",
)

grafica = final.groupby(["Presidente", eje_x])["cantidad"].sum().reset_index()
grafica["Acumulado"] = grafica.groupby("Presidente")["cantidad"].cumsum()

pob = final.groupby(["Presidente", eje_x])["Poblacion_Interpolada"].mean().reset_index()
grafica = grafica.merge(pob, on=["Presidente", eje_x], how="left")
grafica["Tasa_100k"] = (grafica["cantidad"] / grafica["Poblacion_Interpolada"]) * 100000
grafica["Acumulado_Tasa_100k"] = grafica.groupby("Presidente")["Tasa_100k"].cumsum()

metrica = st.selectbox(
    "Metrica para hurto a residencias:",
    ["cantidad", "Tasa_100k"],
)
metrica_acum = "Acumulado" if metrica == "cantidad" else "Acumulado_Tasa_100k"

fig1 = px.line(
    grafica,
    x=eje_x,
    y=metrica,
    color="Presidente",
    markers=True,
    title=f"Comparativo presidencial - {metrica}",
)
fig1.update_layout(hovermode="x unified")
st.plotly_chart(fig1, use_container_width=True)

fig2 = px.line(
    grafica,
    x=eje_x,
    y=metrica_acum,
    color="Presidente",
    markers=True,
    title=f"Acumulado presidencial - {metrica}",
)
fig2.update_layout(hovermode="x unified")
st.plotly_chart(fig2, use_container_width=True)

st.markdown("### Filtros de mapa (solo afectan mapas coropleticos)")

presidentes_mapa = sorted(final["Presidente"].dropna().astype(str).unique())
presidente_mapa = st.selectbox(
    "Presidente para mapas:",
    ["TODOS"] + presidentes_mapa,
    key="res_map_presidente",
)

if "res_map_periodo" not in st.session_state:
    st.session_state["res_map_periodo"] = "Año Gobierno"
periodo_mapa = st.selectbox(
    "Periodo para mapas:",
    ["Año Gobierno", "Trimestre Gobierno", "Mes Gobierno"],
    key="res_map_periodo",
)

final_mapa = final.copy()
if presidente_mapa != "TODOS":
    final_mapa = final_mapa[final_mapa["Presidente"].astype(str) == presidente_mapa].copy()

final_mapa = final_mapa.dropna(subset=[periodo_mapa]).copy()
if not final_mapa.empty:
    periodos_ordenados = (
        final_mapa.groupby(periodo_mapa, as_index=False)["Fecha"]
        .min()
        .sort_values("Fecha")[periodo_mapa]
        .tolist()
    )
    if len(periodos_ordenados) > 1:
        inicio_mapa, fin_mapa = st.select_slider(
            "Rango de periodo para mapas:",
            options=periodos_ordenados,
            value=(periodos_ordenados[0], periodos_ordenados[-1]),
            key="res_map_rango",
        )
        i_ini = periodos_ordenados.index(inicio_mapa)
        i_fin = periodos_ordenados.index(fin_mapa)
        permitidos = set(periodos_ordenados[i_ini:i_fin + 1])
        final_mapa = final_mapa[final_mapa[periodo_mapa].isin(permitidos)].copy()
else:
    st.warning("No hay datos para los filtros seleccionados en mapas.")

st.header("Mapa coropletico por departamento")

ruta_geojson_depto = ROOT / "colombia.geojson-master" / "depto.json"
with open(ruta_geojson_depto, encoding="utf-8") as f:
    geojson_depto = json.load(f)

final_mapa["cod_depto"] = final_mapa["cod_depto"].astype(str).str.zfill(2)
mapa_depto_df = (
    final_mapa.groupby(["cod_depto", "departamento"])["cantidad"]
    .sum()
    .reset_index()
)

fig_mapa_depto = px.choropleth_mapbox(
    mapa_depto_df,
    geojson=geojson_depto,
    locations="cod_depto",
    featureidkey="properties.DPTO",
    color="cantidad",
    hover_name="departamento",
    hover_data={"cantidad": True},
    color_continuous_scale="Reds",
    mapbox_style="carto-darkmatter",
    zoom=4.5,
    center={"lat": 4.5, "lon": -74},
    opacity=0.85,
)
fig_mapa_depto.update_layout(height=700, margin={"r": 0, "t": 0, "l": 0, "b": 0})
st.plotly_chart(fig_mapa_depto, use_container_width=True)

st.subheader("Tabla departamentos")
st.dataframe(mapa_depto_df.sort_values("cantidad", ascending=False), use_container_width=True)



final_mapa["cod_muni"] = final_mapa["cod_muni"].astype(str).str.zfill(5)
mapa_mpio_df = (
    final_mapa.groupby(["cod_muni", "municipio"])["cantidad"]
    .sum()
    .reset_index()
)


st.subheader("Tabla municipios")
st.dataframe(mapa_mpio_df.sort_values("cantidad", ascending=False), use_container_width=True)




