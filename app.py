import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout='wide')

# --- Cargar datos ---
@st.cache_data
def load_data(file_path):
    df = pd.read_csv(file_path)
    # Convertir 'Fin de vigencia' a datetime y manejar 'No especificado'
    df['Fin de vigencia'] = pd.to_datetime(df['Fin de vigencia'], errors='coerce')
    # Asegurarse de que 'Ramos' se llame 'Ramo' para consistencia con la solicitud del usuario
    if 'Ramos' in df.columns and 'Ramo' not in df.columns:
        df.rename(columns={'Ramos': 'Ramo'}, inplace=True)
    return df

file_path = 'aseguradoras_limpio.csv'
df = load_data(file_path)

# Verificar si 'Prima neta' es numérica, si no, intentar convertirla y manejar 'No especificado'
if df['Prima neta'].dtype == 'object':
    df['Prima neta'] = pd.to_numeric(df['Prima neta'].str.replace(',', ''), errors='coerce')
    df['Prima neta'].fillna(0, inplace=True) # Rellenar NaNs con 0 después de la conversión

# --- Sidebar para filtros ---
st.sidebar.header('Filtros')

# Filtro por Ramo
ramos_unicos = ['Todos'] + sorted(df['Ramo'].unique().tolist())
selected_ramo = st.sidebar.multiselect('Selecciona Ramo(s):', ramos_unicos, default='Todos')

# Filtro por Aseguradora
aseguradoras_unicas = ['Todos'] + sorted(df['Aseguradora'].unique().tolist())
selected_aseguradora = st.sidebar.multiselect('Selecciona Aseguradora(s):', aseguradoras_unicas, default='Todos')

# Aplicar filtros
df_filtered = df.copy()

if 'Todos' not in selected_ramo:
    df_filtered = df_filtered[df_filtered['Ramo'].isin(selected_ramo)]

if 'Todos' not in selected_aseguradora:
    df_filtered = df_filtered[df_filtered['Aseguradora'].isin(selected_aseguradora)]

# --- Título principal ---
st.title('Dashboard de Pólizas y Ventas de Aseguradoras')

# --- Tarjetas de Aseguradoras que generan más ingresos ---
st.markdown('### Aseguradoras con mayores ingresos (Prima Neta)')

if not df_filtered.empty:
    top_aseguradoras = df_filtered.groupby('Aseguradora')['Prima neta'].sum().nlargest(5).reset_index()
    cols = st.columns(len(top_aseguradoras))
    for i, (idx, row) in enumerate(top_aseguradoras.iterrows()):
        with cols[i]:
            st.metric(label=row['Aseguradora'], value=f"${row['Prima neta']:,.2f}")
else:
    st.warning('No hay datos para mostrar con los filtros aplicados.')

st.markdown('---')

# --- Gráficas interactivas ---
col1, col2 = st.columns(2)

with col1:
    st.markdown('### Ventas agrupadas por Ramo')
    if not df_filtered.empty:
        ventas_por_ramo = df_filtered.groupby('Ramo')['Prima neta'].sum().reset_index()
        fig_ramo = px.bar(ventas_por_ramo, x='Ramo', y='Prima neta', 
                           title='Total de Prima Neta por Ramo',
                           color='Ramo', template='plotly_white')
        fig_ramo.update_layout(showlegend=False)
        st.plotly_chart(fig_ramo, use_container_width=True)
    else:
        st.info('Selecciona filtros para ver las ventas por Ramo.')

with col2:
    st.markdown('### Ventas agrupadas por Aseguradora')
    if not df_filtered.empty:
        ventas_por_aseguradora = df_filtered.groupby('Aseguradora')['Prima neta'].sum().reset_index()
        fig_aseguradora = px.bar(ventas_por_aseguradora, x='Aseguradora', y='Prima neta', 
                                 title='Total de Prima Neta por Aseguradora',
                                 color='Aseguradora', template='plotly_white')
        fig_aseguradora.update_layout(showlegend=False)
        st.plotly_chart(fig_aseguradora, use_container_width=True)
    else:
        st.info('Selecciona filtros para ver las ventas por Aseguradora.')

st.markdown('---')

