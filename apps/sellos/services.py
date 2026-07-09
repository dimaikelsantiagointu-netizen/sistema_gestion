from django.contrib import messages
from django.utils import timezone

from apps.auditoria.models import LogAuditoria
from apps.recibos.models import Recibo
from .models import HistorialSello, SelloDorado
from django.db import transaction


def registrar_historial(sello, usuario, accion, descripcion):
    HistorialSello.objects.create(
        sello=sello,
        usuario=usuario,
        accion=accion,
        descripcion=descripcion,
    )


def registrar_auditoria(usuario, accion, descripcion, objeto_id=None):
    LogAuditoria.objects.create(
        usuario=usuario,
        modulo='SELLOS DORADOS',
        accion=accion,
        descripcion=descripcion,
        objeto_id=str(objeto_id) if objeto_id else None,
    )


def aprobar_recibos_para_sello(recibo_ids, usuario):
    recibos = Recibo.objects.filter(pk__in=recibo_ids, anulado=False)
    for recibo in recibos:
        recibo.aprobado_sello_dorado = True
        recibo.estatus_sello_dorado = 'aprobado'
        recibo.fecha_aprobacion_sello = timezone.now()
        # Marcar como no notificado para que Consultoría lo detecte
        recibo.notificado_consultoria = False
        recibo.save(update_fields=['aprobado_sello_dorado', 'estatus_sello_dorado', 'fecha_aprobacion_sello', 'notificado_consultoria'])
        registrar_auditoria(usuario, 'M', f'Aprobó el recibo N° {recibo.numero_recibo}', recibo.pk)
    return recibos


def asignar_recibos_a_sello(sello, recibo_ids, usuario):
    # Operación atómica para evitar condiciones de carrera en asignaciones concurrentes
    with transaction.atomic():
        # Normalizar ids a enteros cuando sea posible
        ids = []
        for rid in recibo_ids:
            try:
                ids.append(int(rid))
            except Exception:
                # ignorar valores inválidos, quedan reportados luego
                continue

        recibos = Recibo.objects.select_for_update().filter(pk__in=ids)

        assigned = []
        errors = []

        recibos_map = {r.pk: r for r in recibos}

        for rid in ids:
            recibo = recibos_map.get(rid)
            if not recibo:
                errors.append({'id': rid, 'reason': 'Recibo no encontrado'})
                continue

            if recibo.sello_dorado_id and recibo.sello_dorado_id != sello.pk:
                errors.append({'id': recibo.pk, 'reason': 'Ya asignado a otro sello'})
                continue

            if not recibo.aprobado_sello_dorado:
                errors.append({'id': recibo.pk, 'reason': 'No aprobado para sello dorado'})
                continue

            # asignar
            recibo.sello_dorado = sello
            recibo.estatus_sello_dorado = 'asignado'
            recibo.notificado_consultoria = True
            recibo.save(update_fields=['sello_dorado', 'estatus_sello_dorado', 'notificado_consultoria'])
            assigned.append(recibo.pk)
            registrar_historial(sello, usuario, 'ASIGNAR', f'Recibo {recibo.numero_recibo} asignado al sello')
            registrar_auditoria(usuario, 'M', f'Asignó el recibo {recibo.numero_recibo} al sello {sello.codigo_sello}', recibo.pk)

        if assigned:
            sello.estado = 'asignado'
            sello.save(update_fields=['estado'])

        return {
            'success': len(assigned) > 0 and len(errors) == 0,
            'assigned_count': len(assigned),
            'assigned_ids': assigned,
            'errors': errors,
            'message': f'Se asignaron {len(assigned)} recibo(s); {len(errors)} con errores.',
        }
