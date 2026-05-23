"""
Servicio de inventario, compras y ajustes manuales.
"""

from datetime import datetime
from typing import List, Tuple, Optional
from app.database.connection import get_session
from app.database.models import Insumo, Compra, Proveedor, Empleado


def obtener_insumos() -> List[dict]:
    """Devuelve todos los insumos con info para mostrar."""
    session = get_session()
    try:
        insumos = session.query(Insumo).order_by(Insumo.nombre).all()
        return [
            {
                "id": i.id,
                "nombre": i.nombre,
                "unidad": i.unidad,
                "stock_actual": i.stock_actual,
                "stock_minimo": i.stock_minimo,
                "costo_unitario": i.costo_unitario,
                "estado": _calcular_estado_stock(i.stock_actual, i.stock_minimo),
            }
            for i in insumos
        ]
    finally:
        session.close()


def _calcular_estado_stock(actual: float, minimo: float) -> str:
    if actual < 0:
        return "NEGATIVO"
    if actual == 0:
        return "AGOTADO"
    if actual <= minimo:
        return "BAJO"
    return "OK"


def obtener_proveedores() -> List[dict]:
    session = get_session()
    try:
        provs = session.query(Proveedor).order_by(Proveedor.nombre).all()
        return [{"id": p.id, "nombre": p.nombre} for p in provs]
    finally:
        session.close()


def registrar_compra(
    insumo_id: int,
    cantidad: float,
    proveedor_id: Optional[int],
    empleado_id: int,
    costo_total: Optional[float] = None,
    notas: Optional[str] = None,
) -> Tuple[bool, str]:
    if cantidad <= 0:
        return False, "La cantidad debe ser mayor a 0."

    session = get_session()
    try:
        insumo = session.query(Insumo).filter_by(id=insumo_id).first()
        if not insumo:
            return False, "Insumo no encontrado."

        nueva_compra = Compra(
            fecha=datetime.now(),
            insumo_id=insumo_id,
            cantidad=cantidad,
            costo_total=costo_total,
            notas=notas,
            proveedor_id=proveedor_id,
            empleado_id=empleado_id,
        )
        session.add(nueva_compra)

        insumo.stock_actual = insumo.stock_actual + cantidad

        if costo_total and costo_total > 0:
            insumo.costo_unitario = costo_total / cantidad

        session.commit()
        return True, f"Compra registrada. Nuevo stock: {insumo.stock_actual:.2f} {insumo.unidad}"

    except Exception as e:
        session.rollback()
        return False, f"Error: {str(e)}"
    finally:
        session.close()


def obtener_compras_recientes(limite: int = 20) -> List[dict]:
    session = get_session()
    try:
        compras = session.query(Compra).order_by(Compra.fecha.desc()).limit(limite).all()
        return [
            {
                "id": c.id,
                "fecha": c.fecha,
                "insumo": c.insumo.nombre if c.insumo else "?",
                "cantidad": c.cantidad,
                "unidad": c.insumo.unidad if c.insumo else "",
                "proveedor": c.proveedor.nombre if c.proveedor else "Sin proveedor",
                "empleado": c.empleado.nombre if c.empleado else "?",
                "costo_total": c.costo_total,
                "notas": c.notas,
            }
            for c in compras
        ]
    finally:
        session.close()


def obtener_alertas_stock() -> List[dict]:
    session = get_session()
    try:
        insumos = session.query(Insumo).all()
        alertas = []
        for i in insumos:
            estado = _calcular_estado_stock(i.stock_actual, i.stock_minimo)
            if estado != "OK":
                alertas.append({
                    "nombre": i.nombre,
                    "unidad": i.unidad,
                    "stock_actual": i.stock_actual,
                    "stock_minimo": i.stock_minimo,
                    "estado": estado,
                })
        return sorted(alertas, key=lambda x: x["stock_actual"])
    finally:
        session.close()


# ============================================================
# AJUSTES DE INVENTARIO
# ============================================================

MOTIVOS_AJUSTE = [
    "CONTEO_INICIAL",
    "CONTEO_PERIODICO",
    "PERDIDA",
    "DANO",
    "OTRO",
]

MOTIVOS_DISPLAY = {
    "CONTEO_INICIAL": "📋 Conteo inicial",
    "CONTEO_PERIODICO": "🔄 Conteo periódico",
    "PERDIDA": "❌ Pérdida / robo",
    "DANO": "💥 Producto dañado",
    "OTRO": "📝 Otro",
}


def ajustar_stock(
    insumo_id: int,
    nuevo_stock: float,
    motivo: str,
    empleado_id: int,
    notas: Optional[str] = None,
) -> Tuple[bool, str]:
    if motivo not in MOTIVOS_AJUSTE:
        return False, "Motivo inválido."

    if nuevo_stock < 0:
        return False, "El stock no puede ser negativo."

    from app.database.models import AjusteInventario

    session = get_session()
    try:
        insumo = session.query(Insumo).filter_by(id=insumo_id).first()
        if not insumo:
            return False, "Insumo no encontrado."

        stock_anterior = insumo.stock_actual
        diferencia = nuevo_stock - stock_anterior

        if diferencia == 0:
            return False, "El nuevo stock es igual al actual. No hay cambios."

        ajuste = AjusteInventario(
            fecha=datetime.now(),
            insumo_id=insumo_id,
            stock_anterior=stock_anterior,
            stock_nuevo=nuevo_stock,
            diferencia=diferencia,
            motivo=motivo,
            notas=notas,
            empleado_id=empleado_id,
        )
        session.add(ajuste)

        insumo.stock_actual = nuevo_stock

        session.commit()
        signo = "+" if diferencia > 0 else ""
        return True, f"Stock ajustado: {stock_anterior:.2f} → {nuevo_stock:.2f} ({signo}{diferencia:.2f})"

    except Exception as e:
        session.rollback()
        return False, f"Error: {str(e)}"
    finally:
        session.close()


def obtener_ajustes_recientes(limite: int = 20) -> List[dict]:
    from app.database.models import AjusteInventario

    session = get_session()
    try:
        ajustes = session.query(AjusteInventario).order_by(AjusteInventario.fecha.desc()).limit(limite).all()
        return [
            {
                "id": a.id,
                "fecha": a.fecha,
                "insumo": a.insumo.nombre if a.insumo else "?",
                "unidad": a.insumo.unidad if a.insumo else "",
                "stock_anterior": a.stock_anterior,
                "stock_nuevo": a.stock_nuevo,
                "diferencia": a.diferencia,
                "motivo": a.motivo,
                "motivo_display": MOTIVOS_DISPLAY.get(a.motivo, a.motivo),
                "empleado": a.empleado.nombre if a.empleado else "?",
                "notas": a.notas,
            }
            for a in ajustes
        ]
    finally:
        session.close()