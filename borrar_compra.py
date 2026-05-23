"""
Herramienta para borrar una compra de prueba y corregir el stock.
Uso: python borrar_compra.py
"""

from app.database.connection import get_session
from app.database.models import Compra, Insumo


def main():
    session = get_session()
    try:
        compras = session.query(Compra).order_by(Compra.fecha.desc()).all()

        if not compras:
            print("No hay compras registradas.")
            return

        print("\n=== COMPRAS REGISTRADAS ===")
        for c in compras:
            insumo = session.query(Insumo).filter_by(id=c.insumo_id).first()
            nombre_insumo = insumo.nombre if insumo else "?"
            print(f"  ID {c.id} | {c.fecha.strftime('%d/%m %H:%M')} | {nombre_insumo} | cantidad: {c.cantidad}")

        print()
        id_borrar = input("Escribe el ID de la compra a borrar (o Enter para cancelar): ").strip()

        if not id_borrar:
            print("Cancelado.")
            return

        compra = session.query(Compra).filter_by(id=int(id_borrar)).first()
        if not compra:
            print(f"No existe una compra con ID {id_borrar}.")
            return

        insumo = session.query(Insumo).filter_by(id=compra.insumo_id).first()
        if insumo:
            stock_antes = insumo.stock_actual
            insumo.stock_actual = insumo.stock_actual - compra.cantidad
            print(f"\nStock de '{insumo.nombre}': {stock_antes} -> {insumo.stock_actual}")

        session.delete(compra)
        session.commit()
        print(f"✓ Compra ID {id_borrar} borrada y stock corregido.")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    main()