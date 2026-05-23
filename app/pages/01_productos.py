"""
Página de productos - lista todos los productos disponibles para la venta.
Solo lectura por ahora.
"""

# --- Ajustar el path para que Python encuentre el módulo 'app' ---
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
from app.database.connection import get_session
from app.database.models import Producto


st.set_page_config(page_title="Productos", page_icon="🛒", layout="wide")

st.title("🛒 Productos")
st.markdown("Lista completa de productos vendibles en tu cafetería.")


# --- Cargar productos desde la base de datos ---
@st.cache_data(ttl=60)
def cargar_productos():
    session = get_session()
    try:
        productos = session.query(Producto).filter(Producto.activo == True).all()
        datos = []
        for p in productos:
            datos.append({
                "ID": p.id,
                "Producto": p.nombre,
                "Precio": f"${int(p.precio):,}".replace(",", "."),
                "Precio_num": p.precio,
                "Categoría": p.categoria or "Sin categoría",
            })
        return pd.DataFrame(datos)
    finally:
        session.close()


df = cargar_productos()


# --- Métricas en la parte superior ---
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total productos", len(df))

with col2:
    a_count = df['Categoría'].str.contains(r'\[A\]', regex=True).sum()
    st.metric("Más vendidos (A)", int(a_count))

with col3:
    precio_promedio = df['Precio_num'].mean()
    st.metric("Precio promedio", f"${int(precio_promedio):,}".replace(",", "."))


st.divider()


# --- Filtros ---
st.subheader("🔍 Filtrar productos")

col_a, col_b = st.columns(2)

with col_a:
    busqueda = st.text_input("Buscar por nombre", "")

with col_b:
    categorias = ["Todas"] + sorted(df['Categoría'].unique().tolist())
    categoria_filtro = st.selectbox("Filtrar por categoría", categorias)


# Aplicar filtros
df_filtrado = df.copy()
if busqueda:
    df_filtrado = df_filtrado[df_filtrado['Producto'].str.contains(busqueda, case=False, na=False)]
if categoria_filtro != "Todas":
    df_filtrado = df_filtrado[df_filtrado['Categoría'] == categoria_filtro]


# --- Tabla ---
st.subheader(f"📋 Productos ({len(df_filtrado)} de {len(df)})")

st.dataframe(
    df_filtrado.drop(columns=['Precio_num']),
    use_container_width=True,
    hide_index=True,
    height=500
)