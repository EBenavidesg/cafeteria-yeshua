"""
Servicio de reportes - estadísticas de ventas, productos y empleados.
También permite anular ventas sin límite de tiempo (solo ADMIN).
"""

from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from app.database.connection import get_session
from app.database.models import Venta, Producto, Empleado, Receta, Insumo


def _rango_dia(fecha: datetime):
    """Devuelve el inicio y fin de un día."""
    inicio = datetime(fecha.year, fecha.month, fecha.day, 0, 0, 0)
    fin = inicio + timedelta(days=1)
    return inicio, fin


def reporte_del_dia(fecha: Optional[datetime] = None) -> dict:
    """
    Resumen de ventas de un día específico (por defecto hoy).
    """
    if fecha is None:
        fecha = datetime.now()

    inicio, fin = _rango_dia(fecha)
    session = get_session()
    try:
        ventas = session.query(Venta).filter(
            Venta.fecha >= inicio,
            Venta.fecha < fin,
            Venta.anulada == False,
        ).all()

        total_ventas = 0
        total_efectivo = 0
        total_transferencia = 0
        total_refrigerios_gratis = 0
        total_refrigerios_costo = 0
        num_transacciones = set()
        unidades_vendidas = 0

        for v in ventas:
            monto = v.total or 0
            if v.tipo == "VENTA":
                num_transacciones.add(v.transaccion_id)
                total_ventas += monto
                unidades_vendidas += v.cantidad
                if v.metodo_pago == "EFECTIVO":
                    total_efectivo += monto
                elif v.metodo_pago == "TRANSFERENCIA":
                    total_transferencia += monto
            elif v.tipo == "REFRIGERIO_GRATIS":
                total_refrigerios_gratis += 0
            elif v.tipo == "REFRIGERIO_COSTO":
                total_refrigerios_costo += monto

        return {
            "fecha": fecha.date(),
            "total_ventas": total_ventas,
            "total_efectivo": total_efectivo,
            "total_transferencia": total_transferencia,
            "num_transacciones": len(num_transacciones),
            "unidades_vendidas": unidades_vendidas,
            "total_refrigerios_costo": total_refrigerios_costo,
        }
    finally:
        session.close()


def top_productos(fecha: Optional[datetime] = None, limite: int = 10) -> List[dict]:
    """Productos más vendidos de un día."""
    if fecha is None:
        fecha = datetime.now()
    inicio, fin = _rango_dia(fecha)

    session = get_session()
    try:
        ventas = session.query(Venta).filter(
            Venta.fecha >= inicio,
            Venta.fecha < fin,
            Venta.anulada == False,
            Venta.tipo == "VENTA",
        ).all()

        conteo = {}
        for v in ventas:
            nombre = v.producto.nombre if v.producto else "?"
            if nombre not in conteo:
                conteo[nombre] = {"unidades": 0, "ingresos": 0}
            conteo[nombre]["unidades"] += v.cantidad
            conteo[nombre]["ingresos"] += v.total or 0

        lista = [
            {"producto": k, "unidades": v["unidades"], "ingresos": v["ingresos"]}
            for k, v in conteo.items()
        ]
        lista.sort(key=lambda x: x["unidades"], reverse=True)
        return lista[:limite]
    finally:
        session.close()


def ventas_por_empleado(fecha: Optional[datetime] = None) -> List[dict]:
    """Cuánto vendió cada empleado en un día."""
    if fecha is None:
        fecha = datetime.now()
    inicio, fin = _rango_dia(fecha)

    session = get_session()
    try:
        ventas = session.query(Venta).filter(
            Venta.fecha >= inicio,
            Venta.fecha < fin,
            Venta.anulada == False,
            Venta.tipo == "VENTA",
        ).all()

        conteo = {}
        for v in ventas:
            nombre = v.empleado.nombre if v.empleado else "?"
            if nombre not in conteo:
                conteo[nombre] = {"ingresos": 0, "transacciones": set()}
            conteo[nombre]["ingresos"] += v.total or 0
            conteo[nombre]["transacciones"].add(v.transaccion_id)

        return sorted(
            [
                {"empleado": k, "ingresos": v["ingresos"], "transacciones": len(v["transacciones"])}
                for k, v in conteo.items()
            ],
            key=lambda x: x["ingresos"],
            reverse=True,
        )
    finally:
        session.close()


