from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
import re

from apps.recibos.models import Recibo
from .models import SelloDorado
from .services import aprobar_recibos_para_sello, asignar_recibos_a_sello, registrar_auditoria, registrar_historial
from django.http import JsonResponse
from django.conf import settings
from django.http import HttpResponse
import csv


def _es_admin(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, 'rol', '') in ['admin', 'superadmin'])


def _es_consultoria(user):
    return user.is_authenticated and getattr(user, 'rol', '') in ['consultoria', 'admin', 'superadmin']


class SelloDoradoListView(LoginRequiredMixin, View):
    def get(self, request):
        if not _es_consultoria(request.user):
            return redirect('home')
        sellos = SelloDorado.objects.all().order_by('-fecha_creacion')
        return render(request, 'sellos/lista.html', {'sellos': sellos})


class SelloDoradoCreateView(LoginRequiredMixin, View):
    def get(self, request):
        if not _es_consultoria(request.user):
            return redirect('home')
        return render(request, 'sellos/crear.html', {})

    def post(self, request):
        if not _es_consultoria(request.user):
            return redirect('home')

        nombre = request.POST.get('nombre', '').strip()
        region = request.POST.get('region', '').strip()
        observaciones = request.POST.get('observaciones', '').strip()

        if not nombre:
            messages.error(request, 'Debe indicar un nombre para el sello.')
            return redirect('sellos:crear')

        sello = SelloDorado.objects.create(
            nombre=nombre,
            region=region,
            observaciones=observaciones,
            creado_por=request.user,
        )

        registrar_historial(sello, request.user, 'CREAR', 'Sello creado por Consultoría')
        registrar_auditoria(request.user, 'C', f'Creó el sello {sello.codigo_sello}', sello.pk)

        messages.success(request, f'Sello creado correctamente: {sello.codigo_sello}')
        return redirect('sellos:detalle', pk=sello.pk)


class SelloDoradoDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        if not _es_consultoria(request.user):
            return redirect('home')
        sello = get_object_or_404(SelloDorado, pk=pk)
        recibos = Recibo.objects.filter(sello_dorado=sello).order_by('-fecha_creacion')
        # recibos disponibles para asignación: aprobados, no anulados y sin sello asignado
        qs_disponibles = Recibo.objects.filter(aprobado_sello_dorado=True, anulado=False, sello_dorado__isnull=True).order_by('-fecha_aprobacion_sello')
        recibos_disponibles = qs_disponibles[:500]

        # diagnósticos: contadores para ayudar a identificar por qué no aparecen recibos
        total_aprobados = Recibo.objects.filter(aprobado_sello_dorado=True).count()
        aprobados_sin_sello = qs_disponibles.count()
        aprobados_asignados = Recibo.objects.filter(aprobado_sello_dorado=True, sello_dorado__isnull=False).count()

        return render(request, 'sellos/detalle.html', {
            'sello': sello,
            'recibos': recibos,
            'recibos_disponibles': recibos_disponibles,
            'diagnostico': {
                'total_aprobados': total_aprobados,
                'aprobados_sin_sello': aprobados_sin_sello,
                'aprobados_asignados': aprobados_asignados,
            }
        })


class AdministracionRecibosView(LoginRequiredMixin, View):
    def get(self, request):
        if not _es_admin(request.user):
            return redirect('home')
        recibos = Recibo.objects.filter(anulado=False, aprobado_sello_dorado=False).order_by('-fecha_creacion')
        return render(request, 'sellos/administracion.html', {'recibos': recibos})


