import logging
import os
import uuid
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Count, F
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.territorio.models import Comuna, Estado, Municipio, Parroquia

from .forms import (
    EstatusDocumentoForm,
    ExpedienteDashboardFilterForm,
    ExpedienteForm,
    TitularForm,
)
from .models import ArchivoExpediente, EstatusDocumento, Expediente, Titular


logger = logging.getLogger(__name__)

PAGE_SIZE_OPTIONS = (10, 25, 50, 100)
DEFAULT_PAGE_SIZE = 10


def requires_permissions(*permissions):
    def decorator(view_func):
        protected_view = permission_required(
            permissions,
            raise_exception=True,
        )(view_func)
        return login_required(protected_view)

    return decorator


def administrator_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if (
            request.user.is_superuser
            or request.user.rol in ('admin', 'superadmin')
        ):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied

    return wrapped_view


document_access_required = requires_permissions('users.ver_gestor_documental')
catalog_access_required = requires_permissions(
    'users.ver_gestor_documental',
    'users.gestionar_catalogos_documentales',
)


def _apply_filters(queryset, form):
    if not form.is_valid():
        return queryset.none()

    filters = form.cleaned_data
    if filters.get('estado'):
        queryset = queryset.filter(estado=filters['estado'])
    if filters.get('estatus'):
        queryset = queryset.filter(estatus=filters['estatus'])
    if filters.get('titular'):
        queryset = queryset.filter(titular=filters['titular'])
    if filters.get('fecha_desde'):
        queryset = queryset.filter(fecha_registro__gte=filters['fecha_desde'])
    if filters.get('fecha_hasta'):
        queryset = queryset.filter(fecha_registro__lte=filters['fecha_hasta'])
    return queryset


def _chart_data(
    queryset,
    field,
    limit=None,
    newest_first=False,
    most_common=False,
):
    grouped_queryset = queryset.values(label=F(field)).annotate(total=Count('pk'))
    if newest_first:
        grouped_queryset = grouped_queryset.order_by('-label')
    elif most_common:
        grouped_queryset = grouped_queryset.order_by('-total', 'label')
    else:
        grouped_queryset = grouped_queryset.order_by('label')
    if limit is not None:
        grouped_queryset = grouped_queryset[:limit]
    grouped = list(grouped_queryset)
    maximum = max((item['total'] for item in grouped), default=0)
    for item in grouped:
        item['porcentaje'] = round(item['total'] * 100 / maximum) if maximum else 0
    return grouped


def _guardar_archivos(expediente, archivos):
    nombres_guardados = []
    try:
        for archivo in archivos:
            nombre_original = os.path.basename(archivo.name.replace('\\', '/'))[:255]
            adjunto = ArchivoExpediente(
                expediente=expediente,
                nombre_original=nombre_original,
            )
            nombre_privado = f'{uuid.uuid4().hex}.pdf'
            adjunto.archivo.save(nombre_privado, archivo, save=False)
            nombres_guardados.append(adjunto.archivo.name)
            adjunto.save()
    except Exception:
        storage = ArchivoExpediente._meta.get_field('archivo').storage
        for nombre in nombres_guardados:
            storage.delete(nombre)
        raise


@document_access_required
def dashboard(request):
    filtros = ExpedienteDashboardFilterForm(request.GET)
    registros = Expediente.objects.select_related(
        'estado',
        'municipio',
        'parroquia',
        'comuna',
        'titular',
        'estatus',
    )
    registros_filtrados = _apply_filters(registros, filtros)
    total = registros_filtrados.count()
    por_estado = _chart_data(registros_filtrados, 'estado__nombre')
    por_estatus = _chart_data(registros_filtrados, 'estatus__nombre')
    por_titular = _chart_data(
        registros_filtrados,
        'titular__nombre',
        limit=8,
        most_common=True,
    )
    por_fecha = _chart_data(
        registros_filtrados,
        'fecha_registro',
        limit=10,
        newest_first=True,
    )
    recientes = registros_filtrados[:10]

    return render(request, 'gestion_documental/dashboard.html', {
        'filtros': filtros,
        'total_expedientes': total,
        'por_estado': por_estado,
        'por_estatus': por_estatus,
        'por_titular': por_titular,
        'por_fecha': por_fecha,
        'expedientes_recientes': recientes,
    })


