"""
Script para importar productos, insumos y recetas desde el Excel revisado.

Uso:
    python importar_excel.py

Lee el archivo 'productos_revisar.xlsx' y popula la base de datos.
Si los productos ya existen, los actualiza (no los duplica).
"""

import sys
import pandas as pd
from app.database.connection import get_session
from app.database.models import Producto, Insumo, Receta


ARCHIVO_EXCEL = "productos_revisar.xlsx"


def importar():
    print("=" * 60)
    print("IMPORTACIÓN DE DATOS DESDE EXCEL")
    print("=" * 60)

    # Leer las 3 hojas
    try:
        df_productos = pd.read_excel(ARCHIVO_EXCEL, sheet_name="PRODUCTOS")
        df_insumos = pd.read_excel(ARCHIVO_EXCEL, sheet_name="INSUMOS")
        df_recetas = pd.read_excel(ARCHIVO_EXCEL, sheet_name="RECETAS")
    except FileNotFoundError:
        print(f"\n❌ ERROR: No encontré el archivo '{ARCHIVO_EXCEL}'.")
        print("Asegúrate de que esté en la carpeta del proyecto.")
        sys.exit(1)

    print(f"\n✓ Excel leído correctamente.")
    print(f"  - {len(df_productos)} productos")
    print(f"  - {len(df_insumos)} insumos")
    print(f"  - {len(df_recetas)} recetas")

    # Abrir sesión con la base de datos
    session = get_session()

    try:
        # ============================================================
        # 1. INSUMOS (primero, porque las recetas dependen de ellos)
        # ============================================================
        print("\n--- Importando INSUMOS ---")
        insumos_creados = 0
        insumos_actualizados = 0

        for _, row in df_insumos.iterrows():
            nombre = str(row['Nombre del insumo']).strip()
            if not nombre or nombre == 'nan':
                continue

            existente = session.query(Insumo).filter_by(nombre=nombre).first()

            unidad = str(row['Unidad de compra']).strip() if pd.notna(row['Unidad de compra']) else 'unidad'
            stock_inicial = float(row['Stock inicial']) if pd.notna(row['Stock inicial']) else 0
            stock_minimo = float(row['Stock mínimo']) if pd.notna(row['Stock mínimo']) else 0
            costo = float(row['Costo paquete']) if pd.notna(row['Costo paquete']) else None

            if existente:
                existente.unidad = unidad
                existente.stock_minimo = stock_minimo
                existente.costo_unitario = costo
                insumos_actualizados += 1
            else:
                nuevo = Insumo(
                    nombre=nombre,
                    unidad=unidad,
                    stock_actual=stock_inicial,
                    stock_minimo=stock_minimo,
                    costo_unitario=costo
                )
                session.add(nuevo)
                insumos_creados += 1

        session.commit()
        print(f"  ✓ Creados: {insumos_creados} | Actualizados: {insumos_actualizados}")

        # ============================================================
        # 2. PRODUCTOS
        # ============================================================
        print("\n--- Importando PRODUCTOS ---")
        productos_creados = 0
        productos_actualizados = 0
        productos_omitidos = 0

        for _, row in df_productos.iterrows():
            nombre = str(row['Nombre del producto']).strip()
            if not nombre or nombre == 'nan':
                continue

            # Si el precio está vacío o es 0, omitir
            precio = row['Precio venta']
            if pd.isna(precio) or float(precio) == 0:
                productos_omitidos += 1
                continue

            popularidad = str(row['Popularidad (A/B/C)']).strip() if pd.notna(row['Popularidad (A/B/C)']) else 'B'
            categoria = str(row['Categoría']).strip() if pd.notna(row['Categoría']) else None

            # Combinamos popularidad + categoría en el campo categoría
            cat_completa = f"[{popularidad}] {categoria}" if categoria else f"[{popularidad}]"

            existente = session.query(Producto).filter_by(nombre=nombre).first()

            if existente:
                existente.precio = float(precio)
                existente.categoria = cat_completa
                existente.activo = True
                productos_actualizados += 1
            else:
                nuevo = Producto(
                    nombre=nombre,
                    precio=float(precio),
                    categoria=cat_completa,
                    activo=True
                )
                session.add(nuevo)
                productos_creados += 1

        session.commit()
        print(f"  ✓ Creados: {productos_creados} | Actualizados: {productos_actualizados} | Omitidos (sin precio): {productos_omitidos}")

        # ============================================================
        # 3. RECETAS (al final, para que productos e insumos ya existan)
        # ============================================================
        print("\n--- Importando RECETAS ---")
        # Borrar recetas anteriores para evitar duplicados
        session.query(Receta).delete()
        session.commit()

        recetas_creadas = 0
        recetas_omitidas = 0

        for _, row in df_recetas.iterrows():
            nombre_producto = str(row['Producto']).strip()
            nombre_insumo = str(row['Insumo']).strip()
            cantidad = row['Cantidad por venta']

            if pd.isna(cantidad) or not nombre_producto or not nombre_insumo:
                continue

            producto = session.query(Producto).filter_by(nombre=nombre_producto).first()
            insumo = session.query(Insumo).filter_by(nombre=nombre_insumo).first()

            if not producto:
                print(f"  ⚠ Producto no encontrado: '{nombre_producto}' (receta omitida)")
                recetas_omitidas += 1
                continue
            if not insumo:
                print(f"  ⚠ Insumo no encontrado: '{nombre_insumo}' (receta omitida)")
                recetas_omitidas += 1
                continue

            nueva_receta = Receta(
                producto_id=producto.id,
                insumo_id=insumo.id,
                cantidad=float(cantidad)
            )
            session.add(nueva_receta)
            recetas_creadas += 1

        session.commit()
        print(f"  ✓ Creadas: {recetas_creadas} | Omitidas: {recetas_omitidas}")

        # ============================================================
        # RESUMEN FINAL
        # ============================================================
        print("\n" + "=" * 60)
        print("✅ IMPORTACIÓN COMPLETADA")
        print("=" * 60)
        print(f"Total productos en BD: {session.query(Producto).count()}")
        print(f"Total insumos en BD:   {session.query(Insumo).count()}")
        print(f"Total recetas en BD:   {session.query(Receta).count()}")
        print()

    except Exception as e:
        session.rollback()
        print(f"\n❌ ERROR durante la importación: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    importar()