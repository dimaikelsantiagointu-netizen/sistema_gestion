import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import post_save, post_delete
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.forms.models import model_to_dict
from .models import LogAuditoria
from .middleware import get_current_user, get_current_ip

# 1. Configuración de exclusión
APPS_IGNORADAS = [
    'auditoria', 'admin', 'sessions', 'contenttypes', 'migrations'
]

def limpiar_datos_auditoria(instance):
    """ Evita errores de serialización eliminando campos complejos """
    try:
        datos = model_to_dict(instance)
        campos_a_eliminar = ['user_permissions', 'groups', 'permissions', 'password']
        
        for campo in campos_a_eliminar:
            if campo in datos:
                del datos[campo]
                
        json_datos = json.dumps(datos, cls=DjangoJSONEncoder)
        return json.loads(json_datos)
    except:
        return {"error": "No se pudo serializar el objeto"}

# --- AUDITORÍA DE DATOS (CRUD) ---

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
            descripcion=f"{'CREÓ' if created else 'MODIFICÓ'} {modulo}: {instance}",
            valor_nuevo=datos_serializables
        )
    except Exception as e:
        print(f"Error auditoría save: {e}")

@receiver(post_delete)
def auditar_eliminacion(sender, instance, **kwargs):
    if sender._meta.app_label in APPS_IGNORADAS:
        return

    try:
        LogAuditoria.objects.create(
            usuario=get_current_user(),
            direccion_ip=get_current_ip(),
            modulo=sender._meta.verbose_name.upper(),
            accion='E',
            objeto_id=instance.pk,
            descripcion=f"ELIMINÓ {sender._meta.verbose_name.upper()}: {instance}",
            valor_anterior=limpiar_datos_auditoria(instance)
        )
    except Exception as e:
        print(f"Error auditoría delete: {e}")

# --- AUDITORÍA DE SEGURIDAD (ACCESOS) ---

@receiver(user_logged_in)
def log_login_exitoso(sender, request, user, **kwargs):
    """ Registra cuando un usuario entra al sistema """
    LogAuditoria.objects.create(
        usuario=user,
        direccion_ip=get_current_ip(),
        modulo='SEGURIDAD',
        accion='L',  # Asegúrate de tener 'L' en las opciones de 'accion' en tu modelo
        descripcion=f"INICIO DE SESIÓN EXITOSO: El usuario {user.username} ha ingresado."
    )

@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    """ Registra cuando un usuario sale del sistema """
    if user:
        LogAuditoria.objects.create(
            usuario=user,
            direccion_ip=get_current_ip(),
            modulo='SEGURIDAD',
            accion='S',  # Asegúrate de tener 'S' en las opciones de 'accion' en tu modelo
            descripcion=f"CIERRE DE SESIÓN: El usuario {user.username} ha salido."
        )

@receiver(user_login_failed)
def log_login_fallido(sender, credentials, request, **kwargs):
    """ Registra intentos de acceso no autorizados (Punto 5 del alcance) """
    LogAuditoria.objects.create(
        usuario=None, # No hay usuario autenticado
        direccion_ip=get_current_ip(),
        modulo='SEGURIDAD',
        accion='F', # 'F' de Fallido
        descripcion=f"INTENTO DE ACCESO FALLIDO: Usuario intentado: {credentials.get('username')}"
    )