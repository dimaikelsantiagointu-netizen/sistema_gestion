from django.db import models
import os
from django.utils import timezone
from django.conf import settings 
from apps.territorio.models import Estado, Municipio, Parroquia, Ciudad, Comuna

# ==============================================================================
# SECCIÓN 1: MAESTRO DE BENEFICIARIOS (CIUDADANOS)
# ==============================================================================

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

    GENERO_CHOICES = [
        ('M', 'MASCULINO'),
        ('F', 'FEMENINO'),
    ]

    # --- Identificación ---
    tipo_documento = models.CharField(max_length=1, choices=TIPO_DOC_CHOICES, default=CEDULA)
    documento_identidad = models.CharField(max_length=20, unique=True, verbose_name="Cédula o RIF")
    nombre_completo = models.CharField(max_length=255)
    
    # NUEVO: Fecha de Nacimiento (Ubicado en Identidad)
    fecha_nacimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Nacimiento")
    
    # --- Perfil Social ---
    genero = models.CharField(max_length=1, choices=GENERO_CHOICES, verbose_name="Género")
    discapacidad = models.BooleanField(default=False, verbose_name="¿Posee alguna discapacidad?")
    
    # --- Contacto ---
    telefono = models.CharField(max_length=20, blank=True, null=True)
    # Correo electrónico actualizado como opcional
    email = models.EmailField(max_length=255, blank=True, null=True, verbose_name="Correo Electrónico")
    
    # --- Ubicación Territorial ---
    estado = models.ForeignKey(Estado, on_delete=models.PROTECT, related_name='beneficiarios')
    municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT, related_name='beneficiarios')
    parroquia = models.ForeignKey(Parroquia, on_delete=models.PROTECT, related_name='beneficiarios')
    ciudad = models.ForeignKey(Ciudad, on_delete=models.PROTECT, null=True, blank=True, related_name='beneficiarios')
    comuna = models.ForeignKey(Comuna, on_delete=models.PROTECT, null=True, blank=True, related_name='beneficiarios')
    direccion_especifica = models.TextField(verbose_name="Dirección Específica")

    # --- Auditoría y Filtros ---
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Registro")

    def save(self, *args, **kwargs):
        """Normalización de datos en mayúsculas"""
        if self.nombre_completo:
            self.nombre_completo = self.nombre_completo.upper()
        if self.documento_identidad:
            self.documento_identidad = self.documento_identidad.upper().strip()
        if self.direccion_especifica:
            self.direccion_especifica = self.direccion_especifica.upper()
        
        # El email no suele normalizarse a mayúsculas por estándar, 
        # pero si lo deseas, puedes añadir self.email = self.email.lower()
        
        super(Beneficiario, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo_documento}-{self.documento_identidad} | {self.nombre_completo}"


# ==============================================================================
# SECCIÓN 2: GESTIÓN DE ATENCIÓN Y VISITAS
# ==============================================================================

class Visita(models.Model):
    MOTIVO_CHOICES = [
        ('ASESORIA', 'Asesoría'),
        ('RECAUDOS', 'Entrega de Recaudos'),
        ('RETIRO', 'Retiros de Documentos'),
        ('SOLICITUD', 'Nueva Solicitud'),
        ('REG_COMERCIAL', 'Regularización Comercial'),
        ('CTU', 'Registro O Actualización de CTU'),
        ('REG_TIERRAS', 'Regularización de Tierras o Vivienda'),
        ('TECNICO', 'Servicios Técnicos'),
        ('OTRO', 'Otros'),
    ]

    beneficiario = models.ForeignKey(
        'Beneficiario', 
        on_delete=models.CASCADE, 
        related_name='visitas'
    )
    
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    fecha_registro = models.DateTimeField(default=timezone.now)
    motivo = models.CharField(max_length=20, choices=MOTIVO_CHOICES)

    # --- CAMPOS CONDICIONALES (ASESORÍA) ---
    funcionario_atiende = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name="Funcionario que lo atiende"
    )

    unidad_administrativa = models.ForeignKey(
        'territorio.UnidadAdscrita',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='visitas_atendidas',
        verbose_name='Unidad Administrativa'
    )

    descripcion = models.TextField(verbose_name="Observaciones de la visita")

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = "Visita"
        verbose_name_plural = "Visitas"

    def __str__(self):
        return f"{self.beneficiario.nombre_completo} - {self.get_motivo_display()}"

# ==============================================================================
# SECCIÓN 3: MOTOR DE EXPEDIENTE DIGITAL
# ==============================================================================

def ruta_expediente_universal(instance, filename):
    if instance.personal:
        return os.path.join('expedientes', 'institucional', instance.personal.cedula, filename)
    return os.path.join('expedientes', 'ciudadanos', instance.beneficiario.documento_identidad, filename)

class DocumentoExpediente(models.Model):
    CATEGORIA_CHOICES = [
        ('ID', 'Documento de Identidad'),
        ('CV', 'Síntesis Curricular (Personal)'),
        ('TIT', 'Títulos y Certificaciones'),
        ('CON', 'Contrato / Nombramiento'),
        ('RIF', 'RIF Vigente'),
        ('OTRO', 'Otros Documentos'),
    ]

    beneficiario = models.ForeignKey(
        Beneficiario, 
        on_delete=models.CASCADE, 
        null=True, blank=True, 
        related_name='documentos'
    )
    
    personal = models.ForeignKey(
        'personal.Personal', 
        on_delete=models.CASCADE, 
        null=True, blank=True, 
        related_name='documentos_institucionales'
    )

    archivo = models.FileField(upload_to=ruta_expediente_universal)
    categoria = models.CharField(max_length=4, choices=CATEGORIA_CHOICES, default='ID')
    nombre_documento = models.CharField(max_length=100)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Documento Digital"
        verbose_name_plural = "Expedientes Digitales"

    def __str__(self):
        dueno = self.beneficiario.nombre_completo if self.beneficiario else f"PERSONAL: {self.personal.apellidos if self.personal else 'S/N'}"
        return f"{self.get_categoria_display()} - {dueno}"