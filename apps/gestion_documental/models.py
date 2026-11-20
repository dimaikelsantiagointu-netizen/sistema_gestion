import os
import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from apps.territorio.models import Comuna, Estado, Municipio, Parroquia


MAX_PDF_SIZE = 5 * 1024 * 1024


def private_document_storage():
    return FileSystemStorage(
        location=Path(settings.PRIVATE_MEDIA_ROOT) / 'gestion_documental',
    )


def validate_pdf_file(uploaded_file):
    if uploaded_file.size > MAX_PDF_SIZE:
        raise ValidationError('Cada archivo PDF debe pesar como máximo 5 MB.')
    if Path(uploaded_file.name).suffix.lower() != '.pdf':
        raise ValidationError('Solo se permiten archivos PDF.')

    position = uploaded_file.tell()
    uploaded_file.seek(0)
    signature = uploaded_file.read(5)
    uploaded_file.seek(position)
    if signature != b'%PDF-':
        raise ValidationError('El archivo seleccionado no parece ser un PDF válido.')


def expediente_upload_path(instance, filename):
    safe_name = f'{uuid.uuid4().hex}.pdf'
    return os.path.join(
        str(instance.expediente.fecha_registro.year),
        instance.expediente.codigo,
        safe_name,
    )


class Titular(models.Model):
    nombre = models.CharField(max_length=255, verbose_name='Nombre del titular')
    documento_identidad = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        verbose_name='Cédula o RIF',
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Titular'
        verbose_name_plural = 'Titulares'

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.strip().upper()
        self.documento_identidad = (
            self.documento_identidad.strip().upper()
            if self.documento_identidad and self.documento_identidad.strip()
            else None
        )
        super().save(*args, **kwargs)

    def __str__(self):
        if self.documento_identidad:
            return f'{self.nombre} ({self.documento_identidad})'
        return self.nombre


class EstatusDocumento(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name='Estatus')
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True, verbose_name='Disponible')

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'Estatus documental'
        verbose_name_plural = 'Estatus documentales'

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class SecuenciaExpediente(models.Model):
    ultimo_numero = models.PositiveBigIntegerField(default=0)

    class Meta:
        verbose_name = 'Secuencia de expediente'
        verbose_name_plural = 'Secuencia de expedientes'


class Expediente(models.Model):
    codigo = models.CharField(
        max_length=24,
        unique=True,
        editable=False,
        verbose_name='Código',
    )
    estado = models.ForeignKey(
        Estado,
        on_delete=models.PROTECT,
        related_name='expedientes_documentales',
    )
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.PROTECT,
        related_name='expedientes_documentales',
    )
    parroquia = models.ForeignKey(
        Parroquia,
        on_delete=models.PROTECT,
        related_name='expedientes_documentales',
    )
    comuna = models.ForeignKey(
        Comuna,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='expedientes_documentales',
    )
    titular = models.ForeignKey(
        Titular,
        on_delete=models.PROTECT,
        related_name='expedientes',
    )
    numero_protocolo = models.CharField(max_length=80, verbose_name='Número de protocolo')
    numero_tomo = models.CharField(max_length=80, verbose_name='Número de tomo')
    fecha_registro = models.DateField(
        default=timezone.localdate,
        verbose_name='Fecha de registro',
    )
    superficie_m2 = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Superficie (m²)',
    )
    direccion = models.TextField(verbose_name='Dirección')
    lindero_norte = models.TextField(verbose_name='Lindero norte')
    lindero_sur = models.TextField(verbose_name='Lindero sur')
    lindero_este = models.TextField(verbose_name='Lindero este')
    lindero_oeste = models.TextField(verbose_name='Lindero oeste')
    estatus = models.ForeignKey(
        EstatusDocumento,
        on_delete=models.PROTECT,
        related_name='expedientes',
    )
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_registro', '-id']
        verbose_name = 'Expediente documental'
        verbose_name_plural = 'Expedientes documentales'

    @property
    def superficie_hectareas(self):
        return (self.superficie_m2 / Decimal('10000')).quantize(
            Decimal('0.0001'),
        )

    def clean(self):
        super().clean()
        errores = {}
        if self.municipio_id and self.estado_id:
            if self.municipio.estado_id != self.estado_id:
                errores['municipio'] = 'El municipio no pertenece al estado seleccionado.'
        if self.parroquia_id and self.municipio_id:
            if self.parroquia.municipio_id != self.municipio_id:
                errores['parroquia'] = 'La parroquia no pertenece al municipio seleccionado.'
        if self.comuna_id and self.parroquia_id:
            if self.comuna.parroquia_id != self.parroquia_id:
                errores['comuna'] = 'La comuna no pertenece a la parroquia seleccionada.'
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        if self.codigo:
            super().save(*args, **kwargs)
            return

        with transaction.atomic():
            secuencia, _ = SecuenciaExpediente.objects.select_for_update().get_or_create(
                pk=1,
                defaults={'ultimo_numero': 0},
            )
            secuencia.ultimo_numero += 1
            secuencia.save(update_fields=['ultimo_numero'])
            self.codigo = (
                f'EXP-{timezone.localdate().year}-{secuencia.ultimo_numero:06d}'
            )
            super().save(*args, **kwargs)

    def __str__(self):
        return self.codigo or 'Nuevo expediente'


class ArchivoExpediente(models.Model):
    expediente = models.ForeignKey(
        Expediente,
        on_delete=models.CASCADE,
        related_name='archivos',
    )
    archivo = models.FileField(
        storage=private_document_storage,
        upload_to=expediente_upload_path,
        validators=[validate_pdf_file],
        verbose_name='Archivo PDF',
    )
    nombre_original = models.CharField(max_length=255)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha_subida', 'id']
        verbose_name = 'Archivo de expediente'
        verbose_name_plural = 'Archivos de expedientes'

    def __str__(self):
        return f'{self.expediente.codigo} - {self.nombre_original}'
