from .models import ListaPrecio, Articulo, PrecioArticulo, ReglaPrecio
from decimal import Decimal
from datetime import date
from django.db.models import Q

class PrecioService:
    """
    Clase que encapsula toda la lógica de negocio para el cálculo de precios.
    """

    @staticmethod
    def calcular_precio_final(
        empresa_id: int,
        canal_venta: str,
        articulo_id: int,
        cantidad: int,
        sucursal_id: int = None,
        monto_pedido: Decimal = Decimal('0.00'),  # <-- NUEVO PARÁMETRO
        cart_items_ids: list[int] = None
    ):
        """
        Calcula el precio final para un artículo, aplicando la lista y reglas correspondientes.
        """
        # 1. Reutilizamos la función para encontrar la lista correcta
        lista_vigente = PrecioService.obtener_lista_vigente(
            empresa_id=empresa_id,
            canal_venta=canal_venta,
            sucursal_id=sucursal_id
        )

        if not lista_vigente:
            return {"error": "No se encontró una lista de precios aplicable.", "precio_final": None}

        # 2. Buscamos el precio base Y el artículo (con su costo)
        try:
            # Optimizamos la consulta para traer el artículo relacionado
            precio_articulo_obj = PrecioArticulo.objects.select_related('articulo').get(
                lista_precio=lista_vigente,
                articulo_id=articulo_id
            )
            precio_base = precio_articulo_obj.precio_base
            articulo = precio_articulo_obj.articulo # Objeto Articulo
            ultimo_costo = articulo.ultimo_costo
        except PrecioArticulo.DoesNotExist:
            return {"error": f"El artículo ID {articulo_id} no tiene un precio base definido en la lista '{lista_vigente.nombre}'.", "precio_final": None}

        # --- INICIO DE LA NUEVA LÓGICA DE REGLAS ---

        precio_final = precio_base
        reglas_aplicadas = []
        # Flag para saber si *alguna* regla aplicada nos da permiso de vender bajo costo
        permiso_venta_bajo_costo = False 

        # Obtenemos todas las reglas de la lista, ordenadas por prioridad
        reglas = lista_vigente.reglas.all() # .all() usará el 'ordering' del Meta
        if cart_items_ids is None:
            cart_items_ids = []
        
        # Convertimos la lista de IDs del carrito a un Set para búsquedas rápidas
        cart_items_set = set(cart_items_ids)
        
        # Aseguramos que el artículo actual esté en el "carrito" para la lógica de combinación
        cart_items_set.add(articulo_id)
        


