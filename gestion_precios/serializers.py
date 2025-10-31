from rest_framework import serializers
from django.db.models import Q
from datetime import date
from .models import (
    Empresa, Sucursal, LineaArticulo, GrupoArticulo, Articulo,
    ListaPrecio, PrecioArticulo, ReglaPrecio, CombinacionProducto
)
from decimal import Decimal

class ArticuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Articulo
        fields = '__all__' # Expondrá todos los campos del modelo

class PrecioArticuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrecioArticulo
        fields = '__all__'

class ReglaPrecioSerializer(serializers.ModelSerializer):
    """
    Serializador para ReglaPrecio con validación de duplicados
    y manejo explícito de ForeignKeys opcionales.
    """
    
    # --- INICIO DE LA SOLUCIÓN ---
    # Le decimos a DRF explícitamente cómo manejar estos campos FK.
    # Aceptan `null` y no son requeridos en la petición.
    aplica_articulo = serializers.PrimaryKeyRelatedField(
        queryset=Articulo.objects.all(),
        allow_null=True,
        required=False
    )
    aplica_grupo = serializers.PrimaryKeyRelatedField(
        queryset=GrupoArticulo.objects.all(),
        allow_null=True,
        required=False
    )
    aplica_linea = serializers.PrimaryKeyRelatedField(
        queryset=LineaArticulo.objects.all(),
        allow_null=True,
        required=False
    )
    aplica_combinacion = serializers.PrimaryKeyRelatedField(
        queryset=CombinacionProducto.objects.all(),
        allow_null=True,
        required=False
    )
    # --- FIN DE LA SOLUCIÓN ---
    