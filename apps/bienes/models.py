from django.db import models

# ==========================================
# A. TABLAS DE UBICACIÓN GEOGRÁFICA
# ==========================================

class Region(models.Model):
    id_region = models.AutoField(primary_key=True)
    nombre_region = models.CharField(max_length=100, unique=True, verbose_name="Región")

    def __str__(self):
        return self.nombre_region

class Estado(models.Model):
    id_estado = models.AutoField(primary_key=True)
    nombre_estado = models.CharField(max_length=100, verbose_name="Estado")
    fk_region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name='estados')

    def __str__(self):
        return self.nombre_estado

class Ciudad(models.Model):
    id_ciudad = models.AutoField(primary_key=True)
    nombre_ciudad = models.CharField(max_length=100, verbose_name="Ciudad")
    fk_estado = models.ForeignKey(Estado, on_delete=models.PROTECT, related_name='ciudades')

    def __str__(self):
        return self.nombre_ciudad

class Municipio(models.Model):
    id_municipio = models.AutoField(primary_key=True)
    nombre_municipio = models.CharField(max_length=100, verbose_name="Municipio")
    fk_estado = models.ForeignKey(Estado, on_delete=models.PROTECT, related_name='municipios')

    def __str__(self):
        return self.nombre_municipio

class Parroquia(models.Model):
    id_parroquia = models.AutoField(primary_key=True)
    nombre_parroquia = models.CharField(max_length=100, verbose_name="Parroquia")
    fk_municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT, related_name='parroquias')

    def __str__(self):
        return self.nombre_parroquia

# ==========================================
# B. TABLAS OPERATIVAS
# ==========================================

class UnidadTrabajo(models.Model):
    id_unidad = models.AutoField(primary_key=True)
    nombre_unidad = models.CharField(max_length=255, verbose_name="Nombre de Unidad")
    fk_parroquia = models.ForeignKey(Parroquia, on_delete=models.PROTECT)
    fk_ciudad = models.ForeignKey(Ciudad, on_delete=models.PROTECT)
    direccion_especifica = models.TextField(verbose_name="Dirección Específica")

    def __str__(self):
        return self.nombre_unidad

class Empleado(models.Model):
    cedula = models.CharField(max_length=20, primary_key=True, verbose_name="Cédula")
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    fk_unidad_trabajo = models.ForeignKey(UnidadTrabajo, on_delete=models.PROTECT, related_name='empleados')
    cargo = models.CharField(max_length=150)
    estatus = models.BooleanField(default=True)

    def __str__(self):
        # Mejora: El nombre completo debe aparecer (Instrucción guardada)
        return f"{self.nombre} {self.apellido}"

class BienNacional(models.Model):
    # RF-01 y BR-01: Registro Individual y Unicidad
    nro_identificacion = models.CharField(max_length=50, primary_key=True, unique=True, verbose_name="Nro. Identificación")
    subcuenta = models.CharField(max_length=100)
    descripcion = models.TextField()
    marca = models.CharField(max_length=100)
    modelo = models.CharField(max_length=100)
    color = models.CharField(max_length=50)
    serial = models.CharField(max_length=100, unique=True)
    monto = models.DecimalField(max_digits=15, decimal_places=2)
    
    observaciones = models.TextField(blank=True, null=True)
    responsable_patrimonial = models.CharField(max_length=255)
    registro_persona = models.CharField(max_length=255)
    jefe_inventariado = models.CharField(max_length=255)
    
    # Relaciones operativas
    fk_empleado_uso = models.ForeignKey(Empleado, on_delete=models.PROTECT, verbose_name="Responsable de Uso")
    fk_unidad_trabajo = models.ForeignKey(UnidadTrabajo, on_delete=models.PROTECT, verbose_name="Unidad de Trabajo")
    
    # Soporte para QR (RF-04)
    qr_code = models.ImageField(upload_to='qrs/', blank=True, null=True)

    def __str__(self):
        return f"{self.nro_identificacion} - {self.descripcion[:30]}"