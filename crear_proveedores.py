"""
Script para crear los proveedores iniciales.
Ejecutar UNA SOLA VEZ.
"""

from app.database.connection import get_session
from app.database.models import Proveedor


PROVEEDORES_INICIALES = [
    {"nombre": "Panadería", "contacto": "", "notas": "Empanadas, buñuelos, pasteles"},
    {"nombre": "NOVAVENTA", "contacto": "", "notas": "Polvos para máquina de café"},
    {"nombre": "Las Becadas", "contacto": "", "notas": "Pasabocas Becadas"},
    {"nombre": "Artesanales", "contacto": "", "notas": "Pasabocas artesanales"},
    {"nombre": "Distribuidor general", "contacto": "", "notas": "Bebidas, galletas, dulces, suministros"},
]


def crear_proveedores():
    session = get_session()
    try:
        creados = 0
        existentes = 0
        for p in PROVEEDORES_INICIALES:
            existe = session.query(Proveedor).filter_by(nombre=p["nombre"]).first()
            if existe:
                existentes += 1
                print(f"  ⊙ {p['nombre']} ya existe")
            else:
                nuevo = Proveedor(**p)
                session.add(nuevo)
                creados += 1
                print(f"  ✓ {p['nombre']}")
        session.commit()
        print(f"\nResumen: {creados} creados, {existentes} ya existían")
    finally:
        session.close()


if __name__ == "__main__":
    crear_proveedores()