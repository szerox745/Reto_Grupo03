# EN: gestion_precios/management/commands/populate_data.py

import random
from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction

# Importamos todos los modelos
from gestion_precios.models import (
    Empresa, Sucursal, LineaArticulo, GrupoArticulo, Articulo,
    ListaPrecio, PrecioArticulo, ReglaPrecio, CombinacionProducto
)

class Command(BaseCommand):
    help = 'Llena la base de datos con datos de prueba para el motor de precios.'

    @transaction.atomic  # Usamos una transacción para que todo falle si algo falla
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando el llenado de datos...'))

        # Limpiamos la base de datos (excepto usuarios)
        self.stdout.write('Limpiando datos antiguos...')
        Articulo.objects.all().delete()
        LineaArticulo.objects.all().delete()
        GrupoArticulo.objects.all().delete()
        ListaPrecio.objects.all().delete() # Borra en cascada PrecioArticulo, ReglaPrecio, etc.
        Sucursal.objects.all().delete()
        Empresa.objects.all().delete()

        # --- 1. CREACIÓN DE MODELOS BASE ---
        self.stdout.write('Creando Empresas y Sucursales...')
        empresa_a = Empresa.objects.create(nombre='Empresa Principal S.A.')
        suc_lima = Sucursal.objects.create(empresa=empresa_a, nombre='Sucursal Lima')
        suc_aqp = Sucursal.objects.create(empresa=empresa_a, nombre='Sucursal Arequipa')

        self.stdout.write('Creando Líneas y Grupos...')
        linea_tecno = LineaArticulo.objects.create(nombre='Tecnología')
        linea_hogar = LineaArticulo.objects.create(nombre='Hogar')
        grupo_laptops = GrupoArticulo.objects.create(nombre='Laptops')
        grupo_muebles = GrupoArticulo.objects.create(nombre='Muebles')

        # --- 2. CREACIÓN DE ARTÍCULOS ---
        self.stdout.write('Creando Artículos...')
        # Artículo para probar venta bajo costo
        art_laptop = Articulo.objects.create(
            linea=linea_tecno, grupo=grupo_laptops, sku='TEC-LAP-001', 
            nombre='Laptop Pro Modelo X', ultimo_costo=Decimal('1500.00')
        )
        # Artículo para probar reglas de grupo
        art_mouse = Articulo.objects.create(
            linea=linea_tecno, grupo=grupo_laptops, sku='TEC-LAP-002', 
            nombre='Mouse Gamer', ultimo_costo=Decimal('80.00')
        )
        # Artículo para probar combinación
        art_teclado = Articulo.objects.create(
            linea=linea_tecno, grupo=grupo_laptops, sku='TEC-LAP-003', 
            nombre='Teclado Mecánico', ultimo_costo=Decimal('120.00')
        )
        # Artículo para probar otra lista de precios
        art_silla = Articulo.objects.create(
            linea=linea_hogar, grupo=grupo_muebles, sku='HOG-MUE-001', 
            nombre='Silla de Oficina', ultimo_costo=Decimal('200.00')
        )

        # --- 3. CREACIÓN DE LISTAS DE PRECIOS ---
        self.stdout.write('Creando Listas de Precios...')
        hoy = date.today()
        
        # Lista E-commerce (para Sucursal Lima)
        lista_ecommerce = ListaPrecio.objects.create(
            empresa=empresa_a,
            sucursal=suc_lima,
            nombre='Lista E-commerce Lima',
            canal_venta='ECOMMERCE',
            fecha_inicio_vigencia=hoy - timedelta(days=30),
            activa=True
        )
        
        # Lista Tienda (para Sucursal Arequipa)
        lista_tienda_aqp = ListaPrecio.objects.create(
            empresa=empresa_a,
            sucursal=suc_aqp,
            nombre='Lista Tienda Arequipa',
            canal_venta='TIENDA',
            fecha_inicio_vigencia=hoy,
            activa=True
        )

        # --- 4. ASIGNACIÓN DE PRECIOS BASE (PrecioArticulo) ---
        self.stdout.write('Asignando precios base...')
        PrecioArticulo.objects.create(lista_precio=lista_ecommerce, articulo=art_laptop, precio_base=Decimal('2000.00'))
        PrecioArticulo.objects.create(lista_precio=lista_ecommerce, articulo=art_mouse, precio_base=Decimal('120.00'))
        PrecioArticulo.objects.create(lista_precio=lista_ecommerce, articulo=art_teclado, precio_base=Decimal('180.00'))
        
        PrecioArticulo.objects.create(lista_precio=lista_tienda_aqp, articulo=art_silla, precio_base=Decimal('300.00'))
        PrecioArticulo.objects.create(lista_precio=lista_tienda_aqp, articulo=art_laptop, precio_base=Decimal('2100.00'))

        # --- 5. CREACIÓN DE REGLAS DE PRECIO ---
        self.stdout.write('Creando Reglas de Precio...')

        # Regla 1: Descuento grande que REQUIERE autorización (para art_laptop)
        ReglaPrecio.objects.create(
            lista_precio=lista_ecommerce,
            nombre_regla='Cyberday Laptop (sin permiso)',
            tipo_regla='PORCENTAJE',
            valor_regla=Decimal('30.00'), # 30% de 2000 = 1400. (Costo es 1500)
            condicion='CANTIDAD_MINIMA',
            condicion_valor=Decimal('1'),
            aplica_articulo=art_laptop,
            prioridad=10,
            permite_venta_bajo_costo=False # No permite
        )
        
        # Regla 2: Descuento grande CON autorización (para art_laptop)
        # La creamos en una lista diferente para probar
        ReglaPrecio.objects.create(
            lista_precio=lista_tienda_aqp, # Diferente lista
            nombre_regla='Cyberday Laptop (CON permiso)',
            tipo_regla='PORCENTAJE',
            valor_regla=Decimal('40.00'), # 40% de 2100 = 1260. (Costo es 1500)
            condicion='CANTIDAD_MINIMA',
            condicion_valor=Decimal('1'),
            aplica_articulo=art_laptop,
            prioridad=10,
            permite_venta_bajo_costo=True # SÍ permite
        )

        # Regla 3: Descuento por volumen (para art_mouse)
        ReglaPrecio.objects.create(
            lista_precio=lista_ecommerce,
            nombre_regla='Descuento x3 Mouse',
            tipo_regla='MONTO_FIJO',
            valor_regla=Decimal('10.00'), # 10 soles fijos
            condicion='CANTIDAD_MINIMA',
            condicion_valor=Decimal('3'), # Si lleva 3 o más
            aplica_articulo=art_mouse,
            prioridad=20
        )
        
        # Regla 4: Descuento por monto de pedido (Regla General)
        ReglaPrecio.objects.create(
            lista_precio=lista_ecommerce,
            nombre_regla='Descuento 10% en pedidos > 5000',
            tipo_regla='PORCENTAJE',
            valor_regla=Decimal('10.00'),
            condicion='MONTO_MINIMO',
            condicion_valor=Decimal('5000.00'), # Si el pedido total es > 5000
            prioridad=100 # Se aplica al final
        )

        # --- 6. CREACIÓN DE COMBINACIONES ---
        self.stdout.write('Creando Combinaciones...')
        combo_teclado_mouse = CombinacionProducto.objects.create(
            lista_precio=lista_ecommerce,
            nombre='Combo Teclado + Mouse'
        )
        combo_teclado_mouse.articulos.add(art_mouse, art_teclado)
        
        # Regla 5: Regla de Combinación
        ReglaPrecio.objects.create(
            lista_precio=lista_ecommerce,
            nombre_regla='Descuento Combo Teclado+Mouse',
            tipo_regla='MONTO_FIJO',
            valor_regla=Decimal('25.00'), # 25 soles de descuento
            condicion='CANTIDAD_MINIMA', # Condición base (se ignora por la lógica de combo)
            condicion_valor=Decimal('1'),
            aplica_combinacion=combo_teclado_mouse,
            prioridad=5 # Muy alta prioridad
        )

        self.stdout.write(self.style.SUCCESS('¡Llenado de datos completado exitosamente!'))