"""
Servicio de ventas - lógica de negocio.
Aquí vive la "magia" del sistema de ventas:
- Verificación y cambio de PIN
- Registro de ventas con descuento automático de inventario
- Anulación de ventas con devolución al stock
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from app.database.connection import get_session
from app.database.models import Empleado, Producto, Receta, Insumo, Venta


# Cuántos minutos puede un cajero anular una venta sin permiso de admin
MINUTOS_VENTANA_ANULACION = 5


# ============================================================
# AUTENTICACIÓN DE EMPLEADOS
# ============================================================

def verificar_pin(pin: str) -> Optional[dict]:
    """
    Verifica si el PIN corresponde a un empleado activo.
    Devuelve un diccionario con los datos del empleado, o None si no es válido.
    """
    session = get_session()
    try:
        empleado = session.query(Empleado).filter_by(pin=pin, activo=True).first()
        if empleado:
            return {
                "id": empleado.id,
                "nombre": empleado.nombre,
                "rol": empleado.rol,
            }
        return None
    finally:
        session.close()


def cambiar_pin(empleado_id: int, pin_actual: str, pin_nuevo: str) -> Tuple[bool, str]:
    """
    Cambia el PIN de un empleado.
    Devuelve (exitoso: bool, mensaje: str).
    """
    if len(pin_nuevo) != 4 or not pin_nuevo.isdigit():
        return False, "El PIN nuevo debe tener exactamente 4 dígitos."

    if pin_actual == pin_nuevo:
        return False, "El PIN nuevo debe ser diferente al actual."

    session = get_session()
    try:
        empleado = session.query(Empleado).filter_by(id=empleado_id).first()
        if not empleado:
            return False, "Empleado no encontrado."

        if empleado.pin != pin_actual:
            return False, "El PIN actual es incorrecto."

        otro = session.query(Empleado).filter(
            Empleado.pin == pin_nuevo,
            Empleado.id != empleado_id
        ).first()
        if otro:
            return False, "Ese PIN ya está siendo usado por otro empleado."

        empleado.pin = pin_nuevo
        session.commit()
        return True, "PIN cambiado correctamente."

    except Exception as e:
        session.rollback()
        return False, f"Error: {str(e)}"
    finally:
        session.close()


# ============================================================
# REGISTRAR VENTAS
# ============================================================

def registrar_venta(
    items_carrito: List[dict],
    empleado_id: int,
    metodo_pago: str,
    monto_recibido: float
) -> Tuple[bool, str, dict]:
    """
    Registra una venta completa.
    items_carrito: [{"producto_id": int, "cantidad": int, "precio": float}, ...]
    metodo_pago: "EFECTIVO" o "TRANSFERENCIA"
    
    Devuelve (exitoso, mensaje, datos_extra).
    datos_extra incluye: {"total": float, "vuelto": float, "advertencias": [str]}
    """
    if not items_carrito:
        return False, "El carrito está vacío.", {}

    if metodo_pago not in ("EFECTIVO", "TRANSFERENCIA"):
        return False, "Método de pago inválido.", {}

    # Calcular total
    total_venta = sum(item["cantidad"] * item["precio"] for item in items_carrito)

    if monto_recibido < total_venta:
        return False, f"Monto recibido (${int(monto_recibido):,}) menor que el total (${int(total_venta):,}).".replace(",", "."), {}

    vuelto = monto_recibido - total_venta
    transaccion_id = str(uuid.uuid4())[:8]  # ID corto para agrupar
    advertencias = []

    session = get_session()
    try:
        for item in items_carrito:
            producto = session.query(Producto).filter_by(id=item["producto_id"]).first()
            if not producto:
                session.rollback()
                return False, f"Producto ID {item['producto_id']} no encontrado.", {}

            cantidad = item["cantidad"]
            precio = item["precio"]
            total_item = cantidad * precio

            # Crear el registro de venta
            nueva_venta = Venta(
                fecha=datetime.now(),
                producto_id=producto.id,
                cantidad=cantidad,
                precio_unitario=precio,
                total=total_item,
                empleado_id=empleado_id,
                transaccion_id=transaccion_id,
                metodo_pago=metodo_pago,
                monto_recibido=monto_recibido if item == items_carrito[0] else None,  # solo en el primer item
                vuelto=vuelto if item == items_carrito[0] else None,
                anulada=False,
            )
            session.add(nueva_venta)

            # Descontar insumos según receta
            recetas = session.query(Receta).filter_by(producto_id=producto.id).all()
            for receta in recetas:
                insumo = session.query(Insumo).filter_by(id=receta.insumo_id).first()
                if not insumo:
                    continue
                cantidad_descontar = receta.cantidad * cantidad
                insumo.stock_actual = insumo.stock_actual - cantidad_descontar

                if insumo.stock_actual < 0:
                    advertencias.append(
                        f"⚠️ {insumo.nombre} en NEGATIVO ({insumo.stock_actual:.2f} {insumo.unidad})"
                    )
                elif insumo.stock_actual <= insumo.stock_minimo:
                    advertencias.append(
                        f"⚠️ {insumo.nombre} bajo mínimo ({insumo.stock_actual:.2f} {insumo.unidad})"
                    )

        session.commit()
        return True, "Venta registrada", {
            "total": total_venta,
            "vuelto": vuelto,
            "transaccion_id": transaccion_id,
            "advertencias": advertencias
        }

    except Exception as e:
        session.rollback()
        return False, f"Error al registrar: {str(e)}", {}
    finally:
        session.close()


# ============================================================
# ANULAR VENTAS
# ============================================================

def obtener_ventas_anulables() -> List[dict]:
    """
    Devuelve las ventas de los últimos 5 minutos que NO han sido anuladas.
    Las agrupa por transaccion_id.
    """
    session = get_session()
    try:
        limite = datetime.now() - timedelta(minutes=MINUTOS_VENTANA_ANULACION)
        
        ventas = session.query(Venta).filter(
            Venta.fecha >= limite,
            Venta.anulada == False,
            Venta.transaccion_id.isnot(None)
        ).order_by(Venta.fecha.desc()).all()

        # Agrupar por transaccion_id
        transacciones = {}
        for v in ventas:
            tid = v.transaccion_id
            if tid not in transacciones:
                transacciones[tid] = {
                    "transaccion_id": tid,
                    "fecha": v.fecha,
                    "empleado": v.empleado.nombre if v.empleado else "?",
                    "metodo_pago": v.metodo_pago,
                    "items": [],
                    "total": 0,
                }
            transacciones[tid]["items"].append({
                "venta_id": v.id,
                "producto": v.producto.nombre,
                "cantidad": v.cantidad,
                "precio": v.precio_unitario,
                "subtotal": v.total,
            })
            transacciones[tid]["total"] += v.total

        # Convertir a lista ordenada por fecha desc
        return sorted(transacciones.values(), key=lambda x: x["fecha"], reverse=True)
    finally:
        session.close()


def anular_transaccion(
    transaccion_id: str,
    empleado_que_anula_id: int,
    motivo: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Anula todas las ventas de una transacción y devuelve insumos al stock.
    """
    session = get_session()
    try:
        ventas = session.query(Venta).filter_by(transaccion_id=transaccion_id).all()
        
        if not ventas:
            return False, "Transacción no encontrada."

        if any(v.anulada for v in ventas):
            return False, "Esta transacción ya fue anulada."

        # Verificar ventana de tiempo (5 minutos)
        primera_venta = min(ventas, key=lambda v: v.fecha)
        tiempo_pasado = datetime.now() - primera_venta.fecha
        if tiempo_pasado > timedelta(minutes=MINUTOS_VENTANA_ANULACION):
            # Solo permitir si el que anula es ADMIN
            empleado = session.query(Empleado).filter_by(id=empleado_que_anula_id).first()
            if not empleado or empleado.rol != "ADMIN":
                return False, f"Solo administradores pueden anular ventas con más de {MINUTOS_VENTANA_ANULACION} minutos."

        # Marcar como anuladas y devolver insumos
        ahora = datetime.now()
        for v in ventas:
            v.anulada = True
            v.fecha_anulacion = ahora
            v.motivo_anulacion = motivo
            v.anulada_por_id = empleado_que_anula_id

            # Devolver insumos al stock
            recetas = session.query(Receta).filter_by(producto_id=v.producto_id).all()
            for r in recetas:
                insumo = session.query(Insumo).filter_by(id=r.insumo_id).first()
                if insumo:
                    insumo.stock_actual = insumo.stock_actual + (r.cantidad * v.cantidad)

        session.commit()
        return True, f"Transacción {transaccion_id} anulada correctamente."

    except Exception as e:
        session.rollback()
        return False, f"Error al anular: {str(e)}"
    finally:
        session.close()