def refrigerios_del_dia(fecha: Optional[datetime] = None) -> List[dict]:
    """Lista de refrigerios consumidos por empleados en un día."""
    if fecha is None:
        fecha = datetime.now()
    inicio, fin = _rango_dia(fecha)

    session = get_session()
    try:
        refris = session.query(Venta).filter(
            Venta.fecha >= inicio,
            Venta.fecha < fin,
            Venta.anulada == False,
            Venta.tipo.in_(["REFRIGERIO_GRATIS", "REFRIGERIO_COSTO"]),
        ).order_by(Venta.fecha.desc()).all()

        return [
            {
                "fecha": r.fecha,
                "empleado": r.empleado.nombre if r.empleado else "?",
                "producto": r.producto.nombre if r.producto else "?",
                "cantidad": r.cantidad,
                "tipo": "Gratis" if r.tipo == "REFRIGERIO_GRATIS" else "A costo",
                "monto": r.total or 0,
            }
            for r in refris
        ]
    finally:
        session.close()


def listar_ventas_del_dia(fecha: Optional[datetime] = None) -> List[dict]:
    """
    Lista todas las transacciones de venta de un día (para que ADMIN pueda anular).
    Agrupa por transaccion_id.
    """
    if fecha is None:
        fecha = datetime.now()
    inicio, fin = _rango_dia(fecha)

    session = get_session()
    try:
        ventas = session.query(Venta).filter(
            Venta.fecha >= inicio,
            Venta.fecha < fin,
            Venta.tipo == "VENTA",
            Venta.transaccion_id.isnot(None),
        ).order_by(Venta.fecha.desc()).all()

        transacciones = {}
        for v in ventas:
            tid = v.transaccion_id
            if tid not in transacciones:
                transacciones[tid] = {
                    "transaccion_id": tid,
                    "fecha": v.fecha,
                    "empleado": v.empleado.nombre if v.empleado else "?",
                    "metodo_pago": v.metodo_pago,
                    "anulada": v.anulada,
                    "items": [],
                    "total": 0,
                }
            transacciones[tid]["items"].append({
                "producto": v.producto.nombre if v.producto else "?",
                "cantidad": v.cantidad,
                "subtotal": v.total or 0,
            })
            transacciones[tid]["total"] += v.total or 0

        return sorted(transacciones.values(), key=lambda x: x["fecha"], reverse=True)
    finally:
        session.close()


def anular_venta_admin(
    transaccion_id: str,
    admin_id: int,
    motivo: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Anula una venta sin límite de tiempo. SOLO para ADMIN.
    Devuelve el inventario al stock.
    """
    session = get_session()
    try:
        # Verificar que quien anula es ADMIN
        admin = session.query(Empleado).filter_by(id=admin_id).first()
        if not admin or admin.rol != "ADMIN":
            return False, "Solo un administrador puede anular ventas antiguas."

        ventas = session.query(Venta).filter_by(transaccion_id=transaccion_id).all()
        if not ventas:
            return False, "Transacción no encontrada."

        if any(v.anulada for v in ventas):
            return False, "Esta transacción ya estaba anulada."

        ahora = datetime.now()
        for v in ventas:
            v.anulada = True
            v.fecha_anulacion = ahora
            v.motivo_anulacion = motivo
            v.anulada_por_id = admin_id

            # Devolver insumos al stock
            recetas = session.query(Receta).filter_by(producto_id=v.producto_id).all()
            for r in recetas:
                insumo = session.query(Insumo).filter_by(id=r.insumo_id).first()
                if insumo:
                    insumo.stock_actual = insumo.stock_actual + (r.cantidad * v.cantidad)

        session.commit()
        return True, f"Transacción {transaccion_id} anulada por {admin.nombre}."

    except Exception as e:
        session.rollback()
        return False, f"Error: {str(e)}"
    finally:
        session.close()