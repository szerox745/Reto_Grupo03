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

    def validate(self, data):
        """
        Validación personalizada para evitar solapamiento de vigencias.
        """
        # Obtenemos las fechas. Si no hay fecha fin, la tratamos como "infinito"
        inicio = data.get('fecha_inicio_vigencia')
        fin = data.get('fecha_fin_vigencia')

        # Construimos el filtro base para listas que compiten
        filtros_competencia = Q(empresa=data.get('empresa')) & \
                              Q(sucursal=data.get('sucursal')) & \
                              Q(canal_venta=data.get('canal_venta')) & \
                              Q(activa=True)

        # Lógica de solapamiento
        # 1. Comprueba si la nueva lista "envuelve" a una existente
        consulta_solapamiento = Q(fecha_inicio_vigencia__gte=inicio)
        if fin:
            consulta_solapamiento &= Q(fecha_fin_vigencia__lte=fin)
        
        # 2. Comprueba si la nueva lista "inicia durante" una existente
        consulta_inicia_durante = Q(fecha_inicio_vigencia__lte=inicio)
        if fin:
             consulta_inicia_durante &= Q(fecha_fin_vigencia__gte=inicio)
        else:
            # Si la nueva lista no tiene fin, choca con cualquiera
            # que no haya terminado antes de que esta empiece.
             consulta_inicia_durante &= Q(fecha_fin_vigencia__gte=inicio) | Q(fecha_fin_vigencia__isnull=True)

        # 3. Comprueba si la nueva lista "termina durante" una existente
        consulta_termina_durante = Q(fecha_inicio_vigencia__isnull=False) # Solo aplica si la nueva tiene fin
        if fin:
            consulta_termina_durante = Q(fecha_inicio_vigencia__lte=fin) & \
                                       (Q(fecha_fin_vigencia__gte=fin) | Q(fecha_fin_vigencia__isnull=True))
        
        filtros_solapamiento = Q(consulta_solapamiento | consulta_inicia_durante | consulta_termina_durante)

        # Excluimos el objeto actual si estamos actualizando (PUT/PATCH)
        instancia_actual = self.instance
        query = ListaPrecio.objects.filter(filtros_competencia & filtros_solapamiento)
        
        if instancia_actual:
            query = query.exclude(pk=instancia_actual.pk) # No te compares contigo mismo

        if query.exists():
            lista_existente = query.first()
            raise serializers.ValidationError(
                f"Las fechas se solapan con una lista de precios existente: "
                f"'{lista_existente.nombre}' (ID: {lista_existente.id})"
            )

        return data
    
    
# --- AÑADE ESTA NUEVA CLASE ---
class ResultadoCalculoSerializer(serializers.Serializer):
    """
    Serializador para mostrar el resultado del cálculo de precios.
    No se basa en un modelo, solo define la estructura de la respuesta.
    """
    lista_precio_aplicada = serializers.CharField()
    precio_base = serializers.DecimalField(max_digits=10, decimal_places=2)
    precio_final = serializers.DecimalField(max_digits=10, decimal_places=2)
    cantidad = serializers.IntegerField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    reglas_aplicadas = serializers.ListField(child=serializers.CharField())
    autorizado_bajo_costo = serializers.BooleanField()


    