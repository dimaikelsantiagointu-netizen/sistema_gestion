from django.db import models
from apps.beneficiarios.models import Beneficiario
from django.contrib.auth import get_user_model

Usuario = get_user_model()

class Contrato(models.Model):
    ESTADOS = [
        ('borrador', 'Borrador'),
        ('revision', 'En Revisión'),
        ('aprobado', 'Aprobado'),
        ('firmado', 'Firmado'),
        ('anulado', 'Anulado'),
    ]

    # Relación con beneficiarios existentes
    beneficiario = models.ForeignKey(Beneficiario, on_delete=models.CASCADE, related_name='contratos')
    
    # Datos básicos
    codigo_contrato = models.CharField(max_length=50, unique=True, verbose_name="Nro. Contrato")
    tipo_contrato = models.CharField(max_length=100, help_text="Ej: Adjudicación de Terreno")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='borrador')
    
    # Contenido (Preparado para plantillas futuras)
    cuerpo_contrato = models.TextField(help_text="Contenido principal y cláusulas")
    version = models.PositiveIntegerField(default=1)
    
    # Flujo de trabajo
    creado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='contratos_creados')
    aprobado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='contratos_aprobados')

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.codigo_contrato} - {self.beneficiario.nombre_completo}"