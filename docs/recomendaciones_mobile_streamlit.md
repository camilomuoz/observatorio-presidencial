# Mejoras recomendadas para vista móvil y estabilidad

## Vista móvil

La app actual usa `st.sidebar` para navegación. En celular, Streamlit suele esconder el sidebar detrás de un menú, lo que hace menos intuitivo navegar y cambiar filtros.

### Cambio recomendado en `app.py`

Agregar una función de navegación que permita usar controles en el cuerpo principal cuando el usuario esté en celular:

```python
def render_navigation():
    st.sidebar.title("Menu")
    vista_sidebar = st.sidebar.radio("Vista:", ["Inicio", "Seguridad"], key="vista_sidebar")

    st.markdown("### Navegación")
    with st.expander("Abrir menú", expanded=False):
        vista_mobile = st.radio("Vista:", ["Inicio", "Seguridad"], key="vista_mobile")

    vista = vista_mobile if vista_mobile else vista_sidebar
    return vista
```

Sin embargo, Streamlit no detecta nativamente el ancho de pantalla sin componentes adicionales. Por eso, la solución más estable sin dependencias externas es mostrar una navegación alternativa dentro del cuerpo de la página y mantener el sidebar para escritorio.

## Filtros de mapas

La función `filtrar_datos_mapa` debería envolver sus controles en un `st.expander` para que en celular no ocupen toda la pantalla:

```python
def filtrar_datos_mapa(df: pd.DataFrame, key_prefix: str) -> pd.DataFrame:
    with st.expander("Filtros de mapa", expanded=False):
        st.caption("Estos filtros solo afectan los mapas coropléticos.")
        # aquí van los selectbox existentes
```

## Carga de datos y estabilidad

La función `descargar_csv_socrata` consulta Datos Abiertos Colombia por bloques. Cuando Streamlit despierta después de inactividad, debe reconstruir el cache y puede parecer caído.

### Cambio recomendado

```python
@st.cache_data(show_spinner=False, ttl=3600)
def descargar_csv_socrata(resource_id: str, limit: int = 50000) -> pd.DataFrame:
    offset = 0
    bloques = []

    try:
        while True:
            url = (
                f"https://www.datos.gov.co/resource/{resource_id}.csv?"
                f"$limit={limit}&$offset={offset}"
            )
            parte = pd.read_csv(url, timeout=60)
            if parte.empty:
                break
            bloques.append(parte)
            offset += limit
    except Exception as exc:
        st.warning("Estamos recuperando la información desde Datos Abiertos. Intenta recargar en unos segundos.")
        return pd.DataFrame()

    if not bloques:
        return pd.DataFrame()

    return pd.concat(bloques, ignore_index=True)
```

## Despliegue

Si la app está desplegada en Streamlit Community Cloud desde GitHub, cada push a la rama conectada normalmente dispara un redeploy automático. Si no se actualiza, revisar:

1. Que el despliegue apunte a la rama `main`.
2. Que el archivo principal configurado sea `app.py`.
3. Que no haya errores en los logs de Streamlit Cloud.
4. Que el repositorio tenga los archivos y dependencias actualizados.

## Próximo paso técnico

Crear un PR que modifique `app.py` con:

- `ttl=3600` en caches de datos.
- Manejo de errores en descarga Socrata.
- Navegación alternativa en cuerpo principal para móvil.
- Filtros de mapa dentro de `st.expander`.
