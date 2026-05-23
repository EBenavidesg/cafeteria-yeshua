"""
Página principal de la app - Cafetería Yeshua
Punto de entrada de Streamlit.
"""

import streamlit as st

st.set_page_config(
    page_title="Cafetería Yeshua",
    page_icon="☕",
    layout="wide"
)

st.title("☕ Cafetería Yeshua - Sistema de gestión")

st.markdown("""
### Bienvenida

Este es tu sistema para gestionar la cafetería:

- **Productos**: ver y administrar lo que vendes
- **Ventas** _(próximamente)_: registrar cada venta del día
- **Compras** _(próximamente)_: registrar entregas de proveedores
- **Reportes** _(próximamente)_: ver gráficos y análisis

Usa el menú de la izquierda para navegar entre páginas.
""")

st.info("💡 Tip: Si es la primera vez que usas el sistema, revisa la pestaña **Productos** para ver lo que se importó del Excel.")