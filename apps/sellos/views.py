from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import CharField
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
import re

from apps.recibos.models import Recibo
from .models import SelloDorado
from .services import aprobar_recibos_para_sello, asignar_recibos_a_sello, registrar_auditoria, registrar_historial
from django.http import JsonResponse
from django.conf import settings
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from urllib.parse import urlparse
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

        # diagnóstico simple: total de recibos asignados a este sello
        total_asignados = recibos.count()

        return render(request, 'sellos/detalle.html', {
            'sello': sello,
            'recibos': recibos,
            'recibos_disponibles': recibos_disponibles,
            'diagnostico': {
                'total_asignados': total_asignados,
            }
        })


@login_required
def imprimir_sello_view(request, pk):
    if not _es_consultoria(request.user):
        return redirect('home')

    sello = get_object_or_404(SelloDorado, pk=pk)
    recibos = Recibo.objects.filter(sello_dorado=sello).order_by('-fecha_creacion')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="sello_{sello.codigo_sello}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=0.6 * inch, leftMargin=0.6 * inch, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=16, textColor=colors.HexColor('#1f4e79'), leading=20)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#d12d2d'), leading=14)
    normal_style = ParagraphStyle('Normal', parent=styles['BodyText'], fontName='Helvetica', fontSize=10, leading=12)
    small_style = ParagraphStyle('Small', parent=styles['BodyText'], fontName='Helvetica', fontSize=9, leading=11, textColor=colors.HexColor('#6b7280'))
    bold_style = ParagraphStyle('Bold', parent=styles['BodyText'], fontName='Helvetica-Bold', fontSize=10, leading=12)

    elements = []
    elements.append(Paragraph(sello.codigo_sello, title_style))
    elements.append(Paragraph(sello.nombre, subtitle_style))
    elements.append(Paragraph('Documento de exportación del sello dorado y sus recibos vinculados.', small_style))
    elements.append(Spacer(1, 0.15 * inch))

    data = [
        ['Región / Jurisdicción', sello.region or 'No especificada'],
        ['Estado', sello.get_estado_display()],
        ['Fecha de generación', sello.fecha_creacion.strftime('%d/%m/%Y %H:%M')],
        ['Última actualización', sello.fecha_actualizacion.strftime('%d/%m/%Y %H:%M')],
    ]
    table = Table(data, colWidths=[2.2 * inch, 4.3 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#6b7280')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.15 * inch))

    elements.append(Paragraph('Observaciones', bold_style))
    elements.append(Paragraph(sello.observaciones or 'Sin observaciones registradas.', normal_style))
    elements.append(Spacer(1, 0.2 * inch))

    elements.append(Paragraph('Recibos asociados', bold_style))
    table_data = [['Nº Recibo', 'Contribuyente', 'Estado', 'Estatus Sello']]
    for recibo in recibos:
        table_data.append([
            f"{recibo.numero_recibo:09d}",
            recibo.nombre or '-',
            recibo.estado or 'Sin estado',
            recibo.get_estatus_sello_dorado_display() or '-',
        ])
    if not recibos:
        table_data.append(['-', '-', 'No hay recibos vinculados a este sello.', '-'])

    table_recibos = Table(table_data, repeatRows=1, colWidths=[1.1 * inch, 2.2 * inch, 1.3 * inch, 1.5 * inch])
    table_recibos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table_recibos)

    doc.build(elements)
    return response


class AdministracionRecibosView(LoginRequiredMixin, View):
    def get(self, request):
        if not _es_admin(request.user):
            return redirect('home')

        numero_filter = request.GET.get('numero_recibo', '').strip()
        contribuyente_filter = request.GET.get('contribuyente', '').strip()
        estado_filter = request.GET.get('estado', '').strip()

        qs_base = Recibo.objects.filter(anulado=False, aprobado_sello_dorado=False)
        estados_disponibles = list(
            qs_base.exclude(estado__isnull=True)
            .exclude(estado='')
            .values_list('estado', flat=True)
            .distinct()
            .order_by('estado')
        )
        qs = qs_base.order_by('-fecha_creacion')

        if numero_filter:
            qs = qs.annotate(numero_recibo_text=Cast('numero_recibo', output_field=CharField())).filter(numero_recibo_text__icontains=numero_filter)

        if contribuyente_filter:
            qs = qs.filter(nombre__icontains=contribuyente_filter)

        if estado_filter:
            qs = qs.filter(estado__icontains=estado_filter)

        paginator = Paginator(qs, 20)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        referer = request.META.get('HTTP_REFERER', '')
        volver_url = None
        if referer:
            try:
                referer_parsed = urlparse(referer)
            except ValueError:
                referer_parsed = None
            if referer_parsed and referer_parsed.path != request.path:
                volver_url = referer

        return render(request, 'sellos/administracion.html', {
            'recibos': page_obj.object_list,
            'page_obj': page_obj,
            'paginator': paginator,
            'numero_filter': numero_filter,
            'contribuyente_filter': contribuyente_filter,
            'estado_filter': estado_filter,
            'estados_disponibles': estados_disponibles,
            'volver_url': volver_url,
        })


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