# --- Gráfica de líneas para incremento de ventas por año (2023, 2024, 2025) ---
st.markdown('### Proyección de incremento de ventas por aseguradora (2023-2025)')

if not df_filtered.empty and 'Fin de vigencia' in df_filtered.columns:
    # Extraer el año de 'Fin de vigencia'
    df_filtered['Año'] = df_filtered['Fin de vigencia'].dt.year

    # Calcular ventas para 2023 (y cualquier año presente en los datos)
    ventas_actuales_anuales = df_filtered.groupby(['Aseguradora', 'Año'])['Prima neta'].sum().reset_index()

    # Proyección para 2024 y 2025 (ejemplo simple)
    # Asumimos un 10% de crecimiento anual sobre el último año de datos disponible (ej. 2023)
    # Si no hay datos de 2023, tomamos el año máximo disponible
    max_year_data = ventas_actuales_anuales['Año'].max() if not ventas_actuales_anuales.empty else 2023 # Default a 2023 si no hay datos

    df_proyeccion = ventas_actuales_anuales.copy()

    # Si max_year_data es inferior a 2023, asumimos 2023 como base para proyección
    if max_year_data < 2023: 
        # Si no hay datos en 2023, creamos una base hipotética o usamos el año más cercano
        st.warning(f"Los datos disponibles no llegan a 2023. Proyectando desde {max_year_data}. Considere ajustar la lógica de proyección.")
        # Para este ejemplo, si no hay 2023, tomamos el total general del último año y lo usamos como base para 2023
        base_2023_data = df_filtered.groupby('Aseguradora')['Prima neta'].sum().reset_index()
        base_2023_data['Año'] = 2023
        df_proyeccion = pd.concat([df_proyeccion, base_2023_data], ignore_index=True)
        df_proyeccion = df_proyeccion.drop_duplicates(subset=['Aseguradora', 'Año'], keep='last') # Mantener la de 2023 si se generó

    for aseguradora in df_proyeccion['Aseguradora'].unique():
        sales_2023_row = df_proyeccion[(df_proyeccion['Aseguradora'] == aseguradora) & (df_proyeccion['Año'] == 2023)]
        sales_2023 = sales_2023_row['Prima neta'].sum() if not sales_2023_row.empty else 0

        if sales_2023 == 0:
             # Si no hay ventas en 2023, podemos usar el promedio de los años disponibles o asumir una base.
            avg_sales = df_proyeccion[df_proyeccion['Aseguradora'] == aseguradora]['Prima neta'].mean()
            sales_2023 = avg_sales if not pd.isna(avg_sales) else 100000 # Base si no hay datos


        # Proyectar para 2024
        sales_2024 = sales_2023 * 1.10  # 10% de crecimiento
        df_proyeccion = pd.concat([df_proyeccion, pd.DataFrame([{'Aseguradora': aseguradora, 'Año': 2024, 'Prima neta': sales_2024}])], ignore_index=True)

        # Proyectar para 2025
        sales_2025 = sales_2024 * 1.10  # Otro 10% de crecimiento
        df_proyeccion = pd.concat([df_proyeccion, pd.DataFrame([{'Aseguradora': aseguradora, 'Año': 2025, 'Prima neta': sales_2025}])], ignore_index=True)

    fig_incremento = px.line(df_proyeccion, x='Año', y='Prima neta', color='Aseguradora',
                             title='Proyección de Ventas (Prima Neta) por Aseguradora (2023-2025)',
                             markers=True, template='plotly_white')
    st.plotly_chart(fig_incremento, use_container_width=True)
else:
    st.info('No hay suficientes datos para la proyección de ventas por año o la columna "Fin de vigencia" no está disponible.')

st.markdown('---')

# --- Visualización de ventas distribuidas por Moneda ---
st.markdown('### Distribución de Ventas por Divisa')

if not df_filtered.empty:
    ventas_por_divisa = df_filtered.groupby('Divisa')['Prima neta'].sum().reset_index()
    fig_divisa = px.pie(ventas_por_divisa, values='Prima neta', names='Divisa',
                        title='Distribución de Prima Neta por Divisa',
                        hole=0.3, template='plotly_white')
    st.plotly_chart(fig_divisa, use_container_width=True)
else:
    st.info('Selecciona filtros para ver la distribución de ventas por Divisa.')