class PanelConsultoriaView(LoginRequiredMixin, View):
    def get(self, request):
        if not _es_consultoria(request.user):
            return redirect('home')

        estado_filter = request.GET.get('estado', '').strip()
        region_filter = request.GET.get('region', '').strip()
        region_group = request.GET.get('region_group', '').strip()

        recibos_aprobados = Recibo.objects.filter(aprobado_sello_dorado=True)
        sellos = SelloDorado.objects.all().order_by('-fecha_creacion')

        # Filtrado por estatus simple
        if estado_filter:
            recibos_aprobados = recibos_aprobados.filter(estatus_sello_dorado=estado_filter)

        # Soporte para grupos de regiones definidos en settings: SELLOS_REGION_GROUPS
        region_states = []
        if region_group:
            groups = getattr(settings, 'SELLOS_REGION_GROUPS', {})
            region_states = groups.get(region_group, [])

        if region_filter:
            sellos = sellos.filter(region__icontains=region_filter)
            recibos_aprobados = recibos_aprobados.filter(sello_dorado__region__icontains=region_filter)

        # Si se seleccionó un grupo, filtrar por estados asociados
        if region_states:
            sellos = sellos.filter(region__in=region_states)
            recibos_aprobados = recibos_aprobados.filter(sello_dorado__region__in=region_states)

        # Contador de nuevos recibos aprobados no notificados a Consultoría
        nuevos_count = Recibo.objects.filter(aprobado_sello_dorado=True, notificado_consultoria=False).count()

        return render(request, 'sellos/panel_consultoria.html', {
            'recibos_aprobados': recibos_aprobados.order_by('-fecha_aprobacion_sello', '-fecha_creacion'),
            'sellos': sellos,
            'estado_filter': estado_filter,
            'region_filter': region_filter,
            'region_group': region_group,
            'nuevos_count': nuevos_count,
        })


def export_recibos_csv(request):
    if not _es_consultoria(request.user):
        return redirect('home')

    estado_filter = request.GET.get('estado', '').strip()
    region_filter = request.GET.get('region', '').strip()
    region_group = request.GET.get('region_group', '').strip()

    qs = Recibo.objects.filter(aprobado_sello_dorado=True)
    if estado_filter:
        qs = qs.filter(estatus_sello_dorado=estado_filter)

    # expand region_group
    region_states = []
    if region_group:
        groups = getattr(settings, 'SELLOS_REGION_GROUPS', {})
        region_states = groups.get(region_group, [])

    if region_filter:
        qs = qs.filter(estado__icontains=region_filter)
    if region_states:
        qs = qs.filter(estado__in=region_states)

    # preparar CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="recibos_sellos.csv"'
    writer = csv.writer(response)
    writer.writerow(['numero_recibo', 'nombre', 'estado', 'estatus_sello_dorado', 'sello_codigo'])
    for r in qs.order_by('-fecha_aprobacion_sello'):
        writer.writerow([r.numero_recibo, r.nombre, r.estado, r.estatus_sello_dorado, r.sello_dorado.codigo_sello if r.sello_dorado else ''])

    return response


@login_required
def aprobar_recibos_view(request):
    if not _es_admin(request.user):
        return redirect('home')

    recibo_ids = request.POST.getlist('recibo_ids')
    if not recibo_ids:
        messages.error(request, 'No seleccionó recibos para aprobar.')
        return redirect('sellos:administracion')

    recibos = aprobar_recibos_para_sello(recibo_ids, request.user)

    messages.success(request, f'Se aprobaron {recibos.count()} recibo(s).')
    return redirect('sellos:administracion')