# ============================================================
# CONSULTAS
# ============================================================

def obtener_productos_activos() -> List[dict]:
    """Devuelve todos los productos activos para mostrar en la pantalla."""
    session = get_session()
    try:
        productos = session.query(Producto).filter_by(activo=True).order_by(Producto.nombre).all()
        return [
            {
                "id": p.id,
                "nombre": p.nombre,
                "precio": p.precio,
                "categoria": p.categoria or "Sin categoría",
            }
            for p in productos
        ]
    finally:
        session.close()
# ============================================================
# REFRIGERIOS / CONSUMO DE EMPLEADOS
# ============================================================

def registrar_refrigerio(
    items_carrito: List[dict],
    empleado_id: int,
    es_gratis: bool,
    monto_pagado: float = 0,
    metodo_pago: Optional[str] = None,
) -> Tuple[bool, str, dict]:
    """
    Registra un consumo de empleado (refrigerio).

    items_carrito: [{"producto_id": int, "cantidad": int, "precio": float}, ...]
    es_gratis: True = refrigerio gratis ($0). False = a precio de costo.
    monto_pagado: lo que el empleado paga (solo si NO es gratis).
    metodo_pago: "EFECTIVO" o "TRANSFERENCIA" (solo si NO es gratis).

    Devuelve (exitoso, mensaje, datos_extra).
    """
    if not items_carrito:
        return False, "No hay productos seleccionados.", {}

    # Determinar el tipo
    if es_gratis:
        tipo = "REFRIGERIO_GRATIS"
        total_refrigerio = 0
        metodo_final = None
    else:
        tipo = "REFRIGERIO_COSTO"
        if monto_pagado <= 0:
            return False, "Debes ingresar el monto a pagar.", {}
        if metodo_pago not in ("EFECTIVO", "TRANSFERENCIA"):
            return False, "Método de pago inválido.", {}
        total_refrigerio = monto_pagado
        metodo_final = metodo_pago

    transaccion_id = str(uuid.uuid4())[:8]
    advertencias = []

    session = get_session()
    try:
        for item in items_carrito:
            producto = session.query(Producto).filter_by(id=item["producto_id"]).first()
            if not producto:
                session.rollback()
                return False, f"Producto ID {item['producto_id']} no encontrado.", {}

            cantidad = item["cantidad"]

            # Crear el registro. El "total" del refrigerio se pone solo en el primer item.
            registro = Venta(
                fecha=datetime.now(),
                producto_id=producto.id,
                cantidad=cantidad,
                precio_unitario=item["precio"],
                total=(total_refrigerio if item == items_carrito[0] else 0),
                empleado_id=empleado_id,
                transaccion_id=transaccion_id,
                metodo_pago=metodo_final,
                monto_recibido=(total_refrigerio if (not es_gratis and item == items_carrito[0]) else None),
                vuelto=0,
                anulada=False,
                tipo=tipo,
            )
            session.add(registro)

            # Descontar insumos según receta (igual que una venta normal)
            recetas = session.query(Receta).filter_by(producto_id=producto.id).all()
            for receta in recetas:
                insumo = session.query(Insumo).filter_by(id=receta.insumo_id).first()
                if not insumo:
                    continue
                cantidad_descontar = receta.cantidad * cantidad
                insumo.stock_actual = insumo.stock_actual - cantidad_descontar

                if insumo.stock_actual < 0:
                    advertencias.append(
                        f"⚠️ {insumo.nombre} en NEGATIVO ({insumo.stock_actual:.2f} {insumo.unidad})"
                    )
                elif insumo.stock_actual <= insumo.stock_minimo:
                    advertencias.append(
                        f"⚠️ {insumo.nombre} bajo mínimo ({insumo.stock_actual:.2f} {insumo.unidad})"
                    )

        session.commit()

        if es_gratis:
            msg = "Refrigerio gratis registrado."
        else:
            msg = f"Consumo registrado. Pagado: ${int(total_refrigerio):,}".replace(",", ".")

        return True, msg, {
            "tipo": tipo,
            "total": total_refrigerio,
            "transaccion_id": transaccion_id,
            "advertencias": advertencias,
        }

    except Exception as e:
        session.rollback()
        return False, f"Error al registrar refrigerio: {str(e)}", {}
    finally:
        session.close()