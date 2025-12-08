from django.db import models
from django.db.models import Max
from django.utils.translation import gettext_lazy as _

MAPEO_CATEGORIAS = {
    1: _("Título de Tierra Urbana - Adjudicación en Propiedad"),
    2: _("Título de Tierra Urbana - Adjudicación más Vivienda"),
    3: _("Vivienda - Tierra Municipal"),
    4: _("Vivienda - Tierra Privada"),
    5: _("Vivienda - Tierra INAVI/INTU"),
    6: _("Excedentes - Con título Tierra Urbana"),
    7: _("Excedentes - Título INAVI"),
    8: _("Estudios Técnicos"),
    9: _("Arrendamiento Locales Comerciales"),
    10: _("Arrendamiento de Terrenos")
}

class Recibo(models.Model):
    id = models.AutoField(primary_key=True)
    numero_recibo = models.IntegerField(
        unique=True, 
        verbose_name="Número de Recibo",
        help_text="Número consecutivo asignado al recibo."
    )
    
    nombre = models.CharField(max_length=255, verbose_name="Nombre del Pagador")
    rif_cedula_identidad = models.CharField(max_length=20, verbose_name="Cédula/RIF")
    direccion_inmueble = models.TextField(blank=True, null=True, verbose_name="Dirección del Inmueble")
    ente_liquidado = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ente Liquidado")
    concepto = models.TextField(blank=True, null=True, verbose_name="Concepto de Pago")
    
    categoria1 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(1))
    categoria2 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(2))
    categoria3 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(3))
    categoria4 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(4))
    categoria5 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(5))
    categoria6 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(6))
    categoria7 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(7))
    categoria8 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(8))
    categoria9 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(9))
    categoria10 = models.BooleanField(default=False, verbose_name=MAPEO_CATEGORIAS.get(10))

    gastos_administrativos = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Gastos Adm. (Bs)")
    tasa_dia = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Tasa del Día (Bs/Divisa)")
    total_monto_bs = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Monto Total (Bs)")
    
    numero_transferencia = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name="Número de Transferencia",
        unique=True, 
    )
    
    fecha = models.DateField(verbose_name="Fecha de Pago/Emisión")
    
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Pagado', 'Pagado'),
        ('En Revisión', 'En Revisión'),
        ('Rechazado', 'Rechazado'),
    ]
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES, 
        default='Pendiente',
        verbose_name="Estado de Pago"
    )
    
    conciliado = models.BooleanField(default=False, verbose_name="Conciliado (Banco)")
    anulado = models.BooleanField(default=False, verbose_name="Anulado")

    usuario_creador = models.CharField(
      max_length=150, 
        verbose_name="Usuario Creador"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha Creación")
    
    usuario_anulo = models.CharField(
       max_length=150, 
        null=True, 
        blank=True,
        verbose_name="Usuario que Anuló"
    )
    fecha_anulacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Anulación")

    class Meta:
        verbose_name = "Recibo de Pago"
        verbose_name_plural = "Recibos de Pago"
        db_table = 'recibos_pago'
        ordering = ['-fecha', '-numero_recibo'] # Ordenar por fecha más reciente

    def __str__(self):
        return f"Recibo N° {self.numero_recibo} - {self.nombre}"

    def save(self, *args, **kwargs):
        if not self.id and not self.numero_recibo:
            max_recibo = Recibo.objects.all().aggregate(Max('numero_recibo'))['numero_recibo__max']           
            self.numero_recibo = (max_recibo if max_recibo is not None else 0) + 1
            
        super().save(*args, **kwargs)
        
    def get_categorias_marcadas_list(self): 
        """Devuelve una lista de los nombres de las categorías marcadas."""
        categorias = []
        for i in range(1, 11):
            campo = f'categoria{i}'
            if getattr(self, campo):
                categorias.append(MAPEO_CATEGORIAS.get(i))
        return categorias
    
    