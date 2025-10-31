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
        
        for regla in reglas:
            
            # ... (La verificación de aplicabilidad por articulo/grupo/linea se queda igual) ...
            
            # --- INICIO DE NUEVA LÓGICA DE COMBINACIÓN ---
            
            # Verificamos si la regla es de combinación
            if regla.aplica_combinacion:
                # 1. El artículo actual debe ser parte de la combinación
                articulos_requeridos_ids = set(
                    regla.aplica_combinacion.articulos.values_list('id', flat=True)
                )
                
                if articulo_id not in articulos_requeridos_ids:
                    continue # Esta regla de combinación no es para este artículo

                # 2. Verificamos si todos los artículos de la combinación
                #    están presentes en el carrito.
                if not articulos_requeridos_ids.issubset(cart_items_set):
                    # No están todos los artículos de la combinación en el carrito.
                    continue
            
            # --- FIN DE NUEVA LÓGICA DE COMBINACIÓN ---

            # --- Verificación de Condiciones de la Regla (CANTIDAD/MONTO) ---
            condicion_cumplida = False

            # Si la regla NO es de combinación, aplicamos lógica de cantidad/monto
            if not regla.aplica_combinacion:
                if regla.condicion == 'CANTIDAD_MINIMA':
                    if cantidad >= regla.condicion_valor:
                        condicion_cumplida = True
                elif regla.condicion == 'MONTO_MINIMO':
                    if monto_pedido >= regla.condicion_valor:
                        condicion_cumplida = True
            else:
                # Si es una regla de combinación, la condición ya se cumplió
                # (todos los productos están en el carrito).
                condicion_cumplida = True

            if not condicion_cumplida:
                continue

            # --- Si llegamos aquí, la regla SE APLICA ---
            
            # 1. Aplicamos el descuento
            if regla.tipo_regla == 'PORCENTAJE':
                descuento = precio_final * (regla.valor_regla / Decimal('100.0'))
                precio_final -= descuento
            elif regla.tipo_regla == 'MONTO_FIJO':
                precio_final -= regla.valor_regla

            # 2. Registramos la regla aplicada
            reglas_aplicadas.append(regla.nombre_regla)

            # 3. Verificamos si esta regla da permiso de venta bajo costo
            if regla.permite_venta_bajo_costo:
                permiso_venta_bajo_costo = True
            
            # 4. Evitamos precios negativos
            if precio_final < Decimal('0.00'):
                precio_final = Decimal('0.00')

        # --- FIN DE LA LÓGICA DE REGLAS ---

        # 3. Validación de Costo (Lógica Final)
        autorizado_bajo_costo = False
        if precio_final < ultimo_costo:
            if permiso_venta_bajo_costo:
                # El precio es bajo costo, PERO una regla aplicada lo autorizó.
                autorizado_bajo_costo = True
            else:
                # El precio es bajo costo y NO tiene autorización.
                # Se ajusta el precio al costo.
                precio_final = ultimo_costo
                reglas_aplicadas.append("Ajuste a costo mínimo (no autorizado bajo costo)")


        # 4. Devolvemos el diccionario final
        return {
            "lista_precio_aplicada": lista_vigente.nombre,
            "precio_base": precio_base,
            "precio_final": precio_final,
            "cantidad": cantidad,
            "total": precio_final * cantidad,
            "reglas_aplicadas": reglas_aplicadas,
            "autorizado_bajo_costo": autorizado_bajo_costo
        }


    @staticmethod
    def obtener_lista_vigente(empresa_id: int, canal_venta: str, sucursal_id: int = None):
        """
        Encuentra la lista de precios más específica y aplicable para una operación.
        """
        # ... (este método se queda exactamente como estaba)
        hoy = date.today()

        filtros_base = Q(empresa_id=empresa_id) & \
                       Q(activa=True) & \
                       Q(fecha_inicio_vigencia__lte=hoy) & \
                       (Q(fecha_fin_vigencia__gte=hoy) | Q(fecha_fin_vigencia__isnull=True))

        if sucursal_id:
            lista = ListaPrecio.objects.filter(
                filtros_base &
                Q(sucursal_id=sucursal_id) &
                Q(canal_venta=canal_venta)
            ).first()
            if lista:
                return lista

            lista = ListaPrecio.objects.filter(
                filtros_base &
                Q(sucursal_id=sucursal_id) &
                Q(canal_venta='TODOS')
            ).first()
            if lista:
                return lista

        lista = ListaPrecio.objects.filter(
            filtros_base &
            Q(sucursal_id__isnull=True) &
            Q(canal_venta=canal_venta)
        ).first()
        if lista:
            return lista

        lista = ListaPrecio.objects.filter(
            filtros_base &
            Q(sucursal_id__isnull=True) &
            Q(canal_venta='TODOS')
        ).first()
        if lista:
            return lista

        return None





