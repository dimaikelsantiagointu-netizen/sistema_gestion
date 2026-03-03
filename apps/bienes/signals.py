from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import BienNacional, MovimientoBien, BienHistorial

# ==========================================
# 1. HISTORIAL DE CAMBIOS GENERALES (POST-SAVE)
# ==========================================
@receiver(post_save, sender=BienNacional)
def registrar_historial_bien(sender, instance, created, **kwargs):
    """
    Registra cada vez que se crea o edita un bien.
    """
    if created:
        descripcion = "Registro inicial del bien en el sistema."
        estado_anterior = None
    else:
        # En el post_save no podemos saber el estado anterior fácilmente, 
        # así que solo marcamos que hubo una actualización.
        descripcion = f"Actualización de datos técnicos del bien."
        estado_anterior = instance.estado_bien # Aquí podrías mejorar la lógica con pre_save si necesitas el valor exacto previo

    # Creamos el registro en BienHistorial
    BienHistorial.objects.create(
        bien=instance,
        descripcion=descripcion,
        estado_anterior=estado_anterior,
        estado_nuevo=instance.estado_bien, # Usamos el campo real: estado_bien
        usuario=None # El usuario suele venir del request, aquí se deja null o sistema
    )

# ==========================================
# 2. HISTORIAL DE MOVIMIENTOS DE PERSONAL (PRE-SAVE)
# ==========================================
@receiver(pre_save, sender=BienNacional)
def gestionar_historial_movimiento(sender, instance, **kwargs):
    """
    Detecta si el empleado_uso cambió ANTES de guardar en la base de datos.
    """
    if instance.pk: # Solo si el objeto ya existe (es una edición)
        try:
            obj_previo = BienNacional.objects.get(pk=instance.pk)
            
            # Si el empleado asignado cambió
            if obj_previo.empleado_uso != instance.empleado_uso:
                MovimientoBien.objects.create(
                    bien=instance,
                    empleado_anterior=obj_previo.empleado_uso,
                    empleado_nuevo=instance.empleado_uso,
                    usuario_sistema="Sistema (Reasignación Automática)" 
                )
                
            # Opcional: También detectar cambio de estado aquí para guardar el 'estado_anterior' exacto
            # if obj_previo.estado_bien != instance.estado_bien:
            #     ... lógica adicional ...

        except BienNacional.DoesNotExist:
            pass