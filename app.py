import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de la página
st.set_page_config(page_title="Dashboard Humedad del Aire", page_icon="🌤️", layout="wide")

st.title("🌤️ Analisis de Datos Sobre la Humedad del Aire en Bogotá")
st.write("Análisis interactivo de variables meteorológicas y humedad atmosférica por estaciones.")

st.sidebar.header("1. Carga de Datos")
archivo_csv = st.sidebar.file_uploader("Sube tu archivo DatosBogotaAct2.csv", type=["csv"])

if archivo_csv is not None:
    # 2. LECTURA Y LIMPIEZA FORZADA DE DATOS
    @st.cache_data
    def cargar_y_limpiar(file):
        datos = pd.read_csv(file)
        
        # Limpieza de coordenadas y valores de humedad
        for col in ['ValorObservado', 'Latitud', 'Longitud']:
            datos[col] = datos[col].astype(str).str.replace(',', '.', regex=False)
            datos[col] = pd.to_numeric(datos[col], errors='coerce')
            
        # Tratamiento de fechas y extracción de horas para el análisis del aire
        datos['FechaObservacion'] = pd.to_datetime(datos['FechaObservacion'])
        datos['Fecha'] = datos['FechaObservacion'].dt.date
        datos['Hora'] = datos['FechaObservacion'].dt.hour # Extrae la hora (0 - 23)
        return datos

    df = cargar_y_limpiar(archivo_csv)

    # 3. FILTROS EN LA BARRA LATERAL
    st.sidebar.header("2. Filtros del Dashboard")
    
    estaciones_disponibles = sorted(df['NombreEstacion'].dropna().unique().tolist())
    estaciones_seleccionadas = st.sidebar.multiselect(
        "Selecciona las Estaciones:",
        options=estaciones_disponibles,
        default=estaciones_disponibles
    )
    
    min_fecha = df['Fecha'].min()
    max_fecha = df['Fecha'].max()
    
    fechas_seleccionadas = st.sidebar.date_input(
        "Selecciona el Rango de Fechas:",
        value=(min_fecha, max_fecha),
        min_value=min_fecha,
        max_value=max_fecha
    )

    # 4. APLICACIÓN DE FILTROS
    df_filtrado = df[df['NombreEstacion'].isin(estaciones_seleccionadas)]
    
    if isinstance(fechas_seleccionadas, tuple) and len(fechas_seleccionadas) == 2:
        fecha_inicio, fecha_fin = fechas_seleccionadas
        df_filtrado = df_filtrado[(df_filtrado['Fecha'] >= fecha_inicio) & (df_filtrado['Fecha'] <= fecha_fin)]

    if df_filtrado.empty:
        st.warning("⚠️ No hay datos disponibles para la combinación de filtros seleccionada.")
    else:
        # 5. TARJETAS DE MÉTRICAS PRINCIPALES
        st.markdown("### Indicadores Principales del Aire")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        kpi1.metric(label="Total de Mediciones", value=f"{len(df_filtrado):,}")
        kpi2.metric(label="Humedad Relativa Promedio", value=f"{df_filtrado['ValorObservado'].mean():.2f}%")
        kpi3.metric(label="Humedad Máxima Registrada", value=f"{df_filtrado['ValorObservado'].max():.2f}%")
        kpi4.metric(label="Estaciones Monitoreadas", value=df_filtrado['NombreEstacion'].nunique())
        
        st.markdown("---")

        # ==========================================
        # GRÁFICOS (ORDENADOS UNO DEBAJO DEL OTRO)
        # ==========================================

        # Gráfico 1: Barras Horizontales
        st.markdown("#### 1. Promedio de la Humedad por Estación")
        df_promedio = df_filtrado.groupby('NombreEstacion')['ValorObservado'].mean().reset_index()
        df_promedio = df_promedio.sort_values(by='ValorObservado', ascending=True) 
        
        fig_bar = px.bar(df_promedio, x='ValorObservado', y='NombreEstacion', orientation='h',
                         text='ValorObservado', color='ValorObservado',
                         color_continuous_scale="Blues", height=500,
                         labels={"ValorObservado": "Humedad Promedio (%)", "NombreEstacion": "Estación"})
        fig_bar.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_bar.update_layout(template="plotly_white", coloraxis_showscale=False)
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")

        # Gráfico 2: Evolución de Líneas Temporal (Histórico Diario)
        st.markdown("#### 2. Evolución Histórica de la Humedad en el Tiempo")
        df_diario = df_filtrado.groupby(['Fecha', 'NombreEstacion'])['ValorObservado'].mean().reset_index()
        
        fig_line = px.line(df_diario, x='Fecha', y='ValorObservado', color='NombreEstacion', height=500,
                           labels={"ValorObservado": "Humedad (%)", "Fecha": "Fecha de Observación"})
        fig_line.update_layout(template="plotly_white")
        st.plotly_chart(fig_line, use_container_width=True)

        st.markdown("---")

        # Gráfico 3: NUEVO GRÁFICO - Ciclo Diario / Comportamiento por Hora (Clave para Humedad del Aire)
        st.markdown("#### 3. Ciclo Diario: Variación de Humedad según la Hora del Día")
        df_horario = df_filtrado.groupby(['Hora', 'NombreEstacion'])['ValorObservado'].mean().reset_index()
        
        fig_hora = px.line(df_horario, x='Hora', y='ValorObservado', color='NombreEstacion', height=500,
                           title="Comportamiento promedio de las 0:00 a las 23:00 hrs",
                           labels={"ValorObservado": "Humedad Promedio (%)", "Hora": "Hora del Día (Formato 24h)"})
        fig_hora.update_layout(template="plotly_white", xaxis=dict(tickmode='linear', tick0=0, dtick=2))
        st.plotly_chart(fig_hora, use_container_width=True)

        st.markdown("---")

        # Gráfico 4: Mapa Geográfico
        st.markdown("#### 4. Distribución Geográfica de la Humedad")
        df_mapa = df_filtrado.groupby(['NombreEstacion', 'Latitud', 'Longitud'])['ValorObservado'].mean().reset_index()
        
        fig_mapa = px.scatter_mapbox(df_mapa, lat="Latitud", lon="Longitud", hover_name="NombreEstacion",
                                     color="ValorObservado", size="ValorObservado",
                                     color_continuous_scale="Blues", mapbox_style="carto-positron", zoom=9, height=550)
        st.plotly_chart(fig_mapa, use_container_width=True)

        st.markdown("---")

        # Gráfico 5: Gráfico Circular (Torta)
        st.markdown("#### 5. Distribución de los Registros Totales por Estación")
        df_conteo = df_filtrado['NombreEstacion'].value_counts().reset_index()
        df_conteo.columns = ['NombreEstacion', 'Conteo']
        
        fig_pie = px.pie(df_conteo, values='Conteo', names='NombreEstacion', hole=0.4,
                         color_discrete_sequence=px.colors.sequential.Blues_r, height=500)
        fig_pie.update_layout(template="plotly_white")
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("---")

        # Gráfico 6: Histograma de Frecuencias
        st.markdown("#### 6. Histograma: Frecuencia de los Niveles de Humedad")
        
        fig_hist = px.histogram(df_filtrado, x="ValorObservado", nbins=40,
                                labels={"ValorObservado": "Humedad (%)"},
                                color_discrete_sequence=['#1f77b4'], height=500)
        fig_hist.update_layout(template="plotly_white", bargap=0.05)
        st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown("---")

        # ==========================================
        # NUEVA SECCIÓN: TABLA DE DATOS (1000 REGISTROS)
        # ==========================================
        st.markdown("#### 📋 Vista de los Primeros 1000 Registros Filtrados")
        st.write("A continuación se presentan las primeras 1,000 filas de datos correspondientes a los filtros aplicados en la barra lateral.")
        
        # Seleccionamos columnas clave para mostrar de forma limpia y ordenada
        columnas_visibles = ['ID', 'NombreEstacion', 'FechaObservacion', 'Hora', 'ValorObservado', 'UnidadMedida', 'Latitud', 'Longitud']
        df_tabla = df_filtrado[columnas_visibles].head(1000).reset_index(drop=True)
        
        st.dataframe(df_tabla, use_container_width=True, height=400)

else:
    st.info("Sube el archivo CSV desde la barra lateral para visualizar el dashboard interactivo.")