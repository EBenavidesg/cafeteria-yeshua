"""
Página de ventas - POS con ventas normales y refrigerios de empleados.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from collections import defaultdict

from app.services.sales import (
    verificar_pin,
    cambiar_pin,
    registrar_venta,
    registrar_refrigerio,
    obtener_productos_activos,
    obtener_ventas_anulables,
    anular_transaccion,
    MINUTOS_VENTANA_ANULACION,
)


st.set_page_config(page_title="Ventas", page_icon="💰", layout="wide")


# Estado de sesión
if "empleado" not in st.session_state:
    st.session_state.empleado = None
if "carrito" not in st.session_state:
    st.session_state.carrito = {}
if "vista" not in st.session_state:
    st.session_state.vista = "login"
if "monto_recibido" not in st.session_state:
    st.session_state.monto_recibido = 0


def fmt_pesos(monto):
    return f"${int(monto):,}".replace(",", ".")


def reset_carrito():
    st.session_state.carrito = {}
    st.session_state.monto_recibido = 0
    st.session_state.vista = "ventas"


# ============================================================
# VISTA: LOGIN
# ============================================================
def vista_login():
    st.title("🔐 Iniciar turno")
    st.caption("Ingresa tu PIN para empezar")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pin = st.text_input("PIN de 4 dígitos", type="password", max_chars=4, key="login_pin")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Entrar", type="primary", use_container_width=True):
                if not pin or len(pin) != 4 or not pin.isdigit():
                    st.error("El PIN debe tener 4 dígitos.")
                else:
                    emp = verificar_pin(pin)
                    if emp:
                        st.session_state.empleado = emp
                        st.session_state.vista = "ventas"
                        st.rerun()
                    else:
                        st.error("PIN incorrecto.")
        with c2:
            if st.button("Cambiar mi PIN", use_container_width=True):
                st.session_state.vista = "cambio_pin"
                st.rerun()


# ============================================================
# VISTA: CAMBIO DE PIN
# ============================================================
def vista_cambio_pin():
    st.title("🔑 Cambiar mi PIN")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pin_actual = st.text_input("PIN actual", type="password", max_chars=4)
        pin_nuevo = st.text_input("PIN nuevo (4 dígitos)", type="password", max_chars=4)
        pin_conf = st.text_input("Confirmar PIN nuevo", type="password", max_chars=4)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Cambiar PIN", type="primary", use_container_width=True):
                if not pin_actual or not pin_nuevo or not pin_conf:
                    st.error("Llena todos los campos.")
                elif pin_nuevo != pin_conf:
                    st.error("El PIN nuevo y la confirmación no coinciden.")
                else:
                    emp = verificar_pin(pin_actual)
                    if not emp:
                        st.error("El PIN actual es incorrecto.")
                    else:
                        ok, msg = cambiar_pin(emp["id"], pin_actual, pin_nuevo)
                        if ok:
                            st.success(msg)
                            st.session_state.vista = "login"
                            st.rerun()
                        else:
                            st.error(msg)
        with c2:
            if st.button("Volver", use_container_width=True):
                st.session_state.vista = "login"
                st.rerun()


# ============================================================
# VISTA: VENTAS (productos + carrito)
# ============================================================
def vista_ventas():
    emp = st.session_state.empleado

    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("💰 Ventas")
        st.caption(f"Cajero: {emp['nombre']} ({emp['rol']})")
    with col2:
        st.write("")
        if st.button("🚪 Cerrar turno", use_container_width=True):
            st.session_state.empleado = None
            st.session_state.carrito = {}
            st.session_state.vista = "login"
            st.rerun()

    st.divider()

    col_prod, col_carr = st.columns([2, 1])

    with col_prod:
        st.subheader("🛒 Productos")
        productos = obtener_productos_activos()

        cats = defaultdict(list)
        for p in productos:
            cat = p["categoria"]
            if "] " in cat:
                cat = cat.split("] ", 1)[1]
            cats[cat].append(p)

        nombres_cats = sorted(cats.keys())
        if nombres_cats:
            tabs = st.tabs(nombres_cats)
            for tab, cat_nom in zip(tabs, nombres_cats):
                with tab:
                    prods_cat = sorted(cats[cat_nom], key=lambda x: x["nombre"])
                    cols = st.columns(3)
                    for i, p in enumerate(prods_cat):
                        with cols[i % 3]:
                            label = f"{p['nombre']}\n{fmt_pesos(p['precio'])}"
                            if st.button(label, key=f"prod_{p['id']}", use_container_width=True):
                                pid = p["id"]
                                if pid in st.session_state.carrito:
                                    st.session_state.carrito[pid]["cantidad"] += 1
                                else:
                                    st.session_state.carrito[pid] = {
                                        "nombre": p["nombre"],
                                        "precio": p["precio"],
                                        "cantidad": 1,
                                    }
                                st.rerun()

    with col_carr:
        st.subheader("📋 Carrito")

        if not st.session_state.carrito:
            st.info("Toca productos para agregarlos.")
        else:
            total = 0
            for pid, item in list(st.session_state.carrito.items()):
                subtotal = item["precio"] * item["cantidad"]
                total += subtotal
                ca, cb, cc = st.columns([3, 1, 1])
                with ca:
                    st.write(f"**{item['cantidad']}× {item['nombre']}**")
                    st.caption(fmt_pesos(subtotal))
                with cb:
                    if st.button("➖", key=f"menos_{pid}"):
                        if item["cantidad"] > 1:
                            st.session_state.carrito[pid]["cantidad"] -= 1
                        else:
                            del st.session_state.carrito[pid]
                        st.rerun()
                with cc:
                    if st.button("🗑️", key=f"del_{pid}"):
                        del st.session_state.carrito[pid]
                        st.rerun()

            st.divider()
            st.markdown(f"### Total: {fmt_pesos(total)}")

            if st.button("🧹 Limpiar", use_container_width=True):
                st.session_state.carrito = {}
                st.rerun()

            c1, c2 = st.columns(2)
            with c1:
                if st.button("💵 Cobrar", type="primary", use_container_width=True):
                    st.session_state.vista = "cobro"
                    st.session_state.monto_recibido = 0
                    st.rerun()
            with c2:
                if st.button("🍱 Refrigerio", use_container_width=True):
                    st.session_state.vista = "refrigerio"
                    st.rerun()

    # Sección de anulaciones
    st.divider()
    st.subheader(f"⏪ Ventas recientes (últimos {MINUTOS_VENTANA_ANULACION} min)")

    anulables = obtener_ventas_anulables()
    if not anulables:
        st.caption("No hay ventas anulables en este momento.")
    else:
        for tx in anulables:
            with st.expander(f"🧾 {tx['fecha'].strftime('%H:%M:%S')} • {fmt_pesos(tx['total'])} • {tx['empleado']} • {tx['metodo_pago']}"):
                for item in tx["items"]:
                    st.write(f"  • {item['cantidad']}× {item['producto']} — {fmt_pesos(item['subtotal'])}")
                motivo = st.text_input(
                    "Motivo (opcional)",
                    key=f"motivo_{tx['transaccion_id']}",
                    placeholder="Ej: cliente cambió de opinión..."
                )
                if st.button("❌ Anular esta venta", key=f"anul_{tx['transaccion_id']}"):
                    ok, msg = anular_transaccion(tx["transaccion_id"], emp["id"], motivo if motivo else None)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)


# ============================================================
# VISTA: COBRO (caja registradora)
# ============================================================
def vista_cobro():
    emp = st.session_state.empleado

    if not st.session_state.carrito:
        st.session_state.vista = "ventas"
        st.rerun()

    total = sum(item["precio"] * item["cantidad"] for item in st.session_state.carrito.values())

    st.title("💵 Cobrar")

    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown(
            f"<div style='text-align:center;padding:20px;background-color:rgba(0,0,0,0.05);border-radius:12px;margin-bottom:20px;'>"
            f"<p style='margin:0;font-size:14px;opacity:0.7;'>Total a cobrar</p>"
            f"<p style='margin:0;font-size:48px;font-weight:600;'>{fmt_pesos(total)}</p></div>",
            unsafe_allow_html=True
        )

        metodo = st.radio("Método de pago", ["EFECTIVO", "TRANSFERENCIA"], horizontal=True, key="metodo_pago")

        st.markdown("**Plata recibida**")
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("$5.000", use_container_width=True):
            st.session_state.monto_recibido = 5000
            st.rerun()
        if c2.button("$10.000", use_container_width=True):
            st.session_state.monto_recibido = 10000
            st.rerun()
        if c3.button("$20.000", use_container_width=True):
            st.session_state.monto_recibido = 20000
            st.rerun()
        if c4.button("$50.000", use_container_width=True):
            st.session_state.monto_recibido = 50000
            st.rerun()

        if st.button(f"✅ Pago exacto ({fmt_pesos(total)})", use_container_width=True, type="primary"):
            st.session_state.monto_recibido = total
            st.rerun()

        monto_manual = st.number_input("O escribe otro monto", min_value=0, value=int(st.session_state.monto_recibido), step=500)
        if monto_manual != int(st.session_state.monto_recibido):
            st.session_state.monto_recibido = monto_manual

        recibido = st.session_state.monto_recibido
        vuelto = recibido - total

        if recibido < total:
            st.error(f"Falta: {fmt_pesos(total - recibido)}")
        else:
            st.success(f"### Vuelto: {fmt_pesos(vuelto)}")

        st.divider()
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("⬅️ Volver", use_container_width=True):
                st.session_state.vista = "ventas"
                st.rerun()
        with cc2:
            if st.button("✅ Confirmar venta", type="primary", use_container_width=True, disabled=(recibido < total)):
                items = [
                    {"producto_id": pid, "cantidad": item["cantidad"], "precio": item["precio"]}
                    for pid, item in st.session_state.carrito.items()
                ]
                ok, msg, datos = registrar_venta(items, emp["id"], metodo, recibido)
                if ok:
                    st.success(f"✅ Venta registrada. Vuelto: {fmt_pesos(datos['vuelto'])}")
                    if datos.get("advertencias"):
                        for adv in datos["advertencias"]:
                            st.warning(adv)
                    reset_carrito()
                    st.rerun()
                else:
                    st.error(msg)


# ============================================================
# VISTA: REFRIGERIO (consumo de empleado)
# ============================================================
def vista_refrigerio():
    emp = st.session_state.empleado

    if not st.session_state.carrito:
        st.session_state.vista = "ventas"
        st.rerun()

    st.title("🍱 Consumo de empleado")
    st.caption(f"Registrando para: {emp['nombre']}")

    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        # Resumen de lo que se lleva
        st.markdown("**Productos seleccionados:**")
        for pid, item in st.session_state.carrito.items():
            st.write(f"  • {item['cantidad']}× {item['nombre']}")

        st.divider()

        # Tipo de consumo
        tipo = st.radio(
            "Tipo de consumo",
            ["🆓 Refrigerio gratis", "💲 A precio de costo"],
            key="tipo_refrigerio"
        )
        es_gratis = tipo.startswith("🆓")

        monto = 0
        metodo = None

        if not es_gratis:
            monto = st.number_input(
                "¿Cuánto vas a pagar? (COP)",
                min_value=0,
                value=0,
                step=500,
                help="Escribe el monto a precio de costo"
            )
            metodo = st.radio("Método de pago", ["EFECTIVO", "TRANSFERENCIA"], horizontal=True, key="metodo_refri")

        st.divider()
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("⬅️ Volver", use_container_width=True):
                st.session_state.vista = "ventas"
                st.rerun()
        with cc2:
            deshabilitado = (not es_gratis and monto <= 0)
            if st.button("✅ Confirmar", type="primary", use_container_width=True, disabled=deshabilitado):
                items = [
                    {"producto_id": pid, "cantidad": item["cantidad"], "precio": item["precio"]}
                    for pid, item in st.session_state.carrito.items()
                ]
                ok, msg, datos = registrar_refrigerio(
                    items_carrito=items,
                    empleado_id=emp["id"],
                    es_gratis=es_gratis,
                    monto_pagado=monto,
                    metodo_pago=metodo,
                )
                if ok:
                    st.success(f"✅ {msg}")
                    if datos.get("advertencias"):
                        for adv in datos["advertencias"]:
                            st.warning(adv)
                    reset_carrito()
                    st.rerun()
                else:
                    st.error(msg)


# ============================================================
# ROUTER
# ============================================================
if st.session_state.empleado is None:
    if st.session_state.vista == "cambio_pin":
        vista_cambio_pin()
    else:
        vista_login()
else:
    if st.session_state.vista == "cobro":
        vista_cobro()
    elif st.session_state.vista == "refrigerio":
        vista_refrigerio()
    else:
        vista_ventas()