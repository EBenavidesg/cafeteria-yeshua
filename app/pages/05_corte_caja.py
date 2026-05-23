"""
Página de corte de caja.
El empleado cierra caja: el sistema muestra lo vendido, el empleado cuenta y entrega.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from app.services.sales import verificar_pin
from app.services.caja import (
    calcular_movimiento_desde_ultimo_corte,
    registrar_corte,
    obtener_cortes_recientes,
)


st.set_page_config(page_title="Corte de caja", page_icon="🧾", layout="wide")


def fmt_pesos(monto):
    return f"${int(monto):,}".replace(",", ".")


# Estado de sesión
if "caja_empleado" not in st.session_state:
    st.session_state.caja_empleado = None


# ============================================================
# LOGIN
# ============================================================
def vista_login():
    st.title("🔐 Corte de caja")
    st.caption("Ingresa tu PIN para hacer el cierre")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pin = st.text_input("PIN", type="password", max_chars=4)
        if st.button("Entrar", type="primary", use_container_width=True):
            if not pin or len(pin) != 4 or not pin.isdigit():
                st.error("PIN debe ser 4 dígitos.")
            else:
                emp = verificar_pin(pin)
                if emp:
                    st.session_state.caja_empleado = emp
                    st.rerun()
                else:
                    st.error("PIN incorrecto.")


# ============================================================
# CORTE DE CAJA
# ============================================================
def vista_corte():
    emp = st.session_state.caja_empleado

    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("🧾 Corte de caja")
        st.caption(f"Cerrando como: {emp['nombre']}")
    with col2:
        st.write("")
        if st.button("🚪 Salir", use_container_width=True):
            st.session_state.caja_empleado = None
            st.rerun()

    st.divider()

    tab_nuevo, tab_historial = st.tabs(["✂️ Nuevo corte", "📜 Historial de cortes"])

    # ---------- Nuevo corte ----------
    with tab_nuevo:
        mov = calcular_movimiento_desde_ultimo_corte()

        st.subheader("📊 Lo que el sistema calculó")
        st.caption(f"Ventas desde el último corte ({mov['desde'].strftime('%d/%m %H:%M')})")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("💵 Ventas efectivo", fmt_pesos(mov["ventas_efectivo"]))
        with c2:
            st.metric("📲 Ventas transferencia", fmt_pesos(mov["ventas_transferencia"]))
        with c3:
            st.metric("🛒 Transacciones", mov["num_transacciones"])

        c4, c5 = st.columns(2)
        with c4:
            st.metric("🏦 Base inicial (sencillo)", fmt_pesos(mov["base_inicial"]))
        with c5:
            st.metric("🎯 Efectivo esperado en caja", fmt_pesos(mov["efectivo_esperado"]),
                      help="Base inicial + ventas en efectivo")

        st.divider()
        st.subheader("✍️ Lo que tú cuentas")
        st.caption("Cuenta la plata física y escribe los valores reales")

        col_a, col_b = st.columns(2)
        with col_a:
            efectivo_contado = st.number_input(
                "💰 Efectivo total contado en caja",
                min_value=0,
                value=0,
                step=1000,
                help="Toda la plata en efectivo que hay en la caja ahora mismo"
            )
            base_dejada = st.number_input(
                "🏦 Base que dejas para después (sencillo)",
                min_value=0,
                value=0,
                step=1000,
                help="El dinero que dejas en la caja para dar vueltas"
            )
        with col_b:
            efectivo_entregado = st.number_input(
                "📤 Efectivo que entregas al jefe",
                min_value=0,
                value=0,
                step=1000,
            )

        # Cálculos en vivo
        diferencia = efectivo_contado - mov["efectivo_esperado"]
        suma_distribuida = base_dejada + efectivo_entregado

        st.divider()

        # Mostrar comparaciones
        st.subheader("🔍 Comparación")

        col_x, col_y = st.columns(2)
        with col_x:
            st.write("**Caja (esperado vs contado)**")
            st.write(f"Esperado: {fmt_pesos(mov['efectivo_esperado'])}")
            st.write(f"Contado: {fmt_pesos(efectivo_contado)}")
            if diferencia == 0:
                st.success("✅ La caja cuadra exactamente")
            elif diferencia > 0:
                st.info(f"➕ Sobra {fmt_pesos(diferencia)}")
            else:
                st.warning(f"➖ Falta {fmt_pesos(abs(diferencia))}")

        with col_y:
            st.write("**Distribución del efectivo contado**")
            st.write(f"Base dejada: {fmt_pesos(base_dejada)}")
            st.write(f"Entregado al jefe: {fmt_pesos(efectivo_entregado)}")
            st.write(f"Suma: {fmt_pesos(suma_distribuida)}")
            if suma_distribuida == efectivo_contado:
                st.success("✅ Todo el efectivo está distribuido")
            else:
                dif_dist = efectivo_contado - suma_distribuida
                if dif_dist > 0:
                    st.warning(f"Quedan {fmt_pesos(dif_dist)} sin asignar")
                else:
                    st.warning(f"Asignaste {fmt_pesos(abs(dif_dist))} de más")

        # Nota opcional
        nota = st.text_input(
            "📝 Nota (opcional)",
            placeholder="Ej: le fié $5.000 a un cliente, falta cuadrar..."
        )

        st.divider()
        if st.button("✅ Registrar corte de caja", type="primary", use_container_width=True):
            if efectivo_contado == 0 and efectivo_entregado == 0:
                st.error("Ingresa al menos el efectivo contado.")
            else:
                ok, msg, datos = registrar_corte(
                    empleado_id=emp["id"],
                    efectivo_contado=efectivo_contado,
                    base_dejada=base_dejada,
                    efectivo_entregado=efectivo_entregado,
                    nota=nota if nota else None,
                )
                if ok:
                    st.success(f"✅ {msg}")
                    st.balloons()
                    st.rerun()
                else:
                    st.error(msg)

    # ---------- Historial ----------
    with tab_historial:
        cortes = obtener_cortes_recientes(limite=30)
        if not cortes:
            st.caption("No hay cortes registrados todavía.")
        else:
            for c in cortes:
                total_ingresos = c["ventas_efectivo"] + c["ventas_transferencia"]
                with st.expander(
                    f"🧾 {c['fecha'].strftime('%d/%m/%Y %H:%M')} — {c['empleado']} — Entregado: {fmt_pesos(c['efectivo_entregado'])}"
                ):
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        st.write("**Ventas del periodo**")
                        st.write(f"Efectivo: {fmt_pesos(c['ventas_efectivo'])}")
                        st.write(f"Transferencia: {fmt_pesos(c['ventas_transferencia'])}")
                        st.write(f"Total ingresos: {fmt_pesos(total_ingresos)}")
                    with cc2:
                        st.write("**Caja**")
                        st.write(f"Base inicial: {fmt_pesos(c['base_inicial'])}")
                        st.write(f"Efectivo contado: {fmt_pesos(c['efectivo_contado'])}")
                        st.write(f"Base dejada: {fmt_pesos(c['base_dejada'])}")
                        st.write(f"Entregado: {fmt_pesos(c['efectivo_entregado'])}")

                    if c["diferencia"] == 0:
                        st.success("✅ Caja cuadró")
                    elif c["diferencia"] > 0:
                        st.info(f"➕ Sobró {fmt_pesos(c['diferencia'])}")
                    else:
                        st.warning(f"➖ Faltó {fmt_pesos(abs(c['diferencia']))}")

                    if c["nota"]:
                        st.write(f"📝 **Nota**: {c['nota']}")


# ============================================================
# ROUTER
# ============================================================
if st.session_state.caja_empleado is None:
    vista_login()
else:
    vista_corte()