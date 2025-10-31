from rest_framework import serializers
from django.db.models import Q
from datetime import date
from decimal import Decimal
from .models import (
    Empresa, Sucursal, LineaArticulo, GrupoArticulo, Articulo,
    ListaPrecio, PrecioArticulo, ReglaPrecio, CombinacionProducto
)

# --- Serializadores base ---

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = '__all__'


class SucursalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sucursal
        fields = '__all__'


class LineaArticuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineaArticulo
        fields = '__all__'


class GrupoArticuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrupoArticulo
        fields = '__all__'


class ArticuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Articulo
        fields = '__all__'


# --- Serializador para Lista de Precios ---
class ListaPrecioSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListaPrecio
        fields = [
            'id',
            'nombre',
            'empresa',
            'sucursal',
            'canal_venta',
            'fecha_inicio_vigencia',
            'fecha_fin_vigencia',
            'activa',
        ]

    def validate(self, data):
        """
        Validación personalizada para evitar solapamiento de vigencias.
        """
        inicio = data.get('fecha_inicio_vigencia')
        fin = data.get('fecha_fin_vigencia')

        filtros_competencia = Q(empresa=data.get('empresa')) & \
                              Q(sucursal=data.get('sucursal')) & \
                              Q(canal_venta=data.get('canal_venta')) & \
                              Q(activa=True)

        consulta_solapamiento = Q(fecha_inicio_vigencia__gte=inicio)
        if fin:
            consulta_solapamiento &= Q(fecha_fin_vigencia__lte=fin)

        consulta_inicia_durante = Q(fecha_inicio_vigencia__lte=inicio)
        if fin:
            consulta_inicia_durante &= Q(fecha_fin_vigencia__gte=inicio)
        else:
            consulta_inicia_durante &= Q(fecha_fin_vigencia__gte=inicio) | Q(fecha_fin_vigencia__isnull=True)

        consulta_termina_durante = Q(fecha_inicio_vigencia__isnull=False)
        if fin:
            consulta_termina_durante = Q(fecha_inicio_vigencia__lte=fin) & (
                Q(fecha_fin_vigencia__gte=fin) | Q(fecha_fin_vigencia__isnull=True)
            )

        filtros_solapamiento = Q(consulta_solapamiento | consulta_inicia_durante | consulta_termina_durante)
        instancia_actual = self.instance
        query = ListaPrecio.objects.filter(filtros_competencia & filtros_solapamiento)

        if instancia_actual:
            query = query.exclude(pk=instancia_actual.pk)

        if query.exists():
            lista_existente = query.first()
            raise serializers.ValidationError(
                f"Las fechas se solapan con una lista de precios existente: "
                f"'{lista_existente.nombre}' (ID: {lista_existente.id})"
            )

        return data


# --- Serializador para Combinación de Productos ---
class CombinacionProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CombinacionProducto
        fields = '__all__'


# --- Serializador para Precio de Artículo ---
class PrecioArticuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrecioArticulo
        fields = '__all__'


# --- Serializador para Reglas de Precio ---
class ReglaPrecioSerializer(serializers.ModelSerializer):
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

    class Meta:
        model = ReglaPrecio
        fields = [
            'id', 'lista_precio', 'nombre_regla', 'tipo_regla', 'valor_regla',
            'condicion', 'condicion_valor', 'prioridad', 'permite_venta_bajo_costo',
            'aplica_articulo', 'aplica_grupo', 'aplica_linea', 'aplica_combinacion'
        ]

    def validate(self, data):
        """
        Validación para evitar reglas duplicadas.
        """
        campos_unicos = [
            'lista_precio', 'tipo_regla', 'condicion', 'condicion_valor',
            'aplica_articulo', 'aplica_grupo', 'aplica_linea', 'aplica_combinacion'
        ]
        filtro_duplicados = {}
        for campo in campos_unicos:
            if campo in data:
                filtro_duplicados[campo] = data.get(campo)

        query = ReglaPrecio.objects.filter(**filtro_duplicados)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)

        if query.exists():
            regla_existente = query.first()
            raise serializers.ValidationError(
                f"Ya existe una regla idéntica con estos criterios: "
                f"'{regla_existente.nombre_regla}' (ID: {regla_existente.id})"
            )

        return data


# --- Serializador de resultado de cálculo ---
class ResultadoCalculoSerializer(serializers.Serializer):
    lista_precio_aplicada = serializers.CharField()
    precio_base = serializers.DecimalField(max_digits=10, decimal_places=2)
    precio_final = serializers.DecimalField(max_digits=10, decimal_places=2)
    cantidad = serializers.IntegerField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    reglas_aplicadas = serializers.ListField(child=serializers.CharField())
    autorizado_bajo_costo = serializers.BooleanField()
