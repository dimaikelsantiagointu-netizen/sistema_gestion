from django.db import models
from django.contrib.auth.models import User
# Usamos el modelo User de Django para la gestión de usuarios/autenticación.

class Receipt(models.Model):
    """
    Modelo que representa un registro de recibo de pago.
    Contiene la información del pago, el cliente y la referencia al usuario que lo creó.
    """
    # 1. Información Principal del Recibo
    receipt_number = models.CharField(max_length=50, unique=True, verbose_name="Nº Recibo")
    # El estado permite marcar si un recibo fue anulado, pagado, etc.
    status = models.CharField(max_length=50, default='PENDIENTE', verbose_name="Estado")
    
    # 2. Información del Cliente
    client_name = models.CharField(max_length=255, verbose_name="Nombre Cliente")
    client_id = models.CharField(max_length=50, verbose_name="Cédula/RIF")
    client_address = models.TextField(verbose_name="Dirección")

    # 3. Información Financiera/Transacción
    # DecimalField es crucial para datos monetarios para evitar errores de coma flotante.
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Monto (Bs.)")
    transaction_number = models.CharField(max_length=100, verbose_name="Nº Transferencia")
    payment_date = models.DateField(verbose_name="Fecha de Pago")
    concept = models.TextField(verbose_name="Concepto")

    # 4. Categorías / Descripción de Regularización (10 campos booleanos)
    # Estos campos almacenan las marcas 'X' del Excel para la generación del PDF.
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
    
    # 5. Información de Auditoría
    # Relación con el usuario de Django que creó el recibo. 
    # SET_NULL: si el usuario es borrado, el campo se pone a NULL, preservando el recibo.
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Creado por")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha Creación")
    
    class Meta:
        # Nombre del modelo en el panel de administración
        verbose_name = "Recibo"
        verbose_name_plural = "Recibos"
        # Ordenar por fecha de creación de forma descendente por defecto
        ordering = ['-created_at']

    def __str__(self):
        """Devuelve una representación legible del objeto Recibo."""
        return f"Recibo {self.receipt_number} - {self.client_name}"

    def get_categories_dict(self):
        """Método auxiliar para retornar las categorías como un diccionario."""
        return {
            f'categoria{i}': getattr(self, f'categoria{i}') for i in range(1, 11)
        }