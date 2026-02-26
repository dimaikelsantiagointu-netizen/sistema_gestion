from django.db import models
import uuid
import qrcode
from io import BytesIO
from django.core.files import File
from django.conf import settings

# ==========================
# UBICACIÓN GEOGRÁFICA
# ==========================

class Region(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Estado(models.Model):
    nombre = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.PROTECT)

    def __str__(self):
        return self.nombre


class Municipio(models.Model):
    nombre = models.CharField(max_length=100)
    estado = models.ForeignKey(Estado, on_delete=models.PROTECT)

    def __str__(self):
        return self.nombre


class Parroquia(models.Model):
    nombre = models.CharField(max_length=100)
    municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT)

    def __str__(self):
        return self.nombre


class Ciudad(models.Model):
    nombre = models.CharField(max_length=100)
    estado = models.ForeignKey(Estado, on_delete=models.PROTECT)

    def __str__(self):
        return self.nombre


class UnidadTrabajo(models.Model):
    nombre = models.CharField(max_length=150)
    parroquia = models.ForeignKey(Parroquia, on_delete=models.PROTECT)
    ciudad = models.ForeignKey(Ciudad, on_delete=models.PROTECT)
    direccion = models.TextField()

    def __str__(self):
        return self.nombre
    

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

    nro_identificacion = models.CharField(max_length=50, unique=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    subcuenta = models.CharField(max_length=50)
    descripcion = models.TextField()
    marca = models.CharField(max_length=100)
    modelo = models.CharField(max_length=100)
    color = models.CharField(max_length=50)
    serial = models.CharField(max_length=100, unique=True)

    monto = models.DecimalField(max_digits=12, decimal_places=2)

    estado_bien = models.CharField(max_length=30, default="Activo")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    empleado_uso = models.ForeignKey('Empleado', on_delete=models.PROTECT)
    unidad_trabajo = models.ForeignKey('UnidadTrabajo', on_delete=models.PROTECT)

    qr_imagen = models.ImageField(upload_to='qr/', blank=True, null=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.qr_imagen:
            qr = qrcode.make(f"http://127.0.0.1:8000/consulta/{self.uuid}/")

            buffer = BytesIO()
            qr.save(buffer, format='PNG')

            file_name = f'qr_{self.uuid}.png'
            self.qr_imagen.save(file_name, File(buffer), save=False)

            super().save(update_fields=['qr_imagen'])

    def __str__(self):
        return self.descripcion

# ==========================
# HISTORIAL
# ==========================

class MovimientoBien(models.Model):
    bien = models.ForeignKey(BienNacional, on_delete=models.CASCADE)
    empleado_anterior = models.ForeignKey(Empleado, related_name='anterior', on_delete=models.PROTECT)
    empleado_nuevo = models.ForeignKey(Empleado, related_name='nuevo', on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario_sistema = models.CharField(max_length=100)

    def __str__(self):
        return f"Movimiento {self.bien}"