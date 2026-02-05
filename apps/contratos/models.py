from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

Usuario = get_user_model()

class Contrato(models.Model):
    # --- Opciones del Sistema ---
    ESTADOS = [
        ('espera', 'En espera'),
        ('aprobado', 'Validado'),
    ]

    TIPOS_CONTRATO = [
        ('arrendamiento', 'Arrendamiento'),
        ('venta', 'Venta'),
        ('comodato', 'Comodato (Institucional)'),
        ('alianza', 'Alianza Comercial'),
        ('titulo_tierra', 'Título de Tierra Urbana'),
    ]
    
    archivo_adjunto = models.FileField(upload_to='contratos/adjuntos/', null=True, blank=True)
    
    # --- Beneficiarios ---
    beneficiarios = models.ManyToManyField(
        'beneficiarios.Beneficiario', 
        related_name='contratos',
        verbose_name="Beneficiarios"
    )
    
    # --- Identificación ---
    codigo_contrato = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Nro. Contrato",
        blank=True
    )
    
    tipo_contrato = models.CharField(
        max_length=50, 
        choices=TIPOS_CONTRATO, 
        default='arrendamiento',
        verbose_name="Tipo de Instrumento Legal"
    )
    
    # --- Datos Técnicos ---
    codigo_catastral = models.CharField(max_length=100, verbose_name="Código Catastral", null=True, blank=True)
    superficie_num = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Superficie (m2)", null=True, blank=True)
    superficie_letras = models.CharField(max_length=255, verbose_name="Superficie en Letras", null=True, blank=True)
    direccion_inmueble = models.TextField(verbose_name="Dirección según Plano", null=True, blank=True)
    
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
    
    # --- Trazabilidad ---
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='espera')
    
    # Observaciones 
    observaciones = models.TextField(verbose_name="Observaciones de Estado", blank=True, null=True)
    
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

    def save(self, *args, **kwargs):
        es_nuevo = self.pk is None
        
        if not self.codigo_contrato:
            anio = timezone.now().year
            prefijo = f"CT-{anio}"
            ultimo = Contrato.objects.filter(
                codigo_contrato__startswith=prefijo
            ).order_by('-codigo_contrato').first()
            
            if ultimo:
                try:
                    partes = ultimo.codigo_contrato.split('-')
                    ultimo_numero = int(partes[-1])
                    nuevo_numero = ultimo_numero + 1
                except (ValueError, IndexError):
                    nuevo_numero = 1
            else:
                nuevo_numero = 1
            
            self.codigo_contrato = f"{prefijo}-{nuevo_numero:04d}"
            
        super().save(*args, **kwargs)

        HistorialContrato.objects.create(
            contrato=self,
            estado=self.estado,
            observacion_tecnica=self.observaciones,
            usuario=self.creado_por if es_nuevo else self.aprobado_por
        )

    def __str__(self):
        return f"{self.codigo_contrato} - {self.get_tipo_contrato_display()}"


class HistorialContrato(models.Model):
    contrato = models.ForeignKey(
        'Contrato',
        on_delete=models.CASCADE, 
        related_name='historial_registros'
    )
    estado = models.CharField(max_length=20)
    accion = models.CharField(max_length=100, help_text="Ej: Modificación de monto, Cambio de fecha", null=True, blank=True)
    datos_cambiados = models.JSONField(null=True, blank=True, help_text="Diccionario con los cambios realizados")
    observacion_tecnica = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True
    )

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = "Historial de Contrato"
        verbose_name_plural = "Historiales de Contratos"

    def __str__(self):
        return f"Historial {self.contrato.codigo_contrato} - {self.estado} ({self.fecha_registro.strftime('%d/%m/%Y')})"


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