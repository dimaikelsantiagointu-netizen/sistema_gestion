from django.db import models
# Importamos los modelos de la app territorio
from apps.territorio.models import Estado, Municipio, Parroquia, Comuna, UnidadAdscrita

class Personal(models.Model):
    cedula = models.CharField(max_length=20, unique=True)
    nombres = models.CharField(max_length=150)
    apellidos = models.CharField(max_length=150)
    fecha_ingreso = models.DateField()
    cargo = models.CharField(max_length=100)
    
    unidad_adscrita = models.ForeignKey(
        UnidadAdscrita, 
        on_delete=models.PROTECT, 
        related_name='personal_asignado'
    )
    
    # --- NUEVOS CAMPOS DE TERRITORIO ---
    estado = models.ForeignKey(
        Estado, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="Estado de Residencia"
    )
    municipio = models.ForeignKey(
        Municipio, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="Municipio"
    )
    parroquia = models.ForeignKey(
        Parroquia, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name="Parroquia"
    )
    comuna = models.ForeignKey(
        Comuna, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Comuna (Opcional)"
    )
    
    direccion_exacta = models.TextField(
        max_length=500, 
        blank=True, 
        null=True,
        verbose_name="Dirección Detallada"
    )
    # ----------------------------------

    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Personal"
        verbose_name_plural = "Personal Institucional"

    def __str__(self):
        return f"{self.cedula} - {self.nombres} {self.apellidos}"

    def estado_expediente(self):
        try:
            conteo = self.expediente_personal.count()
        except Exception:
            conteo = 0
        
        if conteo == 0:
            return {'color': 'bg-red-500', 'texto': 'Vacío', 'bg_soft': 'bg-red-50', 'text_color': 'text-red-700'}
        elif conteo < 4:
            return {'color': 'bg-amber-400', 'texto': f'Incompleto ({conteo}/4)', 'bg_soft': 'bg-amber-50', 'text_color': 'text-amber-700'}
        else:
            return {'color': 'bg-emerald-500', 'texto': 'Completo', 'bg_soft': 'bg-emerald-50', 'text_color': 'text-emerald-700'}

class DocumentoPersonal(models.Model):
    personal = models.ForeignKey(
        Personal, 
        on_delete=models.CASCADE, 
        related_name='expediente_personal'
    )
    archivo = models.FileField(upload_to='personal/expedientes/')
    nombre_documento = models.CharField(max_length=255)
    
    CATEGORIAS = [
        ('ID', 'Documento de Identidad'),
        ('CV', 'Síntesis Curricular (CV)'),
        ('ACAD', 'Títulos Académicos y Certificaciones'),
        ('CONT', 'Actas de Nombramiento o Contratos'),
        ('OTRO', 'Otros Soportes'),
    ]
    
    categoria = models.CharField(max_length=100, choices=CATEGORIAS, default='OTRO')
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre_documento} - {self.personal.apellidos}"

    class Meta:
        verbose_name = "Documento de Personal"
        verbose_name_plural = "Documentos de Personal"