@document_access_required
def lista_expedientes(request):
    filtros = ExpedienteDashboardFilterForm(request.GET)
    page_size_value = request.GET.get('per_page', str(DEFAULT_PAGE_SIZE))
    try:
        per_page = int(page_size_value)
    except (TypeError, ValueError):
        per_page = DEFAULT_PAGE_SIZE
        messages.warning(
            request,
            f'Tamaño de página inválido. Se utilizarán {DEFAULT_PAGE_SIZE} registros.',
        )
    if per_page not in PAGE_SIZE_OPTIONS:
        per_page = DEFAULT_PAGE_SIZE
        messages.warning(
            request,
            f'El tamaño debe ser uno de {", ".join(map(str, PAGE_SIZE_OPTIONS))}. '
            f'Se utilizarán {DEFAULT_PAGE_SIZE} registros.',
        )

    registros = Expediente.objects.select_related(
        'estado',
        'municipio',
        'parroquia',
        'titular',
        'estatus',
    )
    registros = _apply_filters(registros, filtros)
    paginator = Paginator(registros, per_page)
    pagina = paginator.get_page(request.GET.get('page'))
    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_params['per_page'] = str(per_page)
    return render(request, 'gestion_documental/lista.html', {
        'filtros': filtros,
        'pagina': pagina,
        'per_page': per_page,
        'page_size_options': PAGE_SIZE_OPTIONS,
        'query_params': query_params,
    })


def _render_expediente_form(request, form, titulo, expediente=None):
    return render(request, 'gestion_documental/expediente_form.html', {
        'form': form,
        'titulo': titulo,
        'expediente': expediente,
    })


@document_access_required
def crear_expediente(request):
    form = ExpedienteForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        archivos = form.cleaned_data['archivos']
        try:
            with transaction.atomic():
                expediente = form.save()
                _guardar_archivos(expediente, archivos)
        except DatabaseError:
            logger.exception('No se pudo guardar el expediente documental.')
            messages.error(
                request,
                'No fue posible guardar el expediente. Verifica los datos e inténtalo nuevamente.',
            )
        else:
            messages.success(
                request,
                f'Expediente {expediente.codigo} registrado correctamente.',
            )
            return redirect('gestion_documental:detalle', pk=expediente.pk)
    return _render_expediente_form(request, form, 'Registrar expediente')


@document_access_required
def detalle_expediente(request, pk):
    expediente = get_object_or_404(
        Expediente.objects.select_related(
            'estado',
            'municipio',
            'parroquia',
            'comuna',
            'titular',
            'estatus',
        ).prefetch_related('archivos'),
        pk=pk,
    )
    return render(request, 'gestion_documental/detalle.html', {
        'expediente': expediente,
    })


@document_access_required
def editar_expediente(request, pk):
    expediente = get_object_or_404(Expediente, pk=pk)
    form = ExpedienteForm(
        request.POST or None,
        request.FILES or None,
        instance=expediente,
    )
    if request.method == 'POST' and form.is_valid():
        archivos = form.cleaned_data['archivos']
        try:
            with transaction.atomic():
                expediente = form.save()
                _guardar_archivos(expediente, archivos)
        except DatabaseError:
            logger.exception(
                'No se pudo actualizar el expediente documental %s.',
                expediente.pk,
            )
            messages.error(request, 'No fue posible actualizar el expediente.')
        else:
            messages.success(request, 'Expediente actualizado correctamente.')
            return redirect('gestion_documental:detalle', pk=expediente.pk)
    return _render_expediente_form(
        request,
        form,
        'Editar expediente',
        expediente,
    )


@document_access_required
def descargar_archivo(request, pk, archivo_id):
    archivo = get_object_or_404(
        ArchivoExpediente.objects.select_related('expediente'),
        pk=archivo_id,
        expediente_id=pk,
    )
    try:
        file_handle = archivo.archivo.open('rb')
    except OSError:
        logger.exception('No se pudo abrir un archivo del expediente %s.', pk)
        messages.error(request, 'El archivo no está disponible en este momento.')
        return redirect('gestion_documental:detalle', pk=pk)

    response = FileResponse(
        file_handle,
        as_attachment=True,
        filename=archivo.nombre_original,
        content_type='application/pdf',
    )
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@document_access_required
@require_POST
def eliminar_archivo(request, pk, archivo_id):
    archivo = get_object_or_404(
        ArchivoExpediente.objects.select_related('expediente'),
        pk=archivo_id,
        expediente_id=pk,
    )
    try:
        archivo.archivo.delete(save=False)
        archivo.delete()
    except OSError:
        logger.exception('No se pudo eliminar un archivo del expediente %s.', pk)
        messages.error(request, 'No fue posible eliminar el archivo.')
    else:
        messages.success(request, 'Archivo eliminado del expediente.')
    return redirect('gestion_documental:detalle', pk=pk)


