"""
Modelos de datos del sistema.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime,
    ForeignKey, Boolean
)
from sqlalchemy.orm import relationship

from app.database.connection import Base


class Proveedor(Base):
    __tablename__ = "proveedores"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False, unique=True)
    contacto = Column(String, nullable=True)
    notas = Column(String, nullable=True)
    insumos = relationship("Insumo", back_populates="proveedor")
    compras = relationship("Compra", back_populates="proveedor")

    def __repr__(self):
        return f"<Proveedor {self.nombre}>"


class Insumo(Base):
    __tablename__ = "insumos"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False, unique=True)
    unidad = Column(String, nullable=False)
    stock_actual = Column(Float, nullable=False, default=0)
    stock_minimo = Column(Float, nullable=False, default=0)
    costo_unitario = Column(Float, nullable=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True)
    proveedor = relationship("Proveedor", back_populates="insumos")
    en_recetas = relationship("Receta", back_populates="insumo")
    compras = relationship("Compra", back_populates="insumo")
    ajustes = relationship("AjusteInventario", back_populates="insumo")

    def __repr__(self):
        return f"<Insumo {self.nombre}: {self.stock_actual} {self.unidad}>"


class Producto(Base):
    __tablename__ = "productos"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False, unique=True)
    precio = Column(Float, nullable=False)
    categoria = Column(String, nullable=True)
    activo = Column(Boolean, default=True)
    ingredientes = relationship("Receta", back_populates="producto")
    ventas = relationship("Venta", back_populates="producto")

    def __repr__(self):
        return f"<Producto {self.nombre}: ${self.precio}>"


class Receta(Base):
    __tablename__ = "recetas"
    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False)
    cantidad = Column(Float, nullable=False)
    producto = relationship("Producto", back_populates="ingredientes")
    insumo = relationship("Insumo", back_populates="en_recetas")


class Compra(Base):
    __tablename__ = "compras"
    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, default=datetime.now)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False)
    cantidad = Column(Float, nullable=False)
    costo_total = Column(Float, nullable=True)
    notas = Column(String, nullable=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True)
    empleado_id = Column(Integer, ForeignKey("empleados.id"), nullable=True)

    insumo = relationship("Insumo", back_populates="compras")
    proveedor = relationship("Proveedor", back_populates="compras")
    empleado = relationship("Empleado")

    def __repr__(self):
        return f"<Compra {self.fecha.date()}: {self.cantidad} {self.insumo.nombre}>"


class Empleado(Base):
    __tablename__ = "empleados"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False, unique=True)
    pin = Column(String(4), nullable=False, unique=True)
    rol = Column(String, nullable=False, default="CAJERO")
    activo = Column(Boolean, default=True)
    ventas = relationship("Venta", back_populates="empleado", foreign_keys="Venta.empleado_id")

    def __repr__(self):
        return f"<Empleado {self.nombre} ({self.rol})>"


class Venta(Base):
    __tablename__ = "ventas"
    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, default=datetime.now)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Integer, nullable=False, default=1)
    precio_unitario = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    tipo = Column(String, nullable=False, default="VENTA")
    empleado_id = Column(Integer, ForeignKey("empleados.id"), nullable=True)
    transaccion_id = Column(String, nullable=True)
    metodo_pago = Column(String, nullable=True)
    monto_recibido = Column(Float, nullable=True)
    vuelto = Column(Float, nullable=True)
    anulada = Column(Boolean, default=False)
    fecha_anulacion = Column(DateTime, nullable=True)
    motivo_anulacion = Column(String, nullable=True)
    anulada_por_id = Column(Integer, ForeignKey("empleados.id"), nullable=True)

    producto = relationship("Producto", back_populates="ventas")
    empleado = relationship("Empleado", back_populates="ventas", foreign_keys=[empleado_id])
    anulada_por = relationship("Empleado", foreign_keys=[anulada_por_id])

    def __repr__(self):
        return f"<Venta {self.fecha.date()}: {self.cantidad}x {self.producto.nombre}>"


class AjusteInventario(Base):
    """
    Ajustes manuales del stock (no son compras ni ventas).
    Casos: conteo inicial, conteo periódico, pérdida, daño, otro.
    """
    __tablename__ = "ajustes_inventario"
    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, default=datetime.now)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False)
    stock_anterior = Column(Float, nullable=False)
    stock_nuevo = Column(Float, nullable=False)
    diferencia = Column(Float, nullable=False)  # nuevo - anterior
    motivo = Column(String, nullable=False)  # 'CONTEO_INICIAL', 'CONTEO_PERIODICO', etc.
    notas = Column(String, nullable=True)
    empleado_id = Column(Integer, ForeignKey("empleados.id"), nullable=True)

    insumo = relationship("Insumo", back_populates="ajustes")
    empleado = relationship("Empleado")

    def __repr__(self):
        return f"<Ajuste {self.fecha.date()}: {self.insumo.nombre} {self.stock_anterior}→{self.stock_nuevo}>"
    
class CorteCaja(Base):
    __tablename__ = "cortes_caja"

    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, default=datetime.now)
    empleado_id = Column(Integer, ForeignKey("empleados.id"), nullable=True)
    ventas_efectivo = Column(Float, nullable=False, default=0)
    ventas_transferencia = Column(Float, nullable=False, default=0)
    refrigerios_costo = Column(Float, nullable=False, default=0)
    base_inicial = Column(Float, nullable=False, default=0)
    efectivo_contado = Column(Float, nullable=False, default=0)
    base_dejada = Column(Float, nullable=False, default=0)
    efectivo_entregado = Column(Float, nullable=False, default=0)
    diferencia = Column(Float, nullable=False, default=0)
    nota = Column(String, nullable=True)

    empleado = relationship("Empleado")

    def __repr__(self):
        return f"<CorteCaja {self.fecha.strftime('%d/%m %H:%M')}>"