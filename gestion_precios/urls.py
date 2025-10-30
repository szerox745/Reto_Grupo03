# EN: gestion_precios/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CalcularPrecioFinalAPIView, 
    ObtenerListaVigenteAPIView,
    EmpresaViewSet,
    SucursalViewSet,
    ArticuloViewSet,
    ListaPrecioViewSet,
    PrecioArticuloViewSet,
    ReglaPrecioViewSet,
    CombinacionProductoViewSet,
    LineaArticuloViewSet, GrupoArticuloViewSet
)

# 1. Crea un router
router = DefaultRouter()

# 2. Registra los ViewSets en el router
router.register(r'empresas', EmpresaViewSet)
router.register(r'sucursales', SucursalViewSet)
router.register(r'articulos', ArticuloViewSet)
router.register(r'listas-precio', ListaPrecioViewSet)
router.register(r'precios-articulo', PrecioArticuloViewSet)
router.register(r'reglas-precio', ReglaPrecioViewSet)
router.register(r'combinaciones', CombinacionProductoViewSet)
router.register(r'lineas-articulo', LineaArticuloViewSet)
router.register(r'grupos-articulo', GrupoArticuloViewSet)

# 3. Define los urlpatterns
urlpatterns = [
    # Las URLs de tus vistas APIView manuales
    path('calcular-precio/', CalcularPrecioFinalAPIView.as_view(), name='calcular-precio'),
    path('lista-vigente/', ObtenerListaVigenteAPIView.as_view(), name='lista-vigente'),
    
    # Las URLs automáticas generadas por el router
    path('', include(router.urls)),
]