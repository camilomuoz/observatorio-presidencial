from pathlib import Path
import json
import unicodedata

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent

st.set_page_config(page_title="Datos Gov", layout="wide")


@st.cache_data(show_spinner=False)
def descargar_csv_socrata(resource_id: str, limit: int = 50000) -> pd.DataFrame:
    offset = 0
    bloques = []

    while True:
        url = (
            f"https://www.datos.gov.co/resource/{resource_id}.csv?"
            f"$limit={limit}&$offset={offset}"
        )
        parte = pd.read_csv(url)
        if parte.empty:
            break
        bloques.append(parte)
        offset += limit

    if not bloques:
        return pd.DataFrame()

    return pd.concat(bloques, ignore_index=True)


@st.cache_data(show_spinner=False)
def cargar_geojson_departamentos() -> dict:
    ruta = ROOT / "colombia.geojson-master" / "depto.json"
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def cargar_geojson_municipios() -> dict:
    ruta = ROOT / "colombia.geojson-master" / "mpio.json"
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def cargar_tabla_presidentes() -> pd.DataFrame:
    candidatos = [
        ROOT / "tabla_presidentes_gobierno_2000_2026.xlsx",
        ROOT / "Fuerza Publica" / "tabla_presidentes_gobierno_2000_2026.xlsx",
        ROOT / "Secuestro" / "tabla_presidentes_gobierno_2000_2026.xlsx",
    ]
    for ruta in candidatos:
        if ruta.exists():
            return pd.read_excel(ruta)
    raise FileNotFoundError("No se encontro la tabla de presidentes en raiz/Fuerza Publica/Secuestro.")
def normalizar_texto(texto: str) -> str:
    txt = str(texto).strip().lower()
    try:
        txt = txt.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
    except Exception:
        pass
    txt = unicodedata.normalize("NFD", txt)
    return "".join(ch for ch in txt if unicodedata.category(ch) != "Mn")


def resolver_columna_periodo(df: pd.DataFrame, etiqueta: str) -> str:
    objetivo = normalizar_texto(etiqueta)
    for col in df.columns:
        if normalizar_texto(col) == objetivo:
            return col
    raise KeyError(f"No existe una columna equivalente a '{etiqueta}' en el dataframe.")


def pintar_mapa_departamento(df: pd.DataFrame, titulo: str) -> None:
    geojson = cargar_geojson_departamentos()
    mapa_df = df.copy()
    mapa_df["cod_depto"] = mapa_df["cod_depto"].astype(str).str.zfill(2)
    mapa_df = mapa_df.groupby(["cod_depto", "departamento"], as_index=False)["cantidad"].sum()

    st.subheader(titulo)
    fig = px.choropleth_mapbox(
        mapa_df,
        geojson=geojson,
        locations="cod_depto",
        featureidkey="properties.DPTO",
        color="cantidad",
        hover_name="departamento",
        color_continuous_scale="Reds",
        mapbox_style="carto-positron",
        zoom=4.5,
        center={"lat": 4.6, "lon": -74.1},
        opacity=0.85,
    )
    fig.update_layout(height=650, margin={"r": 0, "t": 0, "l": 0, "b": 0})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(mapa_df.sort_values("cantidad", ascending=False), use_container_width=True)


def pintar_mapa_municipio(df: pd.DataFrame, titulo: str) -> None:
    mapa_df = df.copy()
    mapa_df["cod_muni"] = mapa_df["cod_muni"].astype(str).str.zfill(5)
    mapa_df = mapa_df.groupby(["cod_muni", "municipio"], as_index=False)["cantidad"].sum()

    st.subheader("Tabla municipios")
    st.dataframe(mapa_df.sort_values("cantidad", ascending=False), use_container_width=True)


def filtrar_datos_mapa(df: pd.DataFrame, key_prefix: str) -> pd.DataFrame:
    st.markdown("### Filtros de mapa (solo afectan mapas coropleticos)")

    presidentes = sorted(df["Presidente"].dropna().astype(str).unique())
    presidente_mapa = st.selectbox(
        "Presidente para mapas:",
        ["TODOS"] + presidentes,
        key=f"{key_prefix}_map_presidente",
    )

    etiqueta_periodo_mapa = st.selectbox(
        "Periodo para mapas:",
        ["Mes Gobierno", "Trimestre Gobierno", "A\u00f1o Gobierno"],
        key=f"{key_prefix}_map_periodo",
    )
    periodo_mapa = resolver_columna_periodo(df, etiqueta_periodo_mapa)

    filtrado = df.copy()
    if presidente_mapa != "TODOS":
        filtrado = filtrado[filtrado["Presidente"].astype(str) == presidente_mapa].copy()

    filtrado = filtrado.dropna(subset=[periodo_mapa]).copy()
    if filtrado.empty:
        return filtrado

    orden_periodos = (
        filtrado.groupby(periodo_mapa, as_index=False)["Fecha"]
        .min()
        .sort_values("Fecha")[periodo_mapa]
        .tolist()
    )
    if not orden_periodos:
        return filtrado.iloc[0:0].copy()

    if len(orden_periodos) == 1:
        periodo_inicio = periodo_fin = orden_periodos[0]
    else:
        periodo_inicio, periodo_fin = st.select_slider(
            "Rango de periodo para mapas:",
            options=orden_periodos,
            value=(orden_periodos[0], orden_periodos[-1]),
            key=f"{key_prefix}_map_rango",
        )

    idx_inicio = orden_periodos.index(periodo_inicio)
    idx_fin = orden_periodos.index(periodo_fin)
    permitidos = set(orden_periodos[idx_inicio: idx_fin + 1])

    return filtrado[filtrado[periodo_mapa].isin(permitidos)].copy()


