import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict
from .models import LogAuditoria
from .middleware import get_current_user, get_current_ip

APPS_IGNORADAS = [
    'auditoria', 'admin', 'sessions', 'contenttypes', 'migrations'
]

def limpiar_datos_auditoria(instance):
    """
    Convierte la instancia en un diccionario y elimina campos que 
    causan errores de serialización (Many-to-Many como permisos).
    """
    datos = model_to_dict(instance)
    # Lista de campos técnicos que suelen dar problemas en JSON
    campos_a_eliminar = ['user_permissions', 'groups', 'permissions']
    
    for campo in campos_a_eliminar:
        if campo in datos:
            del datos[campo]
            
    # Convertir a JSON string usando el encoder de Django y luego a dict de nuevo
    # Esto resuelve el problema de las fechas (datetime)
    json_datos = json.dumps(datos, cls=DjangoJSONEncoder)
    return json.loads(json_datos)

@receiver(post_save)
def auditar_guardado(sender, instance, created, **kwargs):
    if sender._meta.app_label in APPS_IGNORADAS:
        return

    usuario = get_current_user()
    ip = get_current_ip()
    accion = 'C' if created else 'M'
    modulo = sender._meta.verbose_name.upper()
    
    try:
        datos_serializables = limpiar_datos_auditoria(instance)
        
        LogAuditoria.objects.create(
            usuario=usuario,
            direccion_ip=ip,
            modulo=modulo,
            accion=accion,
            objeto_id=instance.pk,
            descripcion=f"{'Creó' if created else 'Modificó'} {modulo}: {instance}",
            valor_nuevo=datos_serializables
        )
    except Exception as e:
        # Si algo falla, registramos el error pero no bloqueamos el sistema
        print(f"Error en auditoría: {e}")

@receiver(post_delete)
def auditar_eliminacion(sender, instance, **kwargs):
    if sender._meta.app_label in APPS_IGNORADAS:
        return

    try:
        datos_serializables = limpiar_datos_auditoria(instance)
        
        LogAuditoria.objects.create(
            usuario=get_current_user(),
            direccion_ip=get_current_ip(),
            modulo=sender._meta.verbose_name.upper(),
            accion='E',
            objeto_id=instance.pk,
            descripcion=f"Eliminó {sender._meta.verbose_name.upper()}: {instance}",
            valor_anterior=datos_serializables
        )
    except Exception as e:
        print(f"Error en auditoría de eliminación: {e}")