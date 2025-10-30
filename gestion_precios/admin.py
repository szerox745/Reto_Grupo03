from django.contrib import admin
from .models import (
    Empresa,
    Sucursal,
    LineaArticulo,
    GrupoArticulo,
    Articulo,
    ListaPrecio,
    PrecioArticulo,
    ReglaPrecio,
    CombinacionProducto,
)

@admin.register(Articulo)
class ArticuloAdmin(admin.ModelAdmin):
    list_display = ('sku', 'nombre', 'linea', 'grupo', 'ultimo_costo')
    list_filter = ('linea', 'grupo')
    search_fields = ('sku', 'nombre')

@admin.register(ListaPrecio)
class ListaPrecioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'empresa', 'sucursal', 'canal_venta', 'fecha_inicio_vigencia', 'fecha_fin_vigencia', 'activa')
    list_filter = ('empresa', 'sucursal', 'canal_venta', 'activa')
    search_fields = ('nombre',)

@admin.register(PrecioArticulo)
class PrecioArticuloAdmin(admin.ModelAdmin):
    list_display = ('articulo', 'lista_precio', 'precio_base')
    list_filter = ('lista_precio',)
    search_fields = ('articulo__nombre', 'articulo__sku')

@admin.register(ReglaPrecio)
class ReglaPrecioAdmin(admin.ModelAdmin):
    list_display = ('nombre_regla', 'lista_precio', 'tipo_regla', 'valor_regla', 'condicion', 'condicion_valor', 'prioridad', 'permite_venta_bajo_costo')
    list_filter = ('lista_precio', 'tipo_regla', 'condicion')
    search_fields = ('nombre_regla',)


# Registramos los modelos que no necesitan una personalización especial
admin.site.register(Empresa)
admin.site.register(Sucursal)
admin.site.register(LineaArticulo)
admin.site.register(GrupoArticulo)
admin.site.register(CombinacionProducto)

