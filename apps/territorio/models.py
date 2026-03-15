from django.db import models


class Estado(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Estado"
        verbose_name_plural = "Estados"

    def __str__(self):
        return self.nombre

class Municipio(models.Model):
    nombre = models.CharField(max_length=100)
    estado = models.ForeignKey(Estado, on_delete=models.CASCADE, related_name='municipios')

    class Meta:
        verbose_name = "Municipio"
        verbose_name_plural = "Municipios"

    def __str__(self):
        return f"{self.nombre} ({self.estado.nombre})"

class Ciudad(models.Model):
    nombre = models.CharField(max_length=100)
    estado = models.ForeignKey(Estado, on_delete=models.CASCADE, related_name='ciudades')

    class Meta:
        verbose_name = "Ciudad"
        verbose_name_plural = "Ciudades"

    def __str__(self):
        return self.nombre

class Parroquia(models.Model):
    nombre = models.CharField(max_length=100)
    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE, related_name='parroquias')

    class Meta:
        verbose_name = "Parroquia"
        verbose_name_plural = "Parroquias"

    def __str__(self):
        return self.nombre

class Comuna(models.Model):
    nombre = models.CharField(max_length=200)
    codigo_comuna = models.CharField(max_length=50, blank=True, null=True, help_text="Código de registro de la comuna")
    parroquia = models.ForeignKey(Parroquia, on_delete=models.CASCADE, related_name='comunas')

    class Meta:
        verbose_name = "Comuna"
        verbose_name_plural = "Comunas"

    def __str__(self):
        return self.nombre