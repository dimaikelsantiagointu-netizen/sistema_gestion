from django.db import models
from .constants import CATEGORY_CHOICES, CATEGORY_CHOICES_MAP


class Recibo(models.Model):
    # 1. CAMPOS DE CONTROL Y SEGUIMIENTO
    
    # Número único del recibo. Se usa para búsquedas exactas y ordenamiento.
    numero_recibo = models.IntegerField(
        unique=True, 
        null=True, 
        blank=True, 
        db_index=True 
    ) 
    
    # Fecha y hora de creación del registro en la DB (automático, no editable)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    # Indicador de anulación. Se usa como filtro principal en el dashboard (anulado=False).
    anulado = models.BooleanField(
        default=False, 
        db_index=True # Absolutamente necesario para el filtro del dashboard
    ) 
    
    # Fecha de anulación. Solo se llena si 'anulado' es True.
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    
    # 2. DATOS DEL CLIENTE E IDENTIFICACIÓN

    # Estado o región del cliente
    estado = models.CharField(
        max_length=100, 
        db_index=True 
    )
    
    # Nombre completo del cliente.
    nombre = models.CharField(max_length=255)
    
    # RIF o Cédula de Identidad
    rif_cedula_identidad = models.CharField(
        max_length=50, 
        db_index=True 
    )
    
    # Dirección física del inmueble asociado.
    direccion_inmueble = models.TextField()
    
    # Ente/organización que liquida o realiza el pago.
    ente_liquidado = models.CharField(max_length=255)

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
    # Monto fijo o variable de gastos administrativos.
    gastos_administrativos = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Tasa de cambio del día
    tasa_dia = models.DecimalField(max_digits=10, decimal_places=4) 
    
    # Monto total en Bolívares
    total_monto_bs = models.DecimalField(max_digits=15, decimal_places=2) 
    
    # 5. CONCILIACIÓN Y DETALLES DE PAGO
    
    # Número de referencia de la transferencia/pago.
    numero_transferencia = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        db_index=True 
    )
    
    # Indicador de si el recibo ha sido conciliado.
    conciliado = models.BooleanField(default=False)
    
    # Fecha de la transacción/operación. Es clave para los reportes por periodo.
    fecha = models.DateField(db_index=True) 
    
    # Descripción detallada del pago.
    concepto = models.TextField()

    # 6. CONFIGURACIÓN DEL MODELO
    class Meta:
        db_table = 'recibos_pago'
        
        indexes = [
            # Índice compuesto: Acelera el ordenamiento y filtrado principal del dashboard
            models.Index(fields=['anulado', '-fecha', '-numero_recibo']),
            
            # Índice simple para la búsqueda por número de recibo
        ]

        # Configuración de los nombres de los objetos
        verbose_name = "Recibo de Pago"
        verbose_name_plural = "Recibos de Pago"

    # Método para representación textual del objeto
    def __str__(self):
        return f"Recibo N°{self.numero_recibo or self.pk} ({self.nombre})"

    # Método de utilidad para verificar si alguna categoría es True
    def tiene_categorias(self):
        """Verifica si al menos una categoría está marcada como True."""
        for i in range(1, 11):
            if getattr(self, f'categoria{i}'):
                return True
        return False