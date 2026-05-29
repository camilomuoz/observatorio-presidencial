from pathlib import Path
import json

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent


def cargar_tabla_presidentes() -> pd.DataFrame:
    candidatos = [
        ROOT / "tabla_presidentes_gobierno_2000_2026.xlsx",  # tabla transversal (raiz)
        ROOT / "Fuerza Publica" / "tabla_presidentes_gobierno_2000_2026.xlsx",
        ROOT / "Secuestro" / "tabla_presidentes_gobierno_2000_2026.xlsx",
    ]
    for ruta in candidatos:
        if ruta.exists():
            return pd.read_excel(ruta)
    raise FileNotFoundError(
        "No se encontro 'tabla_presidentes_gobierno_2000_2026.xlsx' en raiz/Fuerza Publica/Secuestro."
    )

# ==================================================
# TITULO
# ==================================================

st.title("Observatorio Presidencial")

st.subheader(
    "AFECTACIÃƒâ€œN DE MIEMBROS DE LA FUERZA PÃƒÅ¡BLICA"
)

st.markdown(
    """
Corresponde a los homicidios y lesiones que reporta la Fuerza PÃƒÂºblica
(EjÃƒÂ©rcito Nacional, Armada Nacional, Fuerza AÃƒÂ©rea y PolicÃƒÂ­a Nacional)
en cumplimiento de su deber constitucional o actos de servicio,
excluyendo vacaciones, permisos y licencias.
"""
)

st.markdown(
    """
**Fuente oficial:**  
[Datos Abiertos Colombia - AfectaciÃƒÂ³n de miembros de la Fuerza PÃƒÂºblica](https://www.datos.gov.co/Seguridad-y-Defensa/AFECTACI-N-DE-MIEMBROS-DE-LA-FUERZA-P-BLICA/8rpn-wpty/about_data)
"""
)

st.markdown(
    """
### RevisiÃƒÂ³n metodolÃƒÂ³gica

Para efectos de comparabilidad entre gobiernos, este anÃƒÂ¡lisis
considera ÃƒÂºnicamente periodos equivalentes de mandato presidencial.

El dataset oficial utilizado inicia en el aÃƒÂ±o 2010, por lo cual
no se incluye el segundo periodo presidencial completo de ÃƒÂlvaro Uribe VÃƒÂ©lez,
ya que no existe informaciÃƒÂ³n homogÃƒÂ©nea para todo su mandato dentro
de esta fuente de datos.

En consecuencia, las comparaciones presentadas corresponden a:

- Juan Manuel Santos (primer periodo presidencial)
- Juan Manuel Santos (segundo periodo presidencial)
- IvÃƒÂ¡n Duque MÃƒÂ¡rquez
- Gustavo Petro Urrego

Todos los gobiernos son comparados utilizando ventanas equivalentes
de tiempo de mandato.
"""
)

# ==================================================
# 1. CARGAR DATOS API
# ==================================================

# ==================================================
# DESCARGAR TODOS LOS DATOS API
# ==================================================

offset = 0
limit = 50000

dfs = []

while True:

    url = (
        f"https://www.datos.gov.co/resource/8rpn-wpty.csv?"
        f"$limit={limit}&$offset={offset}"
    )

    temp = pd.read_csv(url)

    # SI YA NO HAY DATOS Ã¢â€ â€™ TERMINA
    if temp.empty:
        break

    dfs.append(temp)

    print(f"Descargadas {len(temp)} filas...")

    offset += limit

# UNIR TODOS LOS DATAFRAMES

df = pd.concat(dfs, ignore_index=True)

print("\nTOTAL FILAS DESCARGADAS:")
print(len(df))

# ==================================================
# 2. CARGAR TABLA PRESIDENTES
# ==================================================

presidentes = cargar_tabla_presidentes()

# ==================================================
# 3. CONVERTIR FECHAS
# ==================================================

df["Fecha"] = pd.to_datetime(df["fecha_hecho"])

presidentes["Fecha"] = pd.to_datetime(
    presidentes["Fecha"]
)

# ==================================================
# 4. ELIMINAR HORA
# ==================================================

df["Fecha"] = df["Fecha"].dt.date
presidentes["Fecha"] = presidentes["Fecha"].dt.date

# ==================================================
# 5. HACER JOIN
# ==================================================

final = df.merge(
    presidentes,
    on="Fecha",
    how="left"
)

# ==================================================
# 6. QUITAR URIBE
# ==================================================

final = final[
    final["Presidente"] != "Alvaro Uribe 2"
]

# ==================================================
# 7. SELECTOR TIPO AFECTACION
# ==================================================

tipo_accion = st.selectbox(
    "Selecciona tipo:",
    [
        "ASESINADO",
        "HERIDO"
    ]
)

# FILTRAR

final = final[
    final["accion"] == tipo_accion
]

# ==================================================
# 8. SELECTOR EJE X
# ==================================================

if "fp_periodo" not in st.session_state:
    st.session_state["fp_periodo"] = "Año Gobierno"
