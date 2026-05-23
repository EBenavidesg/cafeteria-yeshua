"""
Página de reportes - estadísticas del negocio.
Incluye anulación de ventas sin límite de tiempo (solo ADMIN).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
from datetime import datetime

from app.services.sales import verificar_pin
from app.services.reportes import (
    reporte_del_dia,
    top_productos,
    ventas_por_empleado,
    refrigerios_del_dia,
    listar_ventas_del_dia,
    anular_venta_admin,
)


st.set_page_config(page_title="Reportes", page_icon="📈", layout="wide")


def fmt_pesos(monto):
    return f"${int(monto):,}".replace(",", ".")


# Estado de sesión
if "rep_empleado" not in st.session_state:
    st.session_state.rep_empleado = None


# ============================================================
# LOGIN (reportes solo para ADMIN)
# ============================================================
def vista_login():
    st.title("🔐 Reportes")
    st.caption("Esta sección es solo para administradores")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pin = st.text_input("PIN de administrador", type="password", max_chars=4)
        if st.button("Entrar", type="primary", use_container_width=True):
            if not pin or len(pin) != 4 or not pin.isdigit():
                st.error("PIN debe ser 4 dígitos.")
            else:
                emp = verificar_pin(pin)
                if not emp:
                    st.error("PIN incorrecto.")
                elif emp["rol"] != "ADMIN":
                    st.error("Solo administradores pueden ver los reportes.")
                else:
                    st.session_state.rep_empleado = emp
                    st.rerun()


# ============================================================
# REPORTES
# ============================================================
def vista_reportes():
    emp = st.session_state.rep_empleado

    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("📈 Reportes")
        st.caption(f"Administrador: {emp['nombre']}")
    with col2:
        st.write("")
        if st.button("🚪 Salir", use_container_width=True):
            st.session_state.rep_empleado = None
            st.rerun()

    # Selector de fecha
    fecha_sel = st.date_input("Fecha del reporte", value=datetime.now())
    fecha_dt = datetime(fecha_sel.year, fecha_sel.month, fecha_sel.day)

    st.divider()

    # ===== RESUMEN DEL DÍA =====
    rep = reporte_del_dia(fecha_dt)

    st.subheader(f"📊 Resumen del {rep['fecha'].strftime('%d/%m/%Y')}")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("💰 Total ventas", fmt_pesos(rep["total_ventas"]))
    with c2:
        st.metric("🛒 Transacciones", rep["num_transacciones"])
    with c3:
        st.metric("📦 Unidades vendidas", rep["unidades_vendidas"])
    with c4:
        ticket = rep["total_ventas"] / rep["num_transacciones"] if rep["num_transacciones"] > 0 else 0
        st.metric("🎫 Ticket promedio", fmt_pesos(ticket))

    c5, c6, c7 = st.columns(3)
    with c5:
        st.metric("💵 Efectivo", fmt_pesos(rep["total_efectivo"]))
    with c6:
        st.metric("📲 Transferencia", fmt_pesos(rep["total_transferencia"]))
    with c7:
        st.metric("🍱 Refrigerios (a costo)", fmt_pesos(rep["total_refrigerios_costo"]))

    st.divider()

    # ===== PESTAÑAS =====
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏆 Top productos",
        "👥 Por empleado",
        "🍱 Refrigerios",
        "❌ Anular ventas",
    ])

    # ---- Top productos ----
    with tab1:
        productos = top_productos(fecha_dt, limite=10)
        if not productos:
            st.info("No hay ventas registradas este día.")
        else:
            df = pd.DataFrame(productos)
            df_display = df.copy()
            df_display["ingresos"] = df_display["ingresos"].apply(fmt_pesos)
            df_display.columns = ["Producto", "Unidades", "Ingresos"]
            st.dataframe(df_display, use_container_width=True, hide_index=True)

            # Gráfico de barras
            st.bar_chart(df.set_index("producto")["unidades"])

    # ---- Por empleado ----
    with tab2:
        empleados = ventas_por_empleado(fecha_dt)
        if not empleados:
            st.info("No hay ventas registradas este día.")
        else:
            for e in empleados:
                col_a, col_b, col_c = st.columns([2, 1, 1])
                with col_a:
                    st.write(f"**{e['empleado']}**")
                with col_b:
                    st.write(f"{e['transacciones']} ventas")
                with col_c:
                    st.write(fmt_pesos(e["ingresos"]))

    # ---- Refrigerios ----
    with tab3:
        refris = refrigerios_del_dia(fecha_dt)
        if not refris:
            st.info("No se registraron refrigerios este día.")
        else:
            for r in refris:
                emoji = "🆓" if r["tipo"] == "Gratis" else "💲"
                texto = f"{emoji} {r['fecha'].strftime('%H:%M')} — **{r['empleado']}**: {r['cantidad']}× {r['producto']} ({r['tipo']})"
                if r["monto"] > 0:
                    texto += f" — {fmt_pesos(r['monto'])}"
                st.write(texto)

    # ---- Anular ventas (ADMIN) ----
    with tab4:
        st.markdown("**Anular una venta** (sin límite de tiempo, solo ADMIN)")
        st.caption("Útil para corregir errores que se descubren después. El inventario se devuelve automáticamente.")

        transacciones = listar_ventas_del_dia(fecha_dt)
        if not transacciones:
            st.info("No hay ventas este día.")
        else:
            for tx in transacciones:
                estado = "🚫 ANULADA" if tx["anulada"] else "✅ Activa"
                titulo = f"{estado} • {tx['fecha'].strftime('%H:%M')} • {fmt_pesos(tx['total'])} • {tx['empleado']}"

                with st.expander(titulo):
                    for item in tx["items"]:
                        st.write(f"  • {item['cantidad']}× {item['producto']} — {fmt_pesos(item['subtotal'])}")

                    if tx["anulada"]:
                        st.caption("Esta venta ya fue anulada.")
                    else:
                        motivo = st.text_input(
                            "Motivo de la anulación",
                            key=f"motivo_admin_{tx['transaccion_id']}",
                            placeholder="Ej: producto mal registrado, error de cobro..."
                        )
                        if st.button("❌ Anular esta venta", key=f"anul_admin_{tx['transaccion_id']}"):
                            ok, msg = anular_venta_admin(
                                tx["transaccion_id"],
                                emp["id"],
                                motivo if motivo else None
                            )
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)


# ============================================================
# ROUTER
# ============================================================
if st.session_state.rep_empleado is None:
    vista_login()
else:
    vista_reportes()