@catalog_access_required
def lista_titulares(request):
    titulares = Titular.objects.all()
    return render(request, 'gestion_documental/titulares_lista.html', {
        'titulares': titulares,
    })


@catalog_access_required
def crear_titular(request):
    form = TitularForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        titular = form.save()
        messages.success(request, f'Titular "{titular.nombre}" creado.')
        return redirect('gestion_documental:titulares')
    return render(request, 'gestion_documental/catalogo_form.html', {
        'form': form,
        'titulo': 'Nuevo titular',
        'volver_url': reverse('gestion_documental:titulares'),
    })


@catalog_access_required
def editar_titular(request, pk):
    titular = get_object_or_404(Titular, pk=pk)
    form = TitularForm(request.POST or None, instance=titular)
    if request.method == 'POST' and form.is_valid():
        titular = form.save()
        messages.success(request, f'Titular "{titular.nombre}" actualizado.')
        return redirect('gestion_documental:titulares')
    return render(request, 'gestion_documental/catalogo_form.html', {
        'form': form,
        'titulo': 'Editar titular',
        'volver_url': reverse('gestion_documental:titulares'),
    })


@catalog_access_required
def lista_estatus(request):
    estatuses = EstatusDocumento.objects.annotate(
        expedientes_count=Count('expedientes'),
    )
    return render(request, 'gestion_documental/estatus_lista.html', {
        'estatuses': estatuses,
    })


@catalog_access_required
@administrator_required
def crear_estatus(request):
    form = EstatusDocumentoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        estatus = form.save()
        messages.success(request, f'Estatus "{estatus.nombre}" creado.')
        return redirect('gestion_documental:estatus')
    return render(request, 'gestion_documental/catalogo_form.html', {
        'form': form,
        'titulo': 'Nuevo estatus',
        'volver_url': reverse('gestion_documental:estatus'),
    })


@catalog_access_required
@administrator_required
def editar_estatus(request, pk):
    estatus = get_object_or_404(EstatusDocumento, pk=pk)
    form = EstatusDocumentoForm(request.POST or None, instance=estatus)
    if request.method == 'POST' and form.is_valid():
        estatus = form.save()
        messages.success(request, f'Estatus "{estatus.nombre}" actualizado.')
        return redirect('gestion_documental:estatus')
    return render(request, 'gestion_documental/catalogo_form.html', {
        'form': form,
        'titulo': 'Editar estatus',
        'volver_url': reverse('gestion_documental:estatus'),
    })


@catalog_access_required
@administrator_required
@require_POST
def eliminar_estatus(request, pk):
    estatus = get_object_or_404(EstatusDocumento, pk=pk)
    if estatus.expedientes.exists():
        messages.error(
            request,
            'No se puede eliminar este estatus porque tiene expedientes asociados.',
        )
        return redirect('gestion_documental:estatus')

    try:
        with transaction.atomic():
            estatus.delete()
    except IntegrityError:
        messages.error(
            request,
            'No se puede eliminar este estatus porque tiene expedientes asociados.',
        )
    else:
        messages.success(request, f'Estatus "{estatus.nombre}" eliminado.')
    return redirect('gestion_documental:estatus')


@document_access_required
def api_municipios(request, estado_id):
    rows = Municipio.objects.filter(estado_id=estado_id).order_by('nombre')
    return JsonResponse(list(rows.values('id', 'nombre')), safe=False)


@document_access_required
def api_parroquias(request, municipio_id):
    rows = Parroquia.objects.filter(municipio_id=municipio_id).order_by('nombre')
    return JsonResponse(list(rows.values('id', 'nombre')), safe=False)


@document_access_required
def api_comunas(request, parroquia_id):
    rows = Comuna.objects.filter(parroquia_id=parroquia_id).order_by('nombre')
    return JsonResponse(list(rows.values('id', 'nombre')), safe=False)