def render_inicio() -> None:
    st.title("Colombia en Datos")
    st.subheader("Visualización y análisis de datos públicos de Colombia")
    st.markdown("""
Bienvenido.

Este proyecto nace como una iniciativa personal para visualizar y explorar datos abiertos de Colombia de una manera más clara, accesible y entendible.

La idea surgió por curiosidad y por el interés de analizar información pública más allá de opiniones o percepciones. Muchas veces las discusiones sobre seguridad, economía o gestión gubernamental se basan en fragmentos de información, por lo que este espacio busca reunir distintos indicadores y presentarlos de forma visual y transparente.

Es importante entender que la gestión de un presidente, gobernador o cualquier gobernante no puede evaluarse a partir de un único dato. Los resultados de un país están influenciados por múltiples factores sociales, económicos, institucionales y regionales, por lo que este proyecto busca aportar contexto a través de datos abiertos oficiales.

Aquí únicamente se muestran datos y visualizaciones. Las interpretaciones y conclusiones quedan abiertas a cada persona.

Desde el menú lateral puedes navegar por distintas categorías como:

- Fuerza Pública
- Secuestro
- Extorsión
- Vehículos Hurtados
- Hurtos a Personas
- Hurto a Comercio
- Hurto a Residencias
- Terrorismo

Próximamente se agregarán más indicadores económicos y sociales para ampliar el análisis y permitir una visión más completa del país.

Fuentes:
- Datos Abiertos Colombia
- Entidades oficiales del Estado
""")


