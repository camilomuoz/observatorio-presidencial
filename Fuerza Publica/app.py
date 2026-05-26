import pandas as pd
import plotly.express as px
import streamlit as st

# ==================================================
# TITULO
# ==================================================

st.title("Observatorio Presidencial")

st.subheader(
    "AFECTACIÓN DE MIEMBROS DE LA FUERZA PÚBLICA"
)

st.markdown(
    """
Corresponde a los homicidios y lesiones que reporta la Fuerza Pública
(Ejército Nacional, Armada Nacional, Fuerza Aérea y Policía Nacional)
en cumplimiento de su deber constitucional o actos de servicio,
excluyendo vacaciones, permisos y licencias.
"""
)

st.markdown(
    """
**Fuente oficial:**  
[Datos Abiertos Colombia - Afectación de miembros de la Fuerza Pública](https://www.datos.gov.co/Seguridad-y-Defensa/AFECTACI-N-DE-MIEMBROS-DE-LA-FUERZA-P-BLICA/8rpn-wpty/about_data)
"""
)

st.markdown(
    """
### Revisión metodológica

Para efectos de comparabilidad entre gobiernos, este análisis
considera únicamente periodos equivalentes de mandato presidencial.

El dataset oficial utilizado inicia en el año 2010, por lo cual
no se incluye el segundo periodo presidencial completo de Álvaro Uribe Vélez,
ya que no existe información homogénea para todo su mandato dentro
de esta fuente de datos.

En consecuencia, las comparaciones presentadas corresponden a:

- Juan Manuel Santos (primer periodo presidencial)
- Juan Manuel Santos (segundo periodo presidencial)
- Iván Duque Márquez
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

    # SI YA NO HAY DATOS → TERMINA
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

presidentes = pd.read_excel(
    "tabla_presidentes_gobierno_2000_2026.xlsx"
)

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

eje_x = st.selectbox(
    "Selecciona periodo:",
    [
        "Mes Gobierno",
        "Trimestre Gobierno",
        "Año Gobierno"
    ]
)

# ==================================================
# 9. AGRUPAR
# ==================================================

grafica = (
    final.groupby(
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