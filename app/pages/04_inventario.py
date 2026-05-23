"""
Página de inventario - ver stock + alertas + ajustes manuales.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd

from app.services.sales import verificar_pin
from app.services.inventory import (
    obtener_insumos,
    obtener_alertas_stock,
    ajustar_stock,
    obtener_ajustes_recientes,
    MOTIVOS_DISPLAY,
)


st.set_page_config(page_title="Inventario", page_icon="📊", layout="wide")


if "inv_empleado" not in st.session_state:
    st.session_state.inv_empleado = None


def fmt_pesos(monto):
    if monto is None:
        return "—"
    return f"${int(monto):,}".replace(",", ".")


st.title("📊 Inventario")
st.caption("Stock actual de todos los insumos")


insumos = obtener_insumos()
alertas = obtener_alertas_stock()


col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total insumos", len(insumos))
with col2:
    ok = sum(1 for i in insumos if i["estado"] == "OK")
    st.metric("✅ OK", ok)
with col3:
    bajo = sum(1 for i in insumos if i["estado"] == "BAJO")
    st.metric("⚠️ Stock bajo", bajo)
with col4:
    critico = sum(1 for i in insumos if i["estado"] in ("AGOTADO", "NEGATIVO"))
    st.metric("🔴 Crítico", critico)


if alertas:
    st.divider()
    st.subheader("🚨 Alertas de stock")
    for a in alertas:
        if a["estado"] == "NEGATIVO":
            st.error(f"🔴 **{a['nombre']}**: {a['stock_actual']:.2f} {a['unidad']} (¡NEGATIVO!)")
        elif a["estado"] == "AGOTADO":
            st.error(f"🚫 **{a['nombre']}**: AGOTADO")
        elif a["estado"] == "BAJO":
            st.warning(f"⚠️ **{a['nombre']}**: {a['stock_actual']:.2f} {a['unidad']} (mínimo: {a['stock_minimo']:.2f})")


st.divider()
tab_tabla, tab_ajuste, tab_hist = st.tabs(["📋 Stock actual", "✏️ Ajustar stock", "📜 Historial de ajustes"])


with tab_tabla:
    col_a, col_b = st.columns(2)
    with col_a:
        busqueda = st.text_input("Buscar por nombre", "", key="busq_inv")
    with col_b:
        estado_filtro = st.selectbox("Filtrar por estado", ["Todos", "OK", "BAJO", "AGOTADO", "NEGATIVO"])

    datos = []
    for i in insumos:
        if busqueda and busqueda.lower() not in i["nombre"].lower():
            continue
        if estado_filtro != "Todos" and i["estado"] != estado_filtro:
            continue
        icono = {"OK": "✅", "BAJO": "⚠️", "AGOTADO": "🚫", "NEGATIVO": "🔴"}.get(i["estado"], "")
        datos.append({
            "Estado": f"{icono} {i['estado']}",
            "Insumo": i["nombre"],
            "Stock actual": f"{i['stock_actual']:.2f} {i['unidad']}",
            "Stock mínimo": f"{i['stock_minimo']:.2f} {i['unidad']}",
            "Costo unit.": fmt_pesos(i["costo_unitario"]),
        })

    if datos:
        st.dataframe(pd.DataFrame(datos), use_container_width=True, hide_index=True, height=500)
    else:
        st.info("No hay insumos que coincidan.")


with tab_ajuste:
    st.markdown("**Ajustar el stock de un insumo** (conteo inicial, pérdida, daño, etc.)")
    st.caption("Escribe el stock real que tienes hoy. El sistema calcula la diferencia.")

    if st.session_state.inv_empleado is None:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            pin = st.text_input("Ingresa tu PIN para hacer ajustes", type="password", max_chars=4, key="pin_ajuste")
            if st.button("Validar PIN", type="primary"):
                if not pin or len(pin) != 4 or not pin.isdigit():
                    st.error("PIN debe ser 4 dígitos.")
                else:
                    emp = verificar_pin(pin)
                    if emp:
                        st.session_state.inv_empleado = emp
                        st.rerun()
                    else:
                        st.error("PIN incorrecto.")
    else:
        emp = st.session_state.inv_empleado
        col_a, col_b = st.columns([4, 1])
        with col_a:
            st.success(f"Registrando ajustes como: **{emp['nombre']}**")
        with col_b:
            if st.button("🚪 Salir", key="salir_aju"):
                st.session_state.inv_empleado = None
                st.rerun()

        opciones = {f"{i['nombre']} (actual: {i['stock_actual']:.2f} {i['unidad']})": i for i in insumos}
        insumo_label = st.selectbox("Insumo a ajustar", list(opciones.keys()))
        insumo_sel = opciones[insumo_label]

        col1, col2 = st.columns(2)
        with col1:
            nuevo = st.number_input(
                f"Stock nuevo ({insumo_sel['unidad']})",
                min_value=0.0,
                value=float(insumo_sel["stock_actual"]),
                step=1.0,
                format="%.2f",
            )
        with col2:
            motivo = st.selectbox(
                "Motivo del ajuste",
                options=list(MOTIVOS_DISPLAY.keys()),
                format_func=lambda x: MOTIVOS_DISPLAY[x],
            )

        diferencia = nuevo - insumo_sel["stock_actual"]
        if diferencia > 0:
            st.info(f"📈 Esto SUMARÁ {diferencia:.2f} {insumo_sel['unidad']} al stock.")
        elif diferencia < 0:
            st.warning(f"📉 Esto QUITARÁ {abs(diferencia):.2f} {insumo_sel['unidad']} del stock.")
        else:
            st.caption("Sin cambios.")

        notas = st.text_input("Notas (opcional)", placeholder="Ej: conteo del lunes 5/may...")

        if st.button("✅ Confirmar ajuste", type="primary", use_container_width=True):
            ok, msg = ajustar_stock(
                insumo_id=insumo_sel["id"],
                nuevo_stock=nuevo,
                motivo=motivo,
                empleado_id=emp["id"],
                notas=notas if notas else None,
            )
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)


with tab_hist:
    ajustes = obtener_ajustes_recientes(limite=30)
    if not ajustes:
        st.caption("No hay ajustes registrados todavía.")
    else:
        for a in ajustes:
            signo = "+" if a["diferencia"] > 0 else ""
            color = "🟢" if a["diferencia"] > 0 else "🔴"
            with st.expander(
                f"{color} {a['fecha'].strftime('%d/%m %H:%M')} — {a['insumo']}: {a['stock_anterior']:.2f} → {a['stock_nuevo']:.2f} ({signo}{a['diferencia']:.2f})"
            ):
                st.write(f"**Motivo**: {a['motivo_display']}")
                st.write(f"**Por**: {a['empleado']}")
                if a["notas"]:
                    st.write(f"**Notas**: {a['notas']}")