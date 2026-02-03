from django.db import models
import os
from django.utils import timezone
from django.conf import settings  # <--- CAMBIO 1: Importar settings

class Beneficiario(models.Model):
    CEDULA = 'V'
    RIF = 'J'
    EXTRANJERO = 'E'
    GUBERNAMENTAL = 'G'
    
    TIPO_DOC_CHOICES = [
        (CEDULA, 'Cédula (V)'),
        (RIF, 'Jurídico (J)'),
        (EXTRANJERO, 'Extranjero (E)'),
        (GUBERNAMENTAL, 'Gubernamental (G)'),
    ]

    tipo_documento = models.CharField(max_length=1, choices=TIPO_DOC_CHOICES, default=CEDULA)
    documento_identidad = models.CharField(max_length=20, unique=True, verbose_name="Cédula o RIF")
    nombre_completo = models.CharField(max_length=255)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    
    def save(self, *args, **kwargs):
        self.nombre_completo = self.nombre_completo.upper()
        self.documento_identidad = self.documento_identidad.upper().strip()
        super(Beneficiario, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo_documento}-{self.documento_identidad} | {self.nombre_completo}"

def ruta_expediente_digital(instance, filename):
    return os.path.join('expedientes', instance.beneficiario.documento_identidad, filename)

class DocumentoExpediente(models.Model):
    beneficiario = models.ForeignKey(Beneficiario, on_delete=models.CASCADE, related_name='documentos')
    archivo = models.FileField(upload_to=ruta_expediente_digital)
    nombre_documento = models.CharField(max_length=100, help_text="Ej: Copia de CI, RIF Vigente, etc.")
    fecha_subida = models.DateTimeField(auto_now_add=True)

class Visita(models.Model):
    MOTIVO_CHOICES = [
        ('ASESORIA', 'Asesoría Jurídica'),
        ('RECAUDOS', 'Entrega de Recaudos'),
        ('RETIRO', 'Retiro de Documentos'),
        ('SOLICITUD', 'Nueva Solicitud'),
        ('OTRO', 'Otro / Información General'),
    ]

    beneficiario = models.ForeignKey(
        'Beneficiario', 
        on_delete=models.CASCADE, 
        related_name='visitas'
    )
    
    fecha_registro = models.DateTimeField(default=timezone.now)
    motivo = models.CharField(max_length=20, choices=MOTIVO_CHOICES)
    descripcion = models.TextField(verbose_name="Observaciones de la visita")
    
    # CAMBIO 2: Usar settings.AUTH_USER_MODEL en lugar de User
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True  # Recomendado para que el Admin no te obligue a llenarlo manualmente
    )

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = "Visita"
        verbose_name_plural = "Visitas"

    def __str__(self):
        return f"{self.beneficiario.nombre_completo} - {self.fecha_registro.date()}"