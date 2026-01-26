from django.db import models
import os

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
    # Eliminamos uppercase=True porque no existe en Django core
    nombre_completo = models.CharField(max_length=255)
    
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    
    def save(self, *args, **kwargs):
        # Forzamos mayúsculas antes de guardar en la DB
        self.nombre_completo = self.nombre_completo.upper()
        self.documento_identidad = self.documento_identidad.upper().strip()
        super(Beneficiario, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo_documento}-{self.documento_identidad} | {self.nombre_completo}"

def ruta_expediente_digital(instance, filename):
    # Limpiamos el nombre del archivo para evitar problemas de ruta
    # Los archivos se guardan en: media/expedientes/[cedula_rif]/[nombre_archivo]
    return os.path.join('expedientes', instance.beneficiario.documento_identidad, filename)

class DocumentoExpediente(models.Model):
    beneficiario = models.ForeignKey(Beneficiario, on_delete=models.CASCADE, related_name='documentos')
    archivo = models.FileField(upload_to=ruta_expediente_digital)
    nombre_documento = models.CharField(max_length=100, help_text="Ej: Copia de CI, RIF Vigente, etc.")
    # Añadimos fecha por utilidad (opcional pero recomendado para el expediente)
    fecha_subida = models.DateTimeField(auto_now_add=True)