from django.db import models
from django.conf import settings

class LogAuditoria(models.Model):
    ACCIONES = [
        ('C', 'CREACIÓN'),
        ('M', 'MODIFICACIÓN'),
        ('E', 'ELIMINACIÓN'),
        ('L', 'LOGIN'),
        ('X', 'LOGOUT'),
        ('F', 'FALLO DE ACCESO'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    modulo = models.CharField(max_length=100)  # Ej: 'Recibos', 'Bienes'
    accion = models.CharField(max_length=1, choices=ACCIONES)
    descripcion = models.TextField()
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    
    # Metadatos para reconstruir la historia
    valor_anterior = models.JSONField(null=True, blank=True)
    valor_nuevo = models.JSONField(null=True, blank=True)
    objeto_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Registro de Auditoría"
        verbose_name_plural = "Bitácora de Auditoría"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp} - {self.usuario} - {self.modulo}"