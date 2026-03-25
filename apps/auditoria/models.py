from django.db import models
from django.conf import settings
from django.core.exceptions import PermissionDenied

class LogAuditoria(models.Model):
    ACCIONES = [
        ('C', 'CREACIÓN'),
        ('M', 'MODIFICACIÓN'),
        ('E', 'ELIMINACIÓN'),
        ('L', 'INICIO DE SESIÓN'),
        ('S', 'CIERRE DE SESIÓN'),  # Cambiado X por S para consistencia
        ('F', 'ACCESO FALLIDO'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Responsable"
    )
    modulo = models.CharField(max_length=100, verbose_name="Módulo")
    accion = models.CharField(max_length=1, choices=ACCIONES, verbose_name="Acción")
    descripcion = models.TextField(verbose_name="Descripción del Evento")
    direccion_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP de Origen")
    
    # Metadatos para reconstruir la historia
    valor_anterior = models.JSONField(null=True, blank=True, verbose_name="Datos Anteriores")
    valor_nuevo = models.JSONField(null=True, blank=True, verbose_name="Datos Nuevos")
    
    # Cambiado a CharField para soportar IDs numéricos y UUIDs
    objeto_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="ID del Objeto")

    class Meta:
        verbose_name = "Registro de Auditoría"
        verbose_name_plural = "Bitácora de Auditoría"
        ordering = ['-timestamp']
        # Indexar por timestamp y usuario mejora MUCHO el rendimiento de los reportes
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['usuario', 'modulo']),
        ]

    def __str__(self):
        return f"{self.timestamp} - {self.usuario} - {self.modulo} ({self.get_accion_display()})"

    def save(self, *args, **kwargs):
        # PROTECCIÓN DE INMUTABILIDAD:
        # Si el objeto ya tiene un ID, significa que se está intentando editar.
        if self.pk:
            raise PermissionDenied("Los registros de auditoría son inmutables y no pueden ser modificados.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Opcional: Impedir borrado accidental desde el código
        raise PermissionDenied("Los registros de auditoría no pueden ser eliminados.")