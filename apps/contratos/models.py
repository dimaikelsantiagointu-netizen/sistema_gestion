from django.db import models
from apps.beneficiarios.models import Beneficiario
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

Usuario = get_user_model()

from django.db import models
from datetime import datetime

class Contrato(models.Model):
    ESTADOS = [
        ('borrador', 'Borrador'),
        ('revision', 'En Revisión'),
        ('aprobado', 'Aprobado'),
        ('firmado', 'Firmado'),
        ('anulado', 'Anulado'),
    ]

    PRIORIDAD = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]

    # --- Beneficiarios (Muchos a Muchos) ---
    beneficiarios = models.ManyToManyField(
        'beneficiarios.Beneficiario', 
        related_name='contratos',
        verbose_name="Beneficiarios"
    )
    
    # --- Identificación (Código automático CT-AÑO-CORRELATIVO) ---
    codigo_contrato = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Nro. Contrato",
        blank=True
    )
    tipo_contrato = models.CharField(max_length=100, default="VENTA PURA Y SIMPLE")
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD, default='media')
    
    # Datos Técnicos
    codigo_catastral = models.CharField(max_length=100, verbose_name="Código Catastral", null=True, blank=True)
    superficie_num = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Superficie (m2)", null=True)
    superficie_letras = models.CharField(max_length=255, verbose_name="Superficie en Letras", null=True)
    direccion_inmueble = models.TextField(verbose_name="Dirección según Plano", null=True)
    
    # Linderos específicos
    lindero_norte = models.CharField(max_length=255, null=True, blank=True)
    lindero_sur = models.CharField(max_length=255, null=True, blank=True)
    lindero_este = models.CharField(max_length=255, null=True, blank=True)
    lindero_oeste = models.CharField(max_length=255, null=True, blank=True)
    
    # Archivo
    archivo_escaneado = models.FileField(
        upload_to='contratos/expedientes/%Y/%m/', 
        null=True, 
        blank=True,
        verbose_name="Contrato Digitalizado (PDF/Imagen)"
    )
    
    # Trazabilidad
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='borrador')
    
    # Texto Legal
    cuerpo_contrato = models.TextField(help_text="Contenido principal generado automáticamente", blank=True)
    version = models.PositiveIntegerField(default=1)
    
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='contratos_creados'
    )
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='contratos_aprobados'
    )

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"

    # --- LÓGICA DE AUTO-GENERACIÓN DE CÓDIGO MEJORADA ---
    def save(self, *args, **kwargs):
        if not self.codigo_contrato:
            # 1. Obtiene el año actual desde el servidor para evitar desfases
            anio = timezone.now().year
            prefijo = f"CT-{anio}"
            
            # 2. Busca el último contrato que empiece con el prefijo del año actual
            # Usamos __startswith para mayor precisión en la consulta
            ultimo = Contrato.objects.filter(
                codigo_contrato__startswith=prefijo
            ).order_by('-codigo_contrato').first()
            
            if ultimo:
                try:
                    # Extrae el número después del último guion
                    partes = ultimo.codigo_contrato.split('-')
                    ultimo_numero = int(partes[-1])
                    nuevo_numero = ultimo_numero + 1
                except (ValueError, IndexError):
                    nuevo_numero = 1
            else:
                # Primer contrato del año
                nuevo_numero = 1
            
            # 3. Formato final: CT-2026-001 (3 dígitos para el correlativo)
            self.codigo_contrato = f"{prefijo}-{nuevo_numero:04d}"
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo_contrato}"

class ConfiguracionInstitucional(models.Model):
    nombre_gerente = models.CharField(max_length=200, default="ROSMEL DANIEL FLORES ÑAÑEZ")
    cedula_gerente = models.CharField(max_length=20, default="V-13.617.999")
    providencia_nro = models.CharField(max_length=100, default="020-024")
    fecha_providencia = models.DateField(null=True, blank=True)
    gaceta_nro = models.CharField(max_length=50, default="43.063")
    monto_m2 = models.DecimalField(max_digits=10, decimal_places=4, default=0.001)

    class Meta:
        verbose_name = "Configuración INTU"
        verbose_name_plural = "Configuración Institucional"

    def __str__(self):
        return "Configuración Actual del Sistema"

class HistorialContrato(models.Model):
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='historial')
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    accion = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']