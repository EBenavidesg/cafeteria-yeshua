"""
Página de compras - registrar entradas de proveedor.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from datetime import datetime

from app.services.sales import verificar_pin
from app.services.inventory import (
    obtener_insumos,
    obtener_proveedores,
    registrar_compra,
    obtener_compras_recientes,
)


st.set_page_config(page_title="Compras", page_icon="📦", layout="wide")


def fmt_pesos(monto):
    if monto is None:
        return "—"
    return f"${int(monto):,}".replace(",", ".")


if "compras_empleado" not in st.session_state:
    st.session_state.compras_empleado = None


def vista_login():
    st.title("🔐 Iniciar sesión - Compras")
    st.caption("Ingresa tu PIN para registrar compras")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pin = st.text_input("PIN", type="password", max_chars=4)
        if st.button("Entrar", type="primary", use_container_width=True):
            if not pin or len(pin) != 4 or not pin.isdigit():
                st.error("PIN debe ser 4 dígitos.")
            else:
                emp = verificar_pin(pin)
                if emp:
                    st.session_state.compras_empleado = emp
                    st.rerun()
                else:
                    st.error("PIN incorrecto.")


def vista_compras():
    emp = st.session_state.compras_empleado

    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("📦 Compras")
        st.caption(f"Registrando como: {emp['nombre']}")
    with col2:
        st.write("")
        if st.button("🚪 Salir", use_container_width=True):
            st.session_state.compras_empleado = None
            st.rerun()

    st.divider()

    col_form, col_hist = st.columns([1, 1])

    with col_form:
        st.subheader("➕ Registrar nueva entrada")

        insumos = obtener_insumos()
        proveedores = obtener_proveedores()

        if not insumos:
            st.warning("No hay insumos en la base de datos.")
            return

        opciones_insumo = {f"{i['nombre']} (stock: {i['stock_actual']:.1f} {i['unidad']})": i for i in insumos}
        insumo_label = st.selectbox("Insumo que llegó", list(opciones_insumo.keys()))
        insumo = opciones_insumo[insumo_label]

        cantidad = st.number_input(
            f"Cantidad recibida ({insumo['unidad']})",
            min_value=0.0,
            value=1.0,
            step=1.0,
            format="%.2f"
        )

        opciones_prov = {"— Sin proveedor —": None}
        for p in proveedores:
            opciones_prov[p["nombre"]] = p["id"]
        prov_label = st.selectbox("Proveedor", list(opciones_prov.keys()))
        prov_id = opciones_prov[prov_label]

        costo = st.number_input(
            "Costo total pagado (COP)",
            min_value=0,
            value=0,
            step=1000,
            help="Déjalo en 0 si no quieres registrar el costo"
        )
        costo_final = costo if costo > 0 else None

        notas = st.text_input("Notas (opcional)", placeholder="Ej: factura #1234, llegó parcial...")

        if st.button("✅ Registrar entrada", type="primary", use_container_width=True):
            if cantidad <= 0:
                st.error("La cantidad debe ser mayor a 0.")
            else:
                ok, msg = registrar_compra(
                    insumo_id=insumo["id"],
                    cantidad=cantidad,
                    proveedor_id=prov_id,
                    empleado_id=emp["id"],
                    costo_total=costo_final,
                    notas=notas if notas else None,
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    with col_hist:
        st.subheader("📋 Compras recientes")
        compras = obtener_compras_recientes(limite=15)

        if not compras:
            st.caption("No hay compras registradas todavía.")
        else:
            for c in compras:
                with st.expander(f"{c['fecha'].strftime('%d/%m %H:%M')} — {c['insumo']}"):
                    st.write(f"**Cantidad**: {c['cantidad']:.2f} {c['unidad']}")
                    st.write(f"**Proveedor**: {c['proveedor']}")
                    st.write(f"**Registrado por**: {c['empleado']}")
                    if c["costo_total"]:
                        st.write(f"**Costo**: {fmt_pesos(c['costo_total'])}")
                    if c["notas"]:
                        st.write(f"**Notas**: {c['notas']}")


if st.session_state.compras_empleado is None:
    vista_login()
else:
    vista_compras()