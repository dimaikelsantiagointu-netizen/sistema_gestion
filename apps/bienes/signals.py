from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import BienNacional, MovimientoBien

@receiver(pre_save, sender=BienNacional)
def gestionar_historial_movimiento(sender, instance, **kwargs):

    if instance.pk:
        try:
            obj_previo = BienNacional.objects.get(pk=instance.pk)
            
            if obj_previo.empleado_uso != instance.empleado_uso:
                MovimientoBien.objects.create(
                    bien=instance,
                    empleado_anterior=obj_previo.empleado_uso,
                    empleado_nuevo=instance.empleado_uso,
                    usuario_sistema="Sistema (Cambio Automático)" 
                )
        except BienNacional.DoesNotExist:
            pass