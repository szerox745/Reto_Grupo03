from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, viewsets
from decimal import Decimal, InvalidOperation
from .services import PrecioService
from .models import (
    Empresa, Sucursal, Articulo, ListaPrecio, 
    PrecioArticulo, ReglaPrecio, CombinacionProducto, LineaArticulo, GrupoArticulo
)
from .serializers import ( # <-- 3. IMPORTA TODOS LOS SERIALIZERS
    EmpresaSerializer, SucursalSerializer, ArticuloSerializer, 
    ListaPrecioSerializer, PrecioArticuloSerializer, 
    ReglaPrecioSerializer, CombinacionProductoSerializer,
    ResultadoCalculoSerializer, LineaArticuloSerializer, GrupoArticuloSerializer
)

class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer

class SucursalViewSet(viewsets.ModelViewSet):
    queryset = Sucursal.objects.all()
    serializer_class = SucursalSerializer

class ArticuloViewSet(viewsets.ModelViewSet):
    queryset = Articulo.objects.all()
    serializer_class = ArticuloSerializer
    
class ListaPrecioViewSet(viewsets.ModelViewSet):
    queryset = ListaPrecio.objects.all()
    serializer_class = ListaPrecioSerializer

class PrecioArticuloViewSet(viewsets.ModelViewSet):
    queryset = PrecioArticulo.objects.all()
    serializer_class = PrecioArticuloSerializer

class ReglaPrecioViewSet(viewsets.ModelViewSet):
    queryset = ReglaPrecio.objects.all()
    serializer_class = ReglaPrecioSerializer

class CombinacionProductoViewSet(viewsets.ModelViewSet):
    queryset = CombinacionProducto.objects.all()
    serializer_class = CombinacionProductoSerializer

class LineaArticuloViewSet(viewsets.ModelViewSet):
    queryset = LineaArticulo.objects.all()
    serializer_class = LineaArticuloSerializer

class GrupoArticuloViewSet(viewsets.ModelViewSet):
    queryset = GrupoArticulo.objects.all()
    serializer_class = GrupoArticuloSerializer

class ObtenerListaVigenteAPIView(APIView):
    """
    Endpoint para obtener la lista de precios vigente según los parámetros.
    """
    def get(self, request, *args, **kwargs):
        """
        Maneja las peticiones GET.
        Espera los siguientes parámetros en la URL (query params):
        - empresa_id (requerido)
        - canal_venta (requerido)
        - sucursal_id (opcional)
        """
        # 1. Obtener parámetros de la URL
        empresa_id = request.query_params.get('empresa_id')
        canal_venta = request.query_params.get('canal_venta')
        sucursal_id = request.query_params.get('sucursal_id')

        # 2. Validar que los parámetros requeridos existan
        if not empresa_id or not canal_venta:
            return Response(
                {"error": "Los parámetros 'empresa_id' y 'canal_venta' son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Llamar a nuestro "cerebro" (el servicio)
        try:
            lista_vigente = PrecioService.obtener_lista_vigente(
                empresa_id=int(empresa_id),
                canal_venta=canal_venta.upper(), # Convertimos a mayúsculas por si acaso
                sucursal_id=int(sucursal_id) if sucursal_id else None
            )
        except (ValueError, TypeError):
             return Response(
                {"error": "Los IDs deben ser números enteros válidos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Preparar y enviar la respuesta
        if lista_vigente:
            # Si encontramos una lista, la "traducimos" con el serializer
            serializer = ListaPrecioSerializer(lista_vigente)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # Si el servicio no encontró nada, respondemos con un error 404
            return Response(
                {"mensaje": "No se encontró una lista de precios aplicable para los criterios dados."},
                status=status.HTTP_404_NOT_FOUND
            )

        
# --- AÑADE ESTA NUEVA CLASE ---
class CalcularPrecioFinalAPIView(APIView):
    """
    Endpoint para calcular el precio final de un artículo.
    """
    def get(self, request, *args, **kwargs):
        # 1. Obtener parámetros (añadimos monto_pedido)
        empresa_id = request.query_params.get('empresa_id')
        canal_venta = request.query_params.get('canal_venta')
        sucursal_id = request.query_params.get('sucursal_id')
        articulo_id = request.query_params.get('articulo_id')
        cantidad = request.query_params.get('cantidad')
        monto_pedido = request.query_params.get('monto_pedido') # <-- NUEVO
        cart_items_str = request.query_params.get('cart_items', '') # ej: "1,5,23"
        # 2. Validar requeridos
        required_params = {'empresa_id': empresa_id, 'canal_venta': canal_venta, 'articulo_id': articulo_id, 'cantidad': cantidad}
        for param, value in required_params.items():
            if not value:
                return Response({"error": f"El parámetro '{param}' es requerido."}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Validar y castear tipos
        try:
            empresa_id_int = int(empresa_id)
            sucursal_id_int = int(sucursal_id) if sucursal_id else None
            articulo_id_int = int(articulo_id)
            cantidad_int = int(cantidad)

            # Validar monto_pedido (es opcional, default 0)
            monto_pedido_decimal = Decimal('0.00')
            if monto_pedido:
                monto_pedido_decimal = Decimal(monto_pedido)
            # Procesar cart_items
            cart_items_ids = []
            if cart_items_str:
                cart_items_ids = [int(item_id) for item_id in cart_items_str.split(',') if item_id.isdigit()]

        except (ValueError, TypeError, InvalidOperation):
             return Response({"error": "Los IDs, cantidad y monto_pedido deben ser números válidos."}, status=status.HTTP_400_BAD_REQUEST)

        # 4. Llamar al servicio (con el nuevo parámetro)
        resultado = PrecioService.calcular_precio_final(
            empresa_id=empresa_id_int,
            canal_venta=canal_venta.upper(),
            sucursal_id=sucursal_id_int,
            articulo_id=articulo_id_int,
            cantidad=cantidad_int,
            monto_pedido=monto_pedido_decimal, # <-- PASAMOS EL NUEVO VALOR
            cart_items_ids=cart_items_ids
        )

        # 5. Enviar respuesta (esta lógica se queda igual)
        if "error" in resultado:
            return Response(resultado, status=status.HTTP_404_NOT_FOUND)
        else:
            serializer = ResultadoCalculoSerializer(resultado)
            return Response(serializer.data, status=status.HTTP_200_OK)