@login_required
def asignar_recibos_view(request):
    if not _es_consultoria(request.user):
        return redirect('home')

    sello_id = request.POST.get('sello_id')
    # aceptar tanto listas de inputs (checkboxes) como textarea con saltos de línea o comas
    recibo_ids_raw = request.POST.getlist('recibo_ids')
    if len(recibo_ids_raw) == 1:
        raw = recibo_ids_raw[0] or ''
        # separar por nuevas líneas o comas si viene en un solo string
        if '\n' in raw or ',' in raw:
            parts = [p.strip() for p in re.split('[,\n]+', raw) if p.strip()]
            recibo_ids = parts
        else:
            recibo_ids = [raw] if raw else []
    else:
        recibo_ids = [r for r in recibo_ids_raw if r]

    if not sello_id:
        messages.error(request, 'Debe seleccionar un sello.')
        return redirect('sellos:lista')

    sello = get_object_or_404(SelloDorado, pk=sello_id)

    # soporte: si no se recibieron ids, permitir asignación por región (fallback)
    if not recibo_ids:
        region_param = request.POST.get('region', '').strip()
        if region_param:
            qs = Recibo.objects.filter(aprobado_sello_dorado=True, anulado=False, sello_dorado__isnull=True, estado__icontains=region_param)
            recibo_ids = list(qs.values_list('pk', flat=True))

    if not recibo_ids:
        messages.error(request, 'Debe seleccionar al menos un recibo o indicar una región.')
        return redirect('sellos:detalle', pk=sello.pk)

    resultado = asignar_recibos_a_sello(sello, recibo_ids, request.user)
    # Mostrar mensajes detallados según resultado
    if resultado.get('assigned_count', 0) > 0:
        messages.success(request, f"Se asignaron {resultado.get('assigned_count')} recibo(s). IDs: {', '.join(str(i) for i in resultado.get('assigned_ids', []))}")

    if resultado.get('errors'):
        # construir mensaje de errores limitado
        errores = [f"{e['id']}: {e['reason']}" for e in resultado.get('errors')][:10]
        messages.error(request, f"Hubo {len(resultado.get('errors'))} error(es): " + '; '.join(errores))

    return redirect('sellos:detalle', pk=sello.pk)


@login_required
def marcar_recibos_leidos_view(request):
    """Marca recibos como notificados/leídos por Consultoría.

    Acepta POST con 'recibo_ids' (lista o textarea) o 'region' para marcar por región.
    Devuelve JSON con conteo marcado.
    """
    if not _es_consultoria(request.user):
        return JsonResponse({'success': False, 'message': 'Acceso denegado'}, status=403)

    recibo_ids_raw = request.POST.getlist('recibo_ids')
    recibo_ids = []
    if recibo_ids_raw:
        if len(recibo_ids_raw) == 1:
            raw = recibo_ids_raw[0] or ''
            if '\n' in raw or ',' in raw:
                parts = [p.strip() for p in re.split('[,\n]+', raw) if p.strip()]
                recibo_ids = parts
            else:
                recibo_ids = [raw] if raw else []
        else:
            recibo_ids = [r for r in recibo_ids_raw if r]

    if not recibo_ids:
        region_param = request.POST.get('region', '').strip()
        if region_param:
            qs = Recibo.objects.filter(aprobado_sello_dorado=True, notificado_consultoria=False, estado__icontains=region_param)
            updated = qs.update(notificado_consultoria=True)
            # registrar auditoría general
            registrar_auditoria(request.user, 'M', f'Marcó {updated} recibo(s) como leídos por región {region_param}')
            return JsonResponse({'success': True, 'marked': updated})

    # marcar por ids
    if recibo_ids:
        qs = Recibo.objects.filter(pk__in=recibo_ids)
        updated = qs.update(notificado_consultoria=True)
        for pk in qs.values_list('pk', flat=True):
            registrar_auditoria(request.user, 'M', f'Marcó recibo {pk} como leído', pk)
        return JsonResponse({'success': True, 'marked': updated})

    return JsonResponse({'success': False, 'message': 'No se recibieron parámetros válidos'})


@login_required
def cambiar_estatus_sello_view(request, pk):
    if not _es_consultoria(request.user):
        return redirect('home')

    sello = get_object_or_404(SelloDorado, pk=pk)
    nuevo_estado = request.POST.get('estado')

    if nuevo_estado in dict(SelloDorado.ESTADO_CHOICES):
        sello.estado = nuevo_estado
        sello.save(update_fields=['estado'])
        registrar_historial(sello, request.user, 'ESTADO', f'Cambió el estado a {nuevo_estado}')
        registrar_auditoria(request.user, 'M', f'Cambió el estado del sello {sello.codigo_sello} a {nuevo_estado}', sello.pk)
        messages.success(request, 'Estatus actualizado correctamente.')

    return redirect('sellos:detalle', pk=sello.pk)
