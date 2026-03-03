from django.db import models
import uuid as uuid_lib
import qrcode
from io import BytesIO
from django.core.files import File
from django.conf import settings
from django.contrib.auth.models import User

# ==========================
# UBICACIÓN GEOGRÁFICA
# ==========================

class Region(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name_plural = "1. Regiones"

class Estado(models.Model):
    nombre = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.PROTECT)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name_plural = "2. Estados"

class Municipio(models.Model):
    nombre = models.CharField(max_length=100)
    estado = models.ForeignKey(Estado, on_delete=models.PROTECT)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name_plural = "3. Municipios"

class Parroquia(models.Model):
    nombre = models.CharField(max_length=100)
    municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name_plural = "4. Parroquias"

class Ciudad(models.Model):
    nombre = models.CharField(max_length=100)
    estado = models.ForeignKey(Estado, on_delete=models.PROTECT)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name_plural = "5. Ciudades"


class UnidadTrabajo(models.Model):
    nombre = models.CharField(max_length=150)
    parroquia = models.ForeignKey(Parroquia, on_delete=models.PROTECT)
    ciudad = models.ForeignKey(Ciudad, on_delete=models.PROTECT)
    direccion = models.TextField()

    def __str__(self):
        return f"{self.nombre} ({self.ciudad.nombre})"

    class Meta:
        verbose_name_plural = "6. Unidades de Trabajo"
    

# ==========================
# EMPLEADOS
# ==========================

class Empleado(models.Model):
    cedula = models.CharField(max_length=15, primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    unidad_trabajo = models.ForeignKey(UnidadTrabajo, on_delete=models.PROTECT)
    cargo = models.CharField(max_length=100)
    estatus = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

# ==========================
# BIENES NACIONALES
# ==========================


class BienNacional(models.Model):
    # Identificación y UUID (RF-01 y Seguridad)
    nro_identificacion = models.CharField(max_length=50, unique=True)
    uuid = models.UUIDField(default=uuid_lib.uuid4, editable=False, unique=True)

    # Datos Técnicos
    subcuenta = models.CharField(max_length=50)
    descripcion = models.TextField()
    marca = models.CharField(max_length=100)
    modelo = models.CharField(max_length=100)
    color = models.CharField(max_length=50)
    serial = models.CharField(max_length=100, unique=True) # BR-01: Serial Único
    monto = models.DecimalField(max_digits=12, decimal_places=2)

    observaciones = models.TextField(blank=True, null=True)
    responsable_patrimonial = models.CharField(max_length=150, help_text="Autoridad patrimonial")
    jefe_inventariado = models.CharField(max_length=150, help_text="Quién supervisó el inventario")
    registro_persona = models.CharField(max_length=150, help_text="Persona que digita el bien")

    ESTADOS_CHOICES = [
        ('Buen Estado', 'Buen Estado'),
        ('Regular', 'Regular'),
        ('Malo', 'Malo'),
        ('En Reparación', 'En Reparación'),
        ('Desincorporado', 'Desincorporado'),
    ]
    estado_bien = models.CharField(max_length=30, choices=ESTADOS_CHOICES, default="Buen Estado")
    
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # Relaciones - BR-02: PROTECT evita borrar empleado si tiene bienes
    empleado_uso = models.ForeignKey('Empleado', on_delete=models.PROTECT)
    unidad_trabajo = models.ForeignKey('UnidadTrabajo', on_delete=models.PROTECT)

    qr_imagen = models.ImageField(upload_to='qr/', blank=True, null=True)

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        
        # BR-03: Generación de QR (solo si es nuevo o no tiene imagen)
        if is_new or not self.qr_imagen:
            # Leemos el dominio desde settings (ej: https://sisi.dominio.com)
            #Aca se debera cambiar en producción por el dominio real del sistema, actualmente se deja localhost para pruebas locales
            dominio = getattr(settings, 'SITE_DOMAIN', 'http://192.168.0.110:8000')
            
            # RF-05: El QR apunta a la URL pública de consulta usando el UUID
            url_consulta = f"{dominio}/bienes/consulta/{self.uuid}/"
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url_consulta)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            
            file_name = f'qr_{self.nro_identificacion}.png'
            self.qr_imagen.save(file_name, File(buffer), save=False)
            
            super().save(update_fields=['qr_imagen'])

    def __str__(self):
        return f"{self.nro_identificacion} - {self.descripcion[:30]}"

# ==========================
# HISTORIAL Y MOVIMIENTOS
# ==========================

class MovimientoBien(models.Model):
    bien = models.ForeignKey(BienNacional, on_delete=models.CASCADE, related_name='movimientos')
    empleado_anterior = models.ForeignKey(Empleado, related_name='movimientos_anteriores', on_delete=models.PROTECT)
    empleado_nuevo = models.ForeignKey(Empleado, related_name='movimientos_nuevos', on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario_sistema = models.CharField(max_length=100)

    def __str__(self):
        return f"Movimiento {self.bien.nro_identificacion}"

class BienHistorial(models.Model):
    bien = models.ForeignKey(BienNacional, on_delete=models.CASCADE, related_name='historial_cambios')
    
    fecha_movimiento = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField() 
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True
    )
    
    estado_anterior = models.CharField(max_length=100, null=True, blank=True)
    estado_nuevo = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        ordering = ['-fecha_movimiento']
        verbose_name_plural = "Historial de Bienes"