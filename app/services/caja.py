"""
Servicio de cortes de caja.

Un corte de caja agrupa las ventas hechas entre un corte y el anterior.
El sistema CALCULA y MUESTRA; el empleado INGRESA lo que realmente pasó.
"""

from datetime import datetime
from typing import List, Tuple, Optional
from app.database.connection import get_session
from app.database.models import Venta, CorteCaja, Empleado


def calcular_movimiento_desde_ultimo_corte() -> dict:
    """
    Calcula cuánto se ha vendido desde el último corte de caja.
    Devuelve un diccionario con los totales y la base inicial sugerida.
    """
    session = get_session()
    try:
        # Buscar el último corte
        ultimo_corte = session.query(CorteCaja).order_by(CorteCaja.fecha.desc()).first()

        if ultimo_corte:
            desde = ultimo_corte.fecha
            base_inicial = ultimo_corte.base_dejada  # arranca con la base que dejó el corte anterior
        else:
            # Primer corte de la historia: desde el inicio de los tiempos
            desde = datetime(2000, 1, 1)
            base_inicial = 0

        # Ventas NO anuladas desde el último corte
        ventas = session.query(Venta).filter(
            Venta.fecha > desde,
            Venta.anulada == False
        ).all()

        ventas_efectivo = 0
        ventas_transferencia = 0
        refrigerios_costo = 0
        num_transacciones = set()

        for v in ventas:
            num_transacciones.add(v.transaccion_id)
            monto = v.total or 0

            if v.tipo == "VENTA":
                if v.metodo_pago == "EFECTIVO":
                    ventas_efectivo += monto
                elif v.metodo_pago == "TRANSFERENCIA":
                    ventas_transferencia += monto
            elif v.tipo == "REFRIGERIO_COSTO":
                refrigerios_costo += monto
                # Los refrigerios a costo también entran como dinero recibido
                if v.metodo_pago == "EFECTIVO":
                    ventas_efectivo += monto
                elif v.metodo_pago == "TRANSFERENCIA":
                    ventas_transferencia += monto
            # REFRIGERIO_GRATIS no suma dinero

        return {
            "desde": desde,
            "base_inicial": base_inicial,
            "ventas_efectivo": ventas_efectivo,
            "ventas_transferencia": ventas_transferencia,
            "refrigerios_costo": refrigerios_costo,
            "num_transacciones": len(num_transacciones),
            "efectivo_esperado": base_inicial + ventas_efectivo,
        }
    finally:
        session.close()


def registrar_corte(
    empleado_id: int,
    efectivo_contado: float,
    base_dejada: float,
    efectivo_entregado: float,
    nota: Optional[str] = None,
) -> Tuple[bool, str, dict]:
    """
    Registra un corte de caja.

    El sistema calcula el movimiento, el empleado ingresa lo que contó.
    NO bloquea por diferencias, solo registra y muestra.
    """
    movimiento = calcular_movimiento_desde_ultimo_corte()

    efectivo_esperado = movimiento["efectivo_esperado"]
    # Diferencia = lo que contó vs lo que debería haber
    diferencia = efectivo_contado - efectivo_esperado

    session = get_session()
    try:
        corte = CorteCaja(
            fecha=datetime.now(),
            empleado_id=empleado_id,
            ventas_efectivo=movimiento["ventas_efectivo"],
            ventas_transferencia=movimiento["ventas_transferencia"],
            refrigerios_costo=movimiento["refrigerios_costo"],
            base_inicial=movimiento["base_inicial"],
            efectivo_contado=efectivo_contado,
            base_dejada=base_dejada,
            efectivo_entregado=efectivo_entregado,
            diferencia=diferencia,
            nota=nota,
        )
        session.add(corte)
        session.commit()

        return True, "Corte de caja registrado.", {
            "efectivo_esperado": efectivo_esperado,
            "efectivo_contado": efectivo_contado,
            "diferencia": diferencia,
            "base_dejada": base_dejada,
            "efectivo_entregado": efectivo_entregado,
        }
    except Exception as e:
        session.rollback()
        return False, f"Error: {str(e)}", {}
    finally:
        session.close()


def obtener_cortes_recientes(limite: int = 20) -> List[dict]:
    """Devuelve los últimos N cortes de caja."""
    session = get_session()
    try:
        cortes = session.query(CorteCaja).order_by(CorteCaja.fecha.desc()).limit(limite).all()
        return [
            {
                "id": c.id,
                "fecha": c.fecha,
                "empleado": c.empleado.nombre if c.empleado else "?",
                "ventas_efectivo": c.ventas_efectivo,
                "ventas_transferencia": c.ventas_transferencia,
                "refrigerios_costo": c.refrigerios_costo,
                "base_inicial": c.base_inicial,
                "efectivo_contado": c.efectivo_contado,
                "base_dejada": c.base_dejada,
                "efectivo_entregado": c.efectivo_entregado,
                "diferencia": c.diferencia,
                "nota": c.nota,
            }
            for c in cortes
        ]
    finally:
        session.close()