def render_fuerza_publica() -> None:
    st.title("Observatorio Presidencial")
    st.subheader("Afectacion de miembros de la Fuerza Publica")
    with st.expander("Descripcion del indicador", expanded=False):
        st.markdown(
            """
Corresponde a homicidios y lesiones reportadas por la Fuerza Publica
(Ejercito, Armada, Fuerza Aerea y Policia) en actos del servicio.
Para comparabilidad, se excluye **Alvaro Uribe 2** porque este dataset
inicia en 2010 y no cubre su periodo completo.
"""
        )

    with st.spinner("Cargando datos de Fuerza Publica..."):
        df = descargar_csv_socrata("8rpn-wpty")

    if df.empty:
        st.error("No fue posible cargar los datos de Fuerza Publica.")
        return

    presidentes = cargar_tabla_presidentes()
    df["Fecha"] = pd.to_datetime(df["fecha_hecho"], errors="coerce").dt.date
    presidentes["Fecha"] = pd.to_datetime(presidentes["Fecha"], errors="coerce").dt.date

    final = df.merge(presidentes, on="Fecha", how="left")
    final = final[final["Presidente"] != "Alvaro Uribe 2"].copy()
    final["cantidad"] = pd.to_numeric(final["cantidad"], errors="coerce").fillna(0)

    tipo_accion = st.selectbox("Selecciona tipo:", ["ASESINADO", "HERIDO"], key="fp_tipo")
    final = final[final["accion"] == tipo_accion].copy()

    etiqueta_eje_x = st.selectbox("Selecciona periodo:", ["Mes Gobierno", "Trimestre Gobierno", "A\u00f1o Gobierno"], key="fp_periodo")
    eje_x = resolver_columna_periodo(final, etiqueta_eje_x)

    grafica = final.groupby(["Presidente", eje_x], as_index=False)["cantidad"].sum()
    grafica["Acumulado"] = grafica.groupby("Presidente")["cantidad"].cumsum()

    fig1 = px.line(grafica, x=eje_x, y="cantidad", color="Presidente", markers=True, title=f"{tipo_accion} por {eje_x}")
    fig1.update_layout(hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.line(grafica, x=eje_x, y="Acumulado", color="Presidente", markers=True, title=f"Acumulado de {tipo_accion}")
    fig2.update_layout(hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)

    final_mapa = filtrar_datos_mapa(final, "fp")
    if final_mapa.empty:
        st.warning("No hay datos para los filtros seleccionados en mapas.")
    else:
        pintar_mapa_departamento(final_mapa, "Mapa coropletico por departamento")
        pintar_mapa_municipio(final_mapa, "Mapa coropletico por municipio")


def render_secuestro() -> None:
    st.title("Observatorio Presidencial")
    st.subheader("Secuestro en Colombia")
    with st.expander("Descripcion del indicador", expanded=False):
        st.markdown(
            """
Analisis de secuestro con datos oficiales de Datos Abiertos Colombia.
Incluye comparativos presidenciales y tasa por 100.000 habitantes.
La serie se analiza desde el segundo periodo de Alvaro Uribe
para mantener ventanas comparables.
"""
        )

    with st.spinner("Cargando datos de Secuestro..."):
        df = descargar_csv_socrata("d7zw-hpf4")

    if df.empty:
        st.error("No fue posible cargar los datos de Secuestro.")
        return

    presidentes = cargar_tabla_presidentes()
    poblacion = pd.read_excel(ROOT / "Secuestro" / "poblacion_interpolada_mensual_colombia.xlsx")

    df["fecha_hecho"] = pd.to_datetime(df["fecha_hecho"], errors="coerce")
    presidentes["Fecha"] = pd.to_datetime(presidentes["Fecha"], errors="coerce")
    poblacion["Fecha"] = pd.to_datetime(poblacion["Fecha"], errors="coerce")

    df["Fecha"] = df["fecha_hecho"].dt.to_period("M").dt.to_timestamp()
    presidentes["Fecha"] = presidentes["Fecha"].dt.to_period("M").dt.to_timestamp()
    poblacion["Fecha"] = poblacion["Fecha"].dt.to_period("M").dt.to_timestamp()

    final = df.merge(presidentes, on="Fecha", how="left")
    final = final.merge(poblacion, on="Fecha", how="left")
    final = final[final["Fecha"] >= pd.Timestamp("2006-08-07")].copy()
    final["cantidad"] = pd.to_numeric(final["cantidad"], errors="coerce").fillna(0)

    tipos = sorted(final["tipo_delito"].dropna().unique())
    tipo_delito = st.selectbox("Selecciona tipo delito:", ["TODOS"] + tipos, key="sec_tipo")
    if tipo_delito != "TODOS":
        final = final[final["tipo_delito"] == tipo_delito].copy()

    etiqueta_eje_x = st.selectbox("Selecciona periodo:", ["Mes Gobierno", "Trimestre Gobierno", "A\u00f1o Gobierno"], key="sec_periodo")
    eje_x = resolver_columna_periodo(final, etiqueta_eje_x)

    grafica = final.groupby(["Presidente", eje_x], as_index=False)["cantidad"].sum()
    grafica["Acumulado"] = grafica.groupby("Presidente")["cantidad"].cumsum()

    pob = final.groupby(["Presidente", eje_x], as_index=False)["Poblacion_Interpolada"].mean()
    grafica = grafica.merge(pob, on=["Presidente", eje_x], how="left")
    grafica["Tasa_100k"] = (grafica["cantidad"] / grafica["Poblacion_Interpolada"]) * 100000
    grafica["Acumulado_Tasa_100k"] = grafica.groupby("Presidente")["Tasa_100k"].cumsum()

    metrica_sec = st.selectbox(
        "Metrica para secuestro:",
        ["cantidad", "Tasa_100k"],
        key="sec_metrica",
    )
    metrica_acum_sec = "Acumulado" if metrica_sec == "cantidad" else "Acumulado_Tasa_100k"

    fig1 = px.line(grafica, x=eje_x, y=metrica_sec, color="Presidente", markers=True, title=f"Comparativo presidencial - {metrica_sec}")
    fig1.update_layout(hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.line(grafica, x=eje_x, y=metrica_acum_sec, color="Presidente", markers=True, title=f"Acumulado presidencial - {metrica_sec}")
    fig2.update_layout(hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)

    final_mapa = filtrar_datos_mapa(final, "sec")
    if final_mapa.empty:
        st.warning("No hay datos para los filtros seleccionados en mapas.")
    else:
        pintar_mapa_departamento(final_mapa, "Mapa coropletico por departamento")
        pintar_mapa_municipio(final_mapa, "Mapa coropletico por municipio")


def render_extorsion() -> None:
    st.title("Observatorio Presidencial")
    st.subheader("Extorsion en Colombia")

    with st.spinner("Cargando datos de Extorsion..."):
        df = descargar_csv_socrata("q2ib-t9am")

    if df.empty:
        st.error("No fue posible cargar los datos de Extorsion.")
        return

    presidentes = cargar_tabla_presidentes()
    poblacion = pd.read_excel(ROOT / "Secuestro" / "poblacion_interpolada_mensual_colombia.xlsx")

    df["fecha_hecho"] = pd.to_datetime(df["fecha_hecho"], errors="coerce")
    presidentes["Fecha"] = pd.to_datetime(presidentes["Fecha"], errors="coerce")
    poblacion["Fecha"] = pd.to_datetime(poblacion["Fecha"], errors="coerce")

    df["Fecha"] = df["fecha_hecho"].dt.to_period("M").dt.to_timestamp()
    presidentes["Fecha"] = presidentes["Fecha"].dt.to_period("M").dt.to_timestamp()
    poblacion["Fecha"] = poblacion["Fecha"].dt.to_period("M").dt.to_timestamp()

    final = df.merge(presidentes, on="Fecha", how="left")
    final = final.merge(poblacion, on="Fecha", how="left")
    final = final[final["Fecha"] >= pd.Timestamp("2006-08-07")].copy()
    final["cantidad"] = pd.to_numeric(final["cantidad"], errors="coerce").fillna(0)

    etiqueta_eje_x = st.selectbox("Selecciona periodo:", ["Mes Gobierno", "Trimestre Gobierno", "A\u00f1o Gobierno"], key="ext_periodo")
    eje_x = resolver_columna_periodo(final, etiqueta_eje_x)

    grafica = final.groupby(["Presidente", eje_x], as_index=False)["cantidad"].sum()
    grafica["Acumulado"] = grafica.groupby("Presidente")["cantidad"].cumsum()

    pob = final.groupby(["Presidente", eje_x], as_index=False)["Poblacion_Interpolada"].mean()
    grafica = grafica.merge(pob, on=["Presidente", eje_x], how="left")
    grafica["Tasa_100k"] = (grafica["cantidad"] / grafica["Poblacion_Interpolada"]) * 100000
    grafica["Acumulado_Tasa_100k"] = grafica.groupby("Presidente")["Tasa_100k"].cumsum()

    metrica_ext = st.selectbox(
        "Metrica para extorsion:",
        ["cantidad", "Tasa_100k"],
        key="ext_metrica",
    )
    metrica_acum_ext = "Acumulado" if metrica_ext == "cantidad" else "Acumulado_Tasa_100k"

    fig1 = px.line(grafica, x=eje_x, y=metrica_ext, color="Presidente", markers=True, title=f"Comparativo presidencial - {metrica_ext}")
    fig1.update_layout(hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.line(grafica, x=eje_x, y=metrica_acum_ext, color="Presidente", markers=True, title=f"Acumulado presidencial - {metrica_ext}")
    fig2.update_layout(hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)

    final_mapa = filtrar_datos_mapa(final, "ext")
    if final_mapa.empty:
        st.warning("No hay datos para los filtros seleccionados en mapas.")
    else:
        pintar_mapa_departamento(final_mapa, "Mapa coropletico por departamento")
        pintar_mapa_municipio(final_mapa, "Mapa coropletico por municipio")


def render_terrorismo() -> None:
    st.title("Observatorio Presidencial")
    st.subheader("Terrorismo en Colombia")

    with st.spinner("Cargando datos de Terrorismo..."):
        df = descargar_csv_socrata("yi5j-5fe9")

    if df.empty:
        st.error("No fue posible cargar los datos de Terrorismo.")
        return

    df = df[["fecha_hecho", "cod_depto", "departamento", "cod_muni", "municipio", "cantidad"]]
    df["fecha_hecho"] = pd.to_datetime(df["fecha_hecho"], errors="coerce")
    df["Fecha"] = df["fecha_hecho"].dt.to_period("M").dt.to_timestamp()
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0)
    df = df[df["Fecha"] >= pd.Timestamp("2006-08-07")]
    df = (
        df.groupby(["Fecha", "cod_depto", "departamento", "cod_muni", "municipio"], as_index=False)["cantidad"]
        .sum()
    )

    presidentes = cargar_tabla_presidentes()
    presidentes["Fecha"] = pd.to_datetime(presidentes["Fecha"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    presidentes = presidentes[["Fecha", "Presidente", "Mes Gobierno", "Trimestre Gobierno", "A\u00f1o Gobierno"]]

    poblacion = pd.read_excel(ROOT / "Secuestro" / "poblacion_interpolada_mensual_colombia.xlsx")
    poblacion["Fecha"] = pd.to_datetime(poblacion["Fecha"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    poblacion = poblacion[["Fecha", "Poblacion_Interpolada"]]

    final = df.merge(presidentes, on="Fecha", how="left")
    final = final.merge(poblacion, on="Fecha", how="left")

    etiqueta_eje_x = st.selectbox("Selecciona periodo:", ["Mes Gobierno", "Trimestre Gobierno", "A\u00f1o Gobierno"], key="ter_periodo")
    eje_x = resolver_columna_periodo(final, etiqueta_eje_x)

    grafica = final.groupby(["Presidente", eje_x], as_index=False)["cantidad"].sum()
    grafica["Acumulado"] = grafica.groupby("Presidente")["cantidad"].cumsum()

    pob = final.groupby(["Presidente", eje_x], as_index=False)["Poblacion_Interpolada"].mean()
    grafica = grafica.merge(pob, on=["Presidente", eje_x], how="left")
    grafica["Tasa_100k"] = (grafica["cantidad"] / grafica["Poblacion_Interpolada"]) * 100000
    grafica["Acumulado_Tasa_100k"] = grafica.groupby("Presidente")["Tasa_100k"].cumsum()

    metrica = st.selectbox("Metrica para terrorismo:", ["cantidad", "Tasa_100k"], key="ter_metrica")
    metrica_acum = "Acumulado" if metrica == "cantidad" else "Acumulado_Tasa_100k"

    fig1 = px.line(grafica, x=eje_x, y=metrica, color="Presidente", markers=True, title=f"Comparativo presidencial - {metrica}")
    fig1.update_layout(hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.line(grafica, x=eje_x, y=metrica_acum, color="Presidente", markers=True, title=f"Acumulado presidencial - {metrica}")
    fig2.update_layout(hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)

    final_mapa = filtrar_datos_mapa(final, "ter")
    if final_mapa.empty:
        st.warning("No hay datos para los filtros seleccionados en mapas.")
    else:
        pintar_mapa_departamento(final_mapa, "Mapa coropletico por departamento")
        pintar_mapa_municipio(final_mapa, "Mapa coropletico por municipio")


def render_vehiculos_hurtados() -> None:
    st.title("Observatorio Presidencial")
    st.subheader("Vehiculos Hurtados en Colombia")

    with st.spinner("Cargando datos de Vehiculos Hurtados..."):
        df = descargar_csv_socrata("csb4-y6v2")

    if df.empty:
        st.error("No fue posible cargar los datos de Vehiculos Hurtados.")
        return

    # Reducimos columnas y agregamos temprano para bajar consumo de memoria.
    columnas_base = ["fecha_hecho", "cod_depto", "departamento", "cod_muni", "municipio", "cantidad"]
    if "tipo_delito" in df.columns:
        columnas_base.insert(5, "tipo_delito")
    df = df[columnas_base]
    df["fecha_hecho"] = pd.to_datetime(df["fecha_hecho"], errors="coerce")
    df["Fecha"] = df["fecha_hecho"].dt.to_period("M").dt.to_timestamp()
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0)
    df = df[df["Fecha"] >= pd.Timestamp("2006-08-07")]
    group_cols = ["Fecha", "cod_depto", "departamento", "cod_muni", "municipio"]
    if "tipo_delito" in df.columns:
        group_cols.append("tipo_delito")
    df = df.groupby(group_cols, as_index=False)["cantidad"].sum()

    presidentes = cargar_tabla_presidentes()
    presidentes["Fecha"] = pd.to_datetime(presidentes["Fecha"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    presidentes = presidentes[["Fecha", "Presidente", "Mes Gobierno", "Trimestre Gobierno", "Año Gobierno"]]

    poblacion = pd.read_excel(ROOT / "Secuestro" / "poblacion_interpolada_mensual_colombia.xlsx")
    poblacion["Fecha"] = pd.to_datetime(poblacion["Fecha"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    poblacion = poblacion[["Fecha", "Poblacion_Interpolada"]]

    final = df.merge(presidentes, on="Fecha", how="left")
    final = final.merge(poblacion, on="Fecha", how="left")

    if "tipo_delito" in final.columns:
        tipos = sorted(final["tipo_delito"].dropna().unique())
        tipo_delito = st.selectbox("Selecciona tipo delito:", ["TODOS"] + tipos, key="veh_tipo")
        if tipo_delito != "TODOS":
            final = final[final["tipo_delito"] == tipo_delito]

    etiqueta_eje_x = st.selectbox("Selecciona periodo:", ["Mes Gobierno", "Trimestre Gobierno", "A\u00f1o Gobierno"], key="veh_periodo")
    eje_x = resolver_columna_periodo(final, etiqueta_eje_x)

    grafica = final.groupby(["Presidente", eje_x], as_index=False)["cantidad"].sum()
    grafica["Acumulado"] = grafica.groupby("Presidente")["cantidad"].cumsum()

    pob = final.groupby(["Presidente", eje_x], as_index=False)["Poblacion_Interpolada"].mean()
    grafica = grafica.merge(pob, on=["Presidente", eje_x], how="left")
    grafica["Tasa_100k"] = (grafica["cantidad"] / grafica["Poblacion_Interpolada"]) * 100000
    grafica["Acumulado_Tasa_100k"] = grafica.groupby("Presidente")["Tasa_100k"].cumsum()

    metrica_veh = st.selectbox(
        "Metrica para vehiculos hurtados:",
        ["cantidad", "Tasa_100k"],
        key="veh_metrica",
    )
    metrica_acum_veh = "Acumulado" if metrica_veh == "cantidad" else "Acumulado_Tasa_100k"

    fig1 = px.line(grafica, x=eje_x, y=metrica_veh, color="Presidente", markers=True, title=f"Comparativo presidencial - {metrica_veh}")
    fig1.update_layout(hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.line(grafica, x=eje_x, y=metrica_acum_veh, color="Presidente", markers=True, title=f"Acumulado presidencial - {metrica_veh}")
    fig2.update_layout(hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)

    final_mapa = filtrar_datos_mapa(final, "veh")
    if final_mapa.empty:
        st.warning("No hay datos para los filtros seleccionados en mapas.")
    else:
        pintar_mapa_departamento(final_mapa, "Mapa coropletico por departamento")
        pintar_mapa_municipio(final_mapa, "Mapa coropletico por municipio")


def render_hurtos_personas() -> None:
    st.title("Observatorio Presidencial")
    st.subheader("Hurtos a Personas en Colombia")
    st.markdown("""
### Sobre este indicador

Este conjunto de datos corresponde al delito de **hurto a personas** en Colombia, entendido como las modalidades de hurto donde el victimario utiliza diferentes medios con el fin de apoderarse de los elementos de valor que lleva consigo una persona. El indicador se mide en numero de victimas registradas.

En este panel se presentan:
- Casos totales registrados
- Tasas por cada 100.000 habitantes
- Evolucion historica del delito
- Comparaciones entre periodos presidenciales

Es importante tener en cuenta que los datos abiertos disponibles para este conjunto comienzan desde el ano 2003, por lo que el analisis historico inicia desde el segundo periodo presidencial de Alvaro Uribe Velez.

La informacion mostrada tiene fines informativos y analiticos. Los datos se presentan de manera objetiva y las conclusiones quedan abiertas a la interpretacion de cada persona.

### Fuente oficial de datos
- Datos Abiertos Colombia - Hurto Personas
- Ministerio de Defensa Nacional / Policia Nacional

https://www.datos.gov.co/Seguridad-y-Defensa/HURTO-PERSONAS/4rxi-8m8d/about_data
""")

    with st.spinner("Cargando datos de Hurtos a Personas..."):
        df = descargar_csv_socrata("4rxi-8m8d")

    if df.empty:
        st.error("No fue posible cargar los datos de Hurtos a Personas.")
        return

    df = df[["fecha_hecho", "cod_depto", "departamento", "cod_muni", "municipio", "cantidad"]]
    df["fecha_hecho"] = pd.to_datetime(df["fecha_hecho"], errors="coerce")
    df["Fecha"] = df["fecha_hecho"].dt.to_period("M").dt.to_timestamp()
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0)
    df = df[df["Fecha"] >= pd.Timestamp("2006-08-07")]
    df = (
        df.groupby(["Fecha", "cod_depto", "departamento", "cod_muni", "municipio"], as_index=False)["cantidad"]
        .sum()
    )

    presidentes = cargar_tabla_presidentes()
    presidentes["Fecha"] = pd.to_datetime(presidentes["Fecha"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    presidentes = presidentes[["Fecha", "Presidente", "Mes Gobierno", "Trimestre Gobierno", "A\u00f1o Gobierno"]]

    poblacion = pd.read_excel(ROOT / "Secuestro" / "poblacion_interpolada_mensual_colombia.xlsx")
    poblacion["Fecha"] = pd.to_datetime(poblacion["Fecha"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    poblacion = poblacion[["Fecha", "Poblacion_Interpolada"]]

    final = df.merge(presidentes, on="Fecha", how="left")
    final = final.merge(poblacion, on="Fecha", how="left")

    etiqueta_eje_x = st.selectbox("Selecciona periodo:", ["Mes Gobierno", "Trimestre Gobierno", "A\u00f1o Gobierno"], key="hp_periodo")
    eje_x = resolver_columna_periodo(final, etiqueta_eje_x)

    grafica = final.groupby(["Presidente", eje_x], as_index=False)["cantidad"].sum()
    grafica["Acumulado"] = grafica.groupby("Presidente")["cantidad"].cumsum()

    pob = final.groupby(["Presidente", eje_x], as_index=False)["Poblacion_Interpolada"].mean()
    grafica = grafica.merge(pob, on=["Presidente", eje_x], how="left")
    grafica["Tasa_100k"] = (grafica["cantidad"] / grafica["Poblacion_Interpolada"]) * 100000
    grafica["Acumulado_Tasa_100k"] = grafica.groupby("Presidente")["Tasa_100k"].cumsum()

    metrica_hp = st.selectbox(
        "Metrica para hurtos a personas:",
        ["cantidad", "Tasa_100k"],
        key="hp_metrica",
    )
    metrica_acum_hp = "Acumulado" if metrica_hp == "cantidad" else "Acumulado_Tasa_100k"

    fig1 = px.line(grafica, x=eje_x, y=metrica_hp, color="Presidente", markers=True, title=f"Comparativo presidencial - {metrica_hp}")
    fig1.update_layout(hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.line(grafica, x=eje_x, y=metrica_acum_hp, color="Presidente", markers=True, title=f"Acumulado presidencial - {metrica_hp}")
    fig2.update_layout(hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)

    final_mapa = filtrar_datos_mapa(final, "hp")
    if final_mapa.empty:
        st.warning("No hay datos para los filtros seleccionados en mapas.")
    else:
        pintar_mapa_departamento(final_mapa, "Mapa coropletico por departamento")
        pintar_mapa_municipio(final_mapa, "Mapa coropletico por municipio")


def render_hurto_residencias() -> None:
    st.title("Observatorio Presidencial")
    st.subheader("Hurto a Residencias en Colombia")

    with st.spinner("Cargando datos de Hurto a Residencias..."):
        df = descargar_csv_socrata("7mn7-vzqp")

    if df.empty:
        st.error("No fue posible cargar los datos de Hurto a Residencias.")
        return

    df = df[["fecha_hecho", "cod_depto", "departamento", "cod_muni", "municipio", "cantidad"]]
    df["fecha_hecho"] = pd.to_datetime(df["fecha_hecho"], errors="coerce")
    df["Fecha"] = df["fecha_hecho"].dt.to_period("M").dt.to_timestamp()
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0)
    df = df[df["Fecha"] >= pd.Timestamp("2006-08-07")]
    df = (
        df.groupby(["Fecha", "cod_depto", "departamento", "cod_muni", "municipio"], as_index=False)["cantidad"]
        .sum()
    )

    presidentes = cargar_tabla_presidentes()
    presidentes["Fecha"] = pd.to_datetime(presidentes["Fecha"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    presidentes = presidentes[["Fecha", "Presidente", "Mes Gobierno", "Trimestre Gobierno", "A\u00f1o Gobierno"]]

    poblacion = pd.read_excel(ROOT / "Secuestro" / "poblacion_interpolada_mensual_colombia.xlsx")
    poblacion["Fecha"] = pd.to_datetime(poblacion["Fecha"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    poblacion = poblacion[["Fecha", "Poblacion_Interpolada"]]

    final = df.merge(presidentes, on="Fecha", how="left")
    final = final.merge(poblacion, on="Fecha", how="left")

    etiqueta_eje_x = st.selectbox("Selecciona periodo:", ["Mes Gobierno", "Trimestre Gobierno", "A\u00f1o Gobierno"], key="res_periodo")
    eje_x = resolver_columna_periodo(final, etiqueta_eje_x)

    grafica = final.groupby(["Presidente", eje_x], as_index=False)["cantidad"].sum()
    grafica["Acumulado"] = grafica.groupby("Presidente")["cantidad"].cumsum()

    pob = final.groupby(["Presidente", eje_x], as_index=False)["Poblacion_Interpolada"].mean()
    grafica = grafica.merge(pob, on=["Presidente", eje_x], how="left")
    grafica["Tasa_100k"] = (grafica["cantidad"] / grafica["Poblacion_Interpolada"]) * 100000
    grafica["Acumulado_Tasa_100k"] = grafica.groupby("Presidente")["Tasa_100k"].cumsum()

    metrica = st.selectbox("Metrica para hurto a residencias:", ["cantidad", "Tasa_100k"], key="res_metrica")
    metrica_acum = "Acumulado" if metrica == "cantidad" else "Acumulado_Tasa_100k"

    fig1 = px.line(grafica, x=eje_x, y=metrica, color="Presidente", markers=True, title=f"Comparativo presidencial - {metrica}")
    fig1.update_layout(hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.line(grafica, x=eje_x, y=metrica_acum, color="Presidente", markers=True, title=f"Acumulado presidencial - {metrica}")
    fig2.update_layout(hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)

    final_mapa = filtrar_datos_mapa(final, "res")
    if final_mapa.empty:
        st.warning("No hay datos para los filtros seleccionados en mapas.")
    else:
        pintar_mapa_departamento(final_mapa, "Mapa coropletico por departamento")
        pintar_mapa_municipio(final_mapa, "Mapa coropletico por municipio")


def render_hurto_comercio() -> None:
    st.title("Observatorio Presidencial")
    st.subheader("Hurto a Comercio en Colombia")

    with st.spinner("Cargando datos de Hurto a Comercio..."):
        df = descargar_csv_socrata("7i2x-h5vp")

    if df.empty:
        st.error("No fue posible cargar los datos de Hurto a Comercio.")
        return

    df = df[["fecha_hecho", "cod_depto", "departamento", "cod_muni", "municipio", "cantidad"]]
    df["fecha_hecho"] = pd.to_datetime(df["fecha_hecho"], errors="coerce")
    df["Fecha"] = df["fecha_hecho"].dt.to_period("M").dt.to_timestamp()
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0)
    df = df[df["Fecha"] >= pd.Timestamp("2006-08-07")]
    df = (
        df.groupby(["Fecha", "cod_depto", "departamento", "cod_muni", "municipio"], as_index=False)["cantidad"]
        .sum()
    )

    presidentes = cargar_tabla_presidentes()
    presidentes["Fecha"] = pd.to_datetime(presidentes["Fecha"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    presidentes = presidentes[["Fecha", "Presidente", "Mes Gobierno", "Trimestre Gobierno", "A\u00f1o Gobierno"]]

    poblacion = pd.read_excel(ROOT / "Secuestro" / "poblacion_interpolada_mensual_colombia.xlsx")
    poblacion["Fecha"] = pd.to_datetime(poblacion["Fecha"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    poblacion = poblacion[["Fecha", "Poblacion_Interpolada"]]

    final = df.merge(presidentes, on="Fecha", how="left")
    final = final.merge(poblacion, on="Fecha", how="left")

    etiqueta_eje_x = st.selectbox("Selecciona periodo:", ["Mes Gobierno", "Trimestre Gobierno", "A\u00f1o Gobierno"], key="com_periodo")
    eje_x = resolver_columna_periodo(final, etiqueta_eje_x)

    grafica = final.groupby(["Presidente", eje_x], as_index=False)["cantidad"].sum()
    grafica["Acumulado"] = grafica.groupby("Presidente")["cantidad"].cumsum()

    pob = final.groupby(["Presidente", eje_x], as_index=False)["Poblacion_Interpolada"].mean()
    grafica = grafica.merge(pob, on=["Presidente", eje_x], how="left")
    grafica["Tasa_100k"] = (grafica["cantidad"] / grafica["Poblacion_Interpolada"]) * 100000
    grafica["Acumulado_Tasa_100k"] = grafica.groupby("Presidente")["Tasa_100k"].cumsum()

    metrica = st.selectbox("Metrica para hurto a comercio:", ["cantidad", "Tasa_100k"], key="com_metrica")
    metrica_acum = "Acumulado" if metrica == "cantidad" else "Acumulado_Tasa_100k"

    fig1 = px.line(grafica, x=eje_x, y=metrica, color="Presidente", markers=True, title=f"Comparativo presidencial - {metrica}")
    fig1.update_layout(hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.line(grafica, x=eje_x, y=metrica_acum, color="Presidente", markers=True, title=f"Acumulado presidencial - {metrica}")
    fig2.update_layout(hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)

    final_mapa = filtrar_datos_mapa(final, "com")
    if final_mapa.empty:
        st.warning("No hay datos para los filtros seleccionados en mapas.")
    else:
        pintar_mapa_departamento(final_mapa, "Mapa coropletico por departamento")
        pintar_mapa_municipio(final_mapa, "Mapa coropletico por municipio")


def render_homicidios() -> None:
    st.title("Observatorio Presidencial")
    st.subheader("Homicidios en Colombia")
    with st.expander("Descripcion del indicador", expanded=False):
        st.markdown(
            """
Analisis del delito de homicidio con datos abiertos oficiales de Colombia.
Incluye comparativos presidenciales, acumulados y tasa por 100.000 habitantes.
"""
        )

    with st.spinner("Cargando datos de Homicidios..."):
        df = descargar_csv_socrata("m8fd-ahd9")

    if df.empty:
        st.error("No fue posible cargar los datos de Homicidios.")
        return

    df = df[["fecha_hecho", "cod_depto", "departamento", "cod_muni", "municipio", "cantidad"]]
    df["fecha_hecho"] = pd.to_datetime(df["fecha_hecho"], errors="coerce")
    df["Fecha"] = df["fecha_hecho"].dt.to_period("M").dt.to_timestamp()
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0)
    df = df[df["Fecha"] >= pd.Timestamp("2006-08-07")]
    df = (
        df.groupby(["Fecha", "cod_depto", "departamento", "cod_muni", "municipio"], as_index=False)["cantidad"]
        .sum()
    )

    presidentes = cargar_tabla_presidentes()
    presidentes["Fecha"] = pd.to_datetime(presidentes["Fecha"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    presidentes = presidentes[["Fecha", "Presidente", "Mes Gobierno", "Trimestre Gobierno", "Año Gobierno"]]

    poblacion = pd.read_excel(ROOT / "Secuestro" / "poblacion_interpolada_mensual_colombia.xlsx")
    poblacion["Fecha"] = pd.to_datetime(poblacion["Fecha"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    poblacion = poblacion[["Fecha", "Poblacion_Interpolada"]]

    final = df.merge(presidentes, on="Fecha", how="left")
    final = final.merge(poblacion, on="Fecha", how="left")

    etiqueta_eje_x = st.selectbox(
        "Selecciona periodo:",
        ["Año Gobierno", "Trimestre Gobierno", "Mes Gobierno"],
        key="hom_periodo",
    )
    eje_x = resolver_columna_periodo(final, etiqueta_eje_x)

    grafica = final.groupby(["Presidente", eje_x], as_index=False)["cantidad"].sum()
    grafica["Acumulado"] = grafica.groupby("Presidente")["cantidad"].cumsum()

    pob = final.groupby(["Presidente", eje_x], as_index=False)["Poblacion_Interpolada"].mean()
    grafica = grafica.merge(pob, on=["Presidente", eje_x], how="left")
    grafica["Tasa_100k"] = (grafica["cantidad"] / grafica["Poblacion_Interpolada"]) * 100000
    grafica["Acumulado_Tasa_100k"] = grafica.groupby("Presidente")["Tasa_100k"].cumsum()

    metrica = st.selectbox("Metrica para homicidios:", ["cantidad", "Tasa_100k"], key="hom_metrica")
    metrica_acum = "Acumulado" if metrica == "cantidad" else "Acumulado_Tasa_100k"

    fig1 = px.line(grafica, x=eje_x, y=metrica, color="Presidente", markers=True, title=f"Comparativo presidencial - {metrica}")
    fig1.update_layout(hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True)

    fig2 = px.line(grafica, x=eje_x, y=metrica_acum, color="Presidente", markers=True, title=f"Acumulado presidencial - {metrica}")
    fig2.update_layout(hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)

    final_mapa = filtrar_datos_mapa(final, "hom")
    if final_mapa.empty:
        st.warning("No hay datos para los filtros seleccionados en mapas.")
    else:
        pintar_mapa_departamento(final_mapa, "Mapa coropletico por departamento")
        pintar_mapa_municipio(final_mapa, "Mapa coropletico por municipio")


def render_economicos() -> None:
    st.title("Indicadores Economicos")
    st.info(
        "Estamos buscando y validando fuentes economicas que permitan integracion por API para actualizar este modulo."
    )
    st.markdown(
        """
### Estado actual
- DANE: muchas series oficiales estan en documentos/boletines descargables y no siempre en API publica directa.
- Datos Abiertos Colombia: hay conjuntos utiles, pero no siempre incluyen todos los indicadores macro clave.

### Indicadores relevantes que estamos priorizando
- PIB (crecimiento real y nominal)
- IPC (inflacion)
- Deuda externa
- Tasa de desempleo
- Tipo de cambio
- Balanza comercial
- Tasa de interes de politica monetaria
- Pobreza monetaria
"""
    )


st.sidebar.title("Menu")
if "nav_actual" not in st.session_state:
    st.session_state["nav_actual"] = "Inicio"

def nav_btn(label: str, target: str, key: str) -> None:
    estilo = "primary" if st.session_state["nav_actual"] == target else "secondary"
    if st.button(label, key=key, use_container_width=True, type=estilo):
        st.session_state["nav_actual"] = target

with st.sidebar:
    st.markdown("### Inicio")
    nav_btn("Inicio", "Inicio", "nav_inicio")

    with st.expander("Seguridad", expanded=True):
        with st.expander("Seguridad Ciudadana", expanded=True):
            nav_btn("Hurtos a Personas", "Hurtos a Personas", "nav_hp")
            nav_btn("Hurto a Comercio", "Hurto a Comercio", "nav_com")
            nav_btn("Hurto a Residencias", "Hurto a Residencias", "nav_res")
            nav_btn("Vehiculos Hurtados", "Vehiculos Hurtados", "nav_veh")

        with st.expander("Seguridad del Estado", expanded=True):
            nav_btn("Fuerza Publica", "Fuerza Publica", "nav_fp")
            nav_btn("Terrorismo", "Terrorismo", "nav_ter")
            nav_btn("Secuestro", "Secuestro", "nav_sec")
            nav_btn("Extorsion", "Extorsion", "nav_ext")
            nav_btn("Homicidios", "Homicidios", "nav_hom")

    with st.expander("Economicos", expanded=False):
        nav_btn("Ver indicadores economicos", "Economicos", "nav_eco")

seleccion = st.session_state["nav_actual"]

if seleccion == "Inicio":
    render_inicio()
elif seleccion == "Fuerza Publica":
    render_fuerza_publica()
elif seleccion == "Secuestro":
    render_secuestro()
elif seleccion == "Terrorismo":
    render_terrorismo()
elif seleccion == "Extorsion":
    render_extorsion()
elif seleccion == "Vehiculos Hurtados":
    render_vehiculos_hurtados()
elif seleccion == "Hurto a Comercio":
    render_hurto_comercio()
elif seleccion == "Hurto a Residencias":
    render_hurto_residencias()
elif seleccion == "Homicidios":
    render_homicidios()
elif seleccion == "Economicos":
    render_economicos()
else:
    render_hurtos_personas()
