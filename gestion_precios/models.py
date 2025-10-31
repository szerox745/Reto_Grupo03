from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

# --- Modelos Base ---
# Estos son los modelos fundamentales de los que dependen los demás.

class Empresa(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

class Sucursal(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='sucursales')
    nombre = models.CharField(max_length=100)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('empresa', 'nombre')

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})"

class LineaArticulo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.nombre

class GrupoArticulo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class Articulo(models.Model):
    linea = models.ForeignKey(LineaArticulo, on_delete=models.PROTECT)
    grupo = models.ForeignKey(GrupoArticulo, on_delete=models.PROTECT)
    sku = models.CharField(max_length=50, unique=True, help_text="Stock Keeping Unit o Código de Artículo único")
    nombre = models.CharField(max_length=200)
    ultimo_costo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.nombre} ({self.sku})"
    

# --- Modelos Centrales (Gestión de Precios) ---
# El corazón de la lógica de negocio.

class ListaPrecio(models.Model):
    CANAL_VENTA_CHOICES = [
        ('TODOS', 'Todos los Canales'),
        ('ECOMMERCE', 'E-commerce'),
        ('TIENDA', 'Tienda Física'),
    ]
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, null=True, blank=True, help_text="Si es nulo, aplica a toda la empresa.")
    nombre = models.CharField(max_length=100)
    canal_venta = models.CharField(max_length=20, choices=CANAL_VENTA_CHOICES, default='TODOS')
    fecha_inicio_vigencia = models.DateField()
    fecha_fin_vigencia = models.DateField(null=True, blank=True, help_text="Si es nulo, no tiene fecha de fin.")
    activa = models.BooleanField(default=True, help_text="Desmarcar para desactivar esta lista de precios.")

    def __str__(self):
        if self.sucursal:
            return f"{self.nombre} ({self.sucursal.nombre})"
        return f"{self.nombre} ({self.empresa.nombre})"
    
class CombinacionProducto(models.Model):
    """
    Define una agrupación de productos para aplicar reglas de combinación.
    Ej: "Lleva Producto A + Producto B y obtén 10%".
    """
    lista_precio = models.ForeignKey(ListaPrecio, on_delete=models.CASCADE, related_name='combinaciones')
    nombre = models.CharField(max_length=150)
    articulos = models.ManyToManyField(Articulo, related_name='combinaciones', help_text="Artículos que forman parte de esta combinación.")

    def __str__(self):
        return f"{self.nombre} ({self.lista_precio.nombre})"
    
    









    
class PrecioArticulo(models.Model):
    lista_precio = models.ForeignKey(ListaPrecio, on_delete=models.CASCADE, related_name='precios')
    articulo = models.ForeignKey(Articulo, on_delete=models.CASCADE, related_name='precios')
    precio_base = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])

    class Meta:
        unique_together = ('lista_precio', 'articulo')

    def __str__(self):
        return f"{self.articulo.nombre} - {self.lista_precio.nombre}: S/ {self.precio_base}"
    

class ReglaPrecio(models.Model):
    TIPO_REGLA_CHOICES = [
        ('PORCENTAJE', 'Porcentaje de Descuento'),
        ('MONTO_FIJO', 'Monto Fijo de Descuento'),
    ]
    CONDICION_CHOICES = [
        ('CANTIDAD_MINIMA', 'Cantidad Mínima de Unidades'),
        ('MONTO_MINIMO', 'Monto Mínimo de Pedido'),
    ]

    lista_precio = models.ForeignKey(ListaPrecio, on_delete=models.CASCADE, related_name='reglas')
    nombre_regla = models.CharField(max_length=150)
    tipo_regla = models.CharField(max_length=20, choices=TIPO_REGLA_CHOICES)
    valor_regla = models.DecimalField(max_digits=10, decimal_places=2, help_text="El valor del descuento (ej. 10 para 10% o 5 para S/ 5.00)")
    condicion = models.CharField(max_length=20, choices=CONDICION_CHOICES)
    condicion_valor = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor a comparar (ej. 3 para 3 unidades, 100 para S/ 100.00)")
    aplica_articulo = models.ForeignKey(
        Articulo, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        help_text="Si se define, esta regla solo aplica a este artículo."
    )
    aplica_grupo = models.ForeignKey(
        GrupoArticulo, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        help_text="Si se define, esta regla aplica a cualquier artículo de este grupo."
    )
    aplica_linea = models.ForeignKey(
        LineaArticulo, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        help_text="Si se define, esta regla aplica a cualquier artículo de esta línea."
    )
    aplica_combinacion = models.ForeignKey(
        CombinacionProducto, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        help_text="Si se define, esta regla aplica si la combinación de productos está presente."
    )
    prioridad = models.IntegerField(default=10, help_text="Menor número se aplica primero.")
    permite_venta_bajo_costo = models.BooleanField(default=False, help_text="Si se marca, esta regla puede hacer que el precio final sea inferior al costo del artículo.")


    class Meta:
        ordering = ['prioridad']

    def __str__(self):
        return f"{self.nombre_regla} ({self.lista_precio.nombre})"

