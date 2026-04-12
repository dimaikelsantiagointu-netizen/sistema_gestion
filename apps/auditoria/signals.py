import json
import logging
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import post_save, post_delete
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.forms.models import model_to_dict
from .models import LogAuditoria
from .middleware import get_current_user, get_current_ip

# USAR EL CANAL ÚNICO DEFINIDO EN EL SETTINGS
logger = logging.getLogger('CH_AUDITORIA')

# 1. Configuración de exclusión (AÑADIMOS 'recibos')
APPS_IGNORADAS = [
    'auditoria', 'admin', 'sessions', 'contenttypes', 'migrations', 
    'admin_interface', 'recibos'  # <--- RECIBOS AHORA ESTÁ BLOQUEADO
]

def limpiar_datos_auditoria(instance):
    """ Evita errores de serialización eliminando campos complejos """
    try:
        datos = model_to_dict(instance)
        # Limpieza de seguridad
        campos_a_eliminar = ['user_permissions', 'groups', 'permissions', 'password']
        for campo in campos_a_eliminar:
            if campo in datos: 
                del datos[campo]
                
        json_datos = json.dumps(datos, cls=DjangoJSONEncoder)
        return json.loads(json_datos)
    except Exception:
        return {"error": "No se pudo serializar el objeto"}

# --- AUDITORÍA DE DATOS (CRUD) ---

@receiver(post_save)
def auditar_guardado(sender, instance, created, **kwargs):
    # BLOQUEO POR APP LABEL
    if sender._meta.app_label in APPS_IGNORADAS:
        return

    try:
        accion = 'C' if created else 'M'
        modulo = sender._meta.verbose_name.upper()
        
        LogAuditoria.objects.create(
            usuario=get_current_user(),
            direccion_ip=get_current_ip(),
            modulo=modulo,
            accion=accion,
            objeto_id=str(instance.pk),
            descripcion=f"{'CREÓ' if created else 'MODIFICÓ'} {modulo}: {instance}",
            valor_nuevo=limpiar_datos_auditoria(instance)
        )
        # Solo escribe en auditoria_global.log si pasó el filtro de APPS_IGNORADAS
        logger.info(f"DATA_CHANGE | {accion} | {modulo} | ID: {instance.pk}")
    except Exception as e:
        logger.error(f"ERROR_AUDITORIA_SAVE: {str(e)}")

@receiver(post_delete)
def auditar_eliminacion(sender, instance, **kwargs):
    # BLOQUEO POR APP LABEL
    if sender._meta.app_label in APPS_IGNORADAS:
        return

    try:
        modulo = sender._meta.verbose_name.upper()
        LogAuditoria.objects.create(
            usuario=get_current_user(),
            direccion_ip=get_current_ip(),
            modulo=modulo,
            accion='E',
            objeto_id=str(instance.pk),
            descripcion=f"ELIMINÓ {modulo}: {instance}",
            valor_anterior=limpiar_datos_auditoria(instance)
        )
        logger.info(f"DATA_CHANGE | E | {modulo} | ID: {instance.pk}")
    except Exception as e:
        logger.error(f"ERROR_AUDITORIA_DELETE: {str(e)}")

# --- AUDITORÍA DE SEGURIDAD (ACCESOS) ---

@receiver(user_logged_in)
def log_login_exitoso(sender, request, user, **kwargs):
    try:
        LogAuditoria.objects.create(
            usuario=user,
            direccion_ip=get_current_ip(),
            modulo='SEGURIDAD',
            accion='L',
            descripcion=f"LOGIN EXITOSO: {user.username}"
        )
        logger.info(f"AUTH | LOGIN | USER: {user.username}")
    except Exception as e:
        logger.error(f"ERROR_LOG_LOGIN: {str(e)}")

@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    if user:
        try:
            LogAuditoria.objects.create(
                usuario=user,
                direccion_ip=get_current_ip(),
                modulo='SEGURIDAD',
                accion='S',
                descripcion=f"LOGOUT: {user.username}"
            )
            logger.info(f"AUTH | LOGOUT | USER: {user.username}")
        except Exception as e:
            logger.error(f"ERROR_LOG_LOGOUT: {str(e)}")

@receiver(user_login_failed)
def log_login_fallido(sender, credentials, request, **kwargs):
    try:
        LogAuditoria.objects.create(
            usuario=None,
            direccion_ip=get_current_ip(),
            modulo='SEGURIDAD',
            accion='F',
            descripcion=f"LOGIN FALLIDO: Intento con usuario {credentials.get('username')}"
        )
        logger.warning(f"AUTH | LOGIN_FAILED | USER_ATTEMPT: {credentials.get('username')}")
    except Exception as e:
        logger.error(f"ERROR_LOG_LOGIN_FAILED: {str(e)}")