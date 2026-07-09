from django.conf import settings
from django.db import models
from django.utils import timezone


class SelloDorado(models.Model):
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('aprobado', 'Aprobado'),
        ('asignado', 'Asignado'),
        ('protocolizado', 'Protocolizado'),
        ('rechazado', 'Rechazado'),
    ]

    codigo_sello = models.CharField(max_length=30, unique=True, blank=True)
    nombre = models.CharField(max_length=200)
    region = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    observaciones = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sellos_creados'
    )

    class Meta:
        verbose_name = 'Sello Dorado'
        verbose_name_plural = 'Sellos Dorados'
        ordering = ['-fecha_creacion']

    def save(self, *args, **kwargs):
        if not self.codigo_sello:
            anio = timezone.now().year
            prefijo = f'SD-{anio}'
            ultimo = SelloDorado.objects.filter(codigo_sello__startswith=prefijo).order_by('-codigo_sello').first()
            if ultimo:
                try:
                    numero = int(ultimo.codigo_sello.split('-')[-1])
                    nuevo_numero = numero + 1
                except (ValueError, IndexError):
                    nuevo_numero = 1
            else:
                nuevo_numero = 1
            self.codigo_sello = f'{prefijo}-{nuevo_numero:04d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.codigo_sello


class HistorialSello(models.Model):
    sello = models.ForeignKey(
        SelloDorado,
        on_delete=models.CASCADE,
        related_name='historial'
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    accion = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Historial de Sello'
        verbose_name_plural = 'Historiales de Sellos'
