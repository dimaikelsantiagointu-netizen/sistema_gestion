# En recibos/models.py (Estructura Completa Sugerida)
from django.db import models

class Recibo(models.Model):
    # Campos automáticos/de control
    numero_recibo = models.IntegerField(unique=True, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    anulado = models.BooleanField(default=False) 

    # 1. Datos del Cliente
    estado = models.CharField(max_length=100)
    nombre = models.CharField(max_length=255)
    rif_cedula_identidad = models.CharField(max_length=50)
    direccion_inmueble = models.TextField()
    ente_liquidado = models.CharField(max_length=255)

    # 2. Categorías (Booleanos)
    categoria1 = models.BooleanField(default=False)
    categoria2 = models.BooleanField(default=False)
    categoria3 = models.BooleanField(default=False)
    categoria4 = models.BooleanField(default=False)
    categoria5 = models.BooleanField(default=False)
    categoria6 = models.BooleanField(default=False)
    categoria7 = models.BooleanField(default=False)
    categoria8 = models.BooleanField(default=False)
    categoria9 = models.BooleanField(default=False)
    categoria10 = models.BooleanField(default=False)

    # 3. Montos
    gastos_administrativos = models.DecimalField(max_digits=10, decimal_places=2)
    tasa_dia = models.DecimalField(max_digits=10, decimal_places=4) # Mayor precisión para la tasa
    total_monto_bs = models.DecimalField(max_digits=12, decimal_places=2)

    # 4. Conciliación
    numero_transferencia = models.CharField(max_length=100, blank=True, null=True)
    conciliado = models.BooleanField(default=False)
    fecha = models.DateField() # La fecha de la transacción
    concepto = models.TextField()

    class Meta:
        db_table = 'recibos_pago'
        # Puedes añadir un índice para optimizar la búsqueda del último recibo
        # indexes = [models.Index(fields=['-numero_recibo'])]