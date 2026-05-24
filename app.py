import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout='wide')

# --- Cargar datos ---
@st.cache_data
def load_data(file_path):
    df = pd.read_csv(file_path)
    
    # Convertir 'Fin de vigencia' a datetime y manejar errores
    if 'Fin de vigencia' in df.columns:
        df['Fin de vigencia'] = pd.to_datetime(df['Fin de vigencia'], errors='coerce')
        
    # Asegurarse de que 'Ramos' se llame 'Ramo'
    if 'Ramos' in df.columns and 'Ramo' not in df.columns:
        df.rename(columns={'Ramos': 'Ramo'}, inplace=True)
        
    # --- LIMPIEZA AGRESIVA DE PRIMA NETA ---
    if 'Prima neta' in df.columns:
        # Convertir a texto, quitar signos de $, comas y espacios vacíos
        df['Prima neta'] = df['Prima neta'].astype(str).str.replace('$', '', regex=False)
        df['Prima neta'] = df['Prima neta'].str.replace(',', '', regex=False)
        df['Prima neta'] = df['Prima neta'].str.strip()
        
        # Convertir a número, si hay textos raros los vuelve NaN y luego esos NaN los hace 0
        df['Prima neta'] = pd.to_numeric(df['Prima neta'], errors='coerce')
        df['Prima neta'] = df['Prima neta'].fillna(0)
        
    return df

# USAMOS EL NOMBRE QUE TIENE TU ARCHIVO EN GITHUB
file_path = 'datos_limpios.csv'
df = load_data(file_path)

# --- Sidebar para filtros ---
st.sidebar.header('Filtros')

# Filtro por Ramo
ramos_unicos = ['Todos'] + sorted(df['Ramo'].unique().tolist()) if 'Ramo' in df.columns else ['Todos']
selected_ramo = st.sidebar.multiselect('Selecciona Ramo(s):', ramos_unicos, default='Todos')

# Filtro por Aseguradora
aseguradoras_unicas = ['Todos'] + sorted(df['Aseguradora'].unique().tolist()) if 'Aseguradora' in df.columns else ['Todos']
selected_aseguradora = st.sidebar.multiselect('Selecciona Aseguradora(s):', aseguradoras_unicas, default='Todos')

# Aplicar filtros
df_filtered = df.copy()

if 'Todos' not in selected_ramo and 'Ramo' in df_filtered.columns:
    df_filtered = df_filtered[df_filtered['Ramo'].isin(selected_ramo)]

if 'Todos' not in selected_aseguradora and 'Aseguradora' in df_filtered.columns:
    df_filtered = df_filtered[df_filtered['Aseguradora'].isin(selected_aseguradora)]

# --- Título principal ---
st.title('Dashboard de Pólizas y Ventas de Aseguradoras')

# --- Tarjetas de Aseguradoras que generan más ingresos ---
st.markdown('### Aseguradoras con mayores ingresos (Prima Neta)')

if not df_filtered.empty and 'Aseguradora' in df_filtered.columns:
    # Asegurar que sea numérico antes de agrupar
    df_filtered['Prima neta'] = pd.to_numeric(df_filtered['Prima neta'], errors='coerce').fillna(0)
    
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
    if not df_filtered.empty and 'Ramo' in df_filtered.columns:
        ventas_por_ramo = df_filtered.groupby('Ramo')['Prima neta'].sum().reset_index()
        fig_ramo = px.bar(ventas_por_ramo, x='Ramo', y='Prima neta', 
                           title='Total de Prima Neta por Ramo',
                           color='Ramo', template='plotly_white')
        fig_ramo.update_layout(showlegend=False)
        st.plotly_chart(fig_ramo, use_container_width=True)
    else:
        st.info('No hay datos o falta la columna Ramo.')

with col2:
    st.markdown('### Ventas agrupadas por Aseguradora')
    if not df_filtered.empty and 'Aseguradora' in df_filtered.columns:
        ventas_por_aseguradora = df_filtered.groupby('Aseguradora')['Prima neta'].sum().reset_index()
        fig_aseguradora = px.bar(ventas_por_aseguradora, x='Aseguradora', y='Prima neta', 
                                 title='Total de Prima Neta por Aseguradora',
                                 color='Aseguradora', template='plotly_white')
        fig_aseguradora.update_layout(showlegend=False)
        st.plotly_chart(fig_aseguradora, use_container_width=True)
    else:
        st.info('No hay datos o falta la columna Aseguradora.')

st.markdown('---')

# --- Gráfica de líneas para incremento de ventas por año (2023, 2024, 2025) ---
st.markdown('### Proyección de incremento de ventas por aseguradora (2023-2025)')

if not df_filtered.empty and 'Fin de vigencia' in df_filtered.columns and df_filtered['Fin de vigencia'].notna().any():
    df_filtered['Año'] = df_filtered['Fin de vigencia'].dt.year
    ventas_actuales_anuales = df_filtered.groupby(['Aseguradora', 'Año'])['Prima neta'].sum().reset_index()
    
    df_proyeccion = ventas_actuales_anuales.copy()
    
    for aseguradora in df_proyeccion['Aseguradora'].unique():
        sales_2023_row = df_proyeccion[(df_proyeccion['Aseguradora'] == aseguradora) & (df_proyeccion['Año'] == 2023)]
        sales_2023 = sales_2023_row['Prima neta'].sum() if not sales_2023_row.empty else 0

        if sales_2023 == 0:
            avg_sales = df_proyeccion[df_proyeccion['Aseguradora'] == aseguradora]['Prima neta'].mean()
            sales_2023 = avg_sales if not pd.isna(avg_sales) else 100000

        sales_2024 = sales_2023 * 1.10
        df_proyeccion = pd.concat([df_proyeccion, pd.DataFrame([{'Aseguradora': aseguradora, 'Año': 2024, 'Prima neta': sales_2024}])], ignore_index=True)

        sales_2025 = sales_2024 * 1.10
        df_proyeccion = pd.concat([df_proyeccion, pd.DataFrame([{'Aseguradora': aseguradora, 'Año': 2025, 'Prima neta': sales_2025}])], ignore_index=True)

    fig_incremento = px.line(df_proyeccion, x='Año', y='Prima neta', color='Aseguradora',
                             title='Proyección de Ventas por Aseguradora (2023-2025)',
                             markers=True, template='plotly_white')
    st.plotly_chart(fig_incremento, use_container_width=True)
else:
    st.info('Nota: No hay fechas válidas en "Fin de vigencia" para calcular la línea temporal histórica. Se muestra vacío.')

st.markdown('---')

# --- Visualización de ventas distribuidas por Moneda ---
st.markdown('### Distribución de Ventas por Divisa')

if not df_filtered.empty and 'Divisa' in df_filtered.columns:
    ventas_por_divisa = df_filtered.groupby('Divisa')['Prima neta'].sum().reset_index()
    fig_divisa = px.pie(ventas_por_divisa, values='Prima neta', names='Divisa',
                        title='Distribución de Prima Neta por Divisa',
                        hole=0.3, template='plotly_white')
    st.plotly_chart(fig_divisa, use_container_width=True)
else:
    st.info('Falta la columna Divisa en los datos.')
