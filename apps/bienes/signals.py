from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import BienNacional, MovimientoBien, BienHistorial

# ==========================================
# 1. GESTIÓN DE CAMBIOS (PRE-SAVE)
# ==========================================
@receiver(pre_save, sender=BienNacional)
def detectar_cambios_antes_de_guardar(sender, instance, **kwargs):
    """
    Detecta cambios de empleado y de estado físico ANTES de guardar.
    Esto nos permite capturar el 'estado_anterior' real.
    """
    if instance.pk:  # Si el bien ya existe (Edición)
        try:
            obj_previo = BienNacional.objects.get(pk=instance.pk)
            
            # --- CASO A: CAMBIO DE CUSTODIA (PERSONAL) ---
            if obj_previo.empleado_uso != instance.empleado_uso:
                MovimientoBien.objects.create(
                    bien=instance,
                    empleado_anterior=obj_previo.empleado_uso,
                    empleado_nuevo=instance.empleado_uso,
                    usuario_sistema="Sistema (Reasignación)"
                )

            # --- CASO B: CAMBIO DE ESTADO FÍSICO ---
            if obj_previo.estado_bien != instance.estado_bien:
                BienHistorial.objects.create(
                    bien=instance,
                    descripcion=f"Cambio de estado físico detectado.",
                    estado_anterior=obj_previo.estado_bien,
                    estado_nuevo=instance.estado_bien,
                    usuario=None 
                )
                
        except BienNacional.DoesNotExist:
            pass

# ==========================================
# 2. REGISTRO INICIAL (POST-SAVE)
# ==========================================
@receiver(post_save, sender=BienNacional)
def registro_inicial_bien(sender, instance, created, **kwargs):
    """
    Crea el primer hito en el historial cuando el bien nace en el sistema.
    """
    if created:
        BienHistorial.objects.create(
            bien=instance,
            descripcion="Registro inicial del bien en el sistema (Carga inicial).",
            estado_anterior=None,
            estado_nuevo=instance.estado_bien,
            usuario=None
        )