eje_x = st.selectbox(
    "Selecciona periodo:",
    [
        "Año Gobierno",
        "Trimestre Gobierno",
        "Mes Gobierno"
    ],
    key="fp_periodo",
)

# ==================================================
# 9. AGRUPAR
# ==================================================

grafica = (
    final_mapa.groupby(
        ["Presidente", eje_x]
    )["cantidad"]
    .sum()
    .reset_index()
)

# ==================================================
# 10. ACUMULADO
# ==================================================

grafica["Acumulado"] = (
    grafica.groupby("Presidente")["cantidad"]
    .cumsum()
)

# ==================================================
# 11. GRAFICA NORMAL
# ==================================================

fig1 = px.line(
    grafica,
    x=eje_x,
    y="cantidad",
    color="Presidente",
    markers=True,
    title=f"{tipo_accion} por {eje_x}"
)

fig1.update_layout(
    hovermode="x unified"
)

st.plotly_chart(fig1)

# ==================================================
# 12. GRAFICA ACUMULADA
# ==================================================

fig2 = px.line(
    grafica,
    x=eje_x,
    y="Acumulado",
    color="Presidente",
    markers=True,
    title=f"Acumulado de {tipo_accion}"
)

fig2.update_layout(
    hovermode="x unified"
)

st.plotly_chart(fig2)

# ==================================================
# FILTROS SOLO PARA MAPAS
# ==================================================

st.markdown("### Filtros de mapa (solo afectan mapas coropleticos)")

presidentes_mapa = sorted(final["Presidente"].dropna().astype(str).unique())
presidente_mapa = st.selectbox(
    "Presidente para mapas:",
    ["TODOS"] + presidentes_mapa,
    key="fp_map_presidente",
)

if "fp_map_periodo" not in st.session_state:
    st.session_state["fp_map_periodo"] = "Año Gobierno"
periodo_mapa = st.selectbox(
    "Periodo para mapas:",
    ["Año Gobierno", "Trimestre Gobierno", "Mes Gobierno"],
    key="fp_map_periodo",
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
            key="fp_map_rango",
        )
        i_ini = periodos_ordenados.index(inicio_mapa)
        i_fin = periodos_ordenados.index(fin_mapa)
        permitidos = set(periodos_ordenados[i_ini:i_fin + 1])
        final_mapa = final_mapa[final_mapa[periodo_mapa].isin(permitidos)].copy()
else:
    st.warning("No hay datos para los filtros seleccionados en mapas.")

# ==================================================
# 13. MAPA CLOROPLETICO
# ==================================================

st.header(
    "Mapa cloroplÃƒÂ©tico por departamento"
)

# ==================================================
# CARGAR GEOJSON
# ==================================================

ruta_geojson = ROOT / "colombia.geojson-master" / "depto.json"
with open(ruta_geojson, encoding="utf-8") as f:

    geojson_data = json.load(f)

# ==================================================
# LIMPIAR CODIGO DANE
# ==================================================

final_mapa["cod_depto"] = (
    final_mapa["cod_depto"]
    .astype(str)
    .str.zfill(2)
)

# ==================================================
# AGRUPAR DEPARTAMENTOS
# ==================================================

mapa_df = (
    final_mapa.groupby(
        ["cod_depto", "departamento"]
    )["cantidad"]
    .sum()
    .reset_index()
)

# ==================================================
# MAPA
# ==================================================

fig_mapa = px.choropleth_mapbox(

    mapa_df,

    geojson=geojson_data,

    locations="cod_depto",

    featureidkey="properties.DPTO",

    color="cantidad",

    hover_name="departamento",

    hover_data={
        "cantidad": True
    },

    color_continuous_scale="Reds",

    mapbox_style="carto-darkmatter",

    zoom=4.5,

    center={
        "lat": 4.5,
        "lon": -74
    },

    opacity=0.85

)

# ==================================================
# AJUSTES
# ==================================================

fig_mapa.update_layout(

    height=700,

    margin={
        "r": 0,
        "t": 0,
        "l": 0,
        "b": 0
    }

)

# ==================================================
# MOSTRAR
# ==================================================

st.plotly_chart(
    fig_mapa,
    use_container_width=True
)

# ==================================================
# TABLA
# ==================================================

st.subheader(
    "Tabla departamentos"
)

st.dataframe(
    mapa_df.sort_values(
        "cantidad",
        ascending=False
    ),
    use_container_width=True
)

# ==================================================
# 14. MAPA CLOROPLETICO MUNICIPIO
# ==================================================



final_mapa["cod_muni"] = (
    final_mapa["cod_muni"]
    .astype(str)
    .str.zfill(5)
)

mapa_mpio_df = (
    final_mapa.groupby(
        ["cod_muni", "municipio"]
    )["cantidad"]
    .sum()
    .reset_index()
)


st.subheader(
    "Tabla municipios"
)

st.dataframe(
    mapa_mpio_df.sort_values("cantidad", ascending=False),
    use_container_width=True
)



