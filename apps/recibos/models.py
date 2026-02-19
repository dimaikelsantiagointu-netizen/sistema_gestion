import io
from django.db import models
from .constants import CATEGORY_CHOICES, CATEGORY_CHOICES_MAP
from django.conf import settings

class Recibo(models.Model):
    # 1. CAMPOS DE CONTROL Y SEGUIMIENTO
    
    # Número único del recibo.
    numero_recibo = models.IntegerField(
        unique=True, 
        null=True, 
        blank=True, 
        db_index=True 
    ) 
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,  
        null=True,                 
        blank=True,              
        related_name='recibos_creados',
        verbose_name="Creado por",
        db_index=True
    )

    anulado = models.BooleanField(
        default=False, 
        db_index=True 
    ) 
    
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    
    # 2. DATOS DEL CLIENTE E IDENTIFICACIÓN

    # Estado o región del cliente. 
    estado = models.CharField(
        max_length=150, 
        db_index=True 
    )
    
    # Nombre completo del cliente.
    nombre = models.CharField(
        max_length=500,
    )
    
    # RIF o Cédula de Identidad.
    rif_cedula_identidad = models.CharField(
        max_length=100, 
        db_index=True 
    )
    
    # Dirección física del inmueble asociado.
    direccion_inmueble = models.TextField()
    
    # Ente/organización que liquida o realiza el pago.
    ente_liquidado = models.CharField(
        max_length=500,
    )

    # 3. CATEGORÍAS (Booleanos)
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

    # 4. MONTOS Y FINANZAS
    gastos_administrativos = models.DecimalField(max_digits=19, decimal_places=2)
    
    tasa_dia = models.DecimalField(max_digits=19, decimal_places=4) 
    
    # total_monto_bs
    total_monto_bs = models.DecimalField(
        max_digits=19, 
        decimal_places=2,
        help_text="Soporta montos extremadamente altos sin desbordamiento."
    ) 
    
    # 5. CONCILIACIÓN Y DETALLES DE PAGO
    
    # Número de referencia de la transferencia/pago.
    numero_transferencia = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        unique=True,
        db_index=True 
    )
    
    conciliado = models.BooleanField(default=False)
    
    fecha = models.DateField(db_index=True) 
    
    # Descripción detallada del pago.
    concepto = models.TextField()

    # 6. CONFIGURACIÓN DEL MODELO
    class Meta:
        db_table = 'recibos_pago'
        indexes = [
            models.Index(fields=['anulado', '-fecha', '-numero_recibo']),
        ]
        verbose_name = "Recibo de Pago"
        verbose_name_plural = "Recibos de Pago"

    def __str__(self):
        return f"Recibo N°{self.numero_recibo or self.pk} ({self.nombre})"

    def tiene_categorias(self):
        """Verifica si al menos una categoría está marcada como True."""
        for i in range(1, 11):
            if getattr(self, f'categoria{i}'):
                return True
        return False