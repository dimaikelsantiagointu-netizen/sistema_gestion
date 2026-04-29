import logging
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Count
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import IntegrityError

# Importación de modelos locales
from .models import Beneficiario, DocumentoExpediente, Visita
# Importación de modelos de territorio
from apps.territorio.models import Estado, Municipio, Parroquia, Ciudad, Comuna, UnidadAdscrita

# Configuración del Logger vinculado a la configuración de settings.py
logger_beneficiarios = logging.getLogger('CH_BENEFICIARIOS')

# Función de verificación para acceso administrativo
def es_administrador(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, 'rol', '') in ['admin', 'superadmin'])

# ================================================================
# 1. SECCIÓN: GESTIÓN INTEGRAL DE BENEFICIARIOS (CRUD Y LISTADOS)
# ================================================================

@login_required
def lista_beneficiarios(request):
    query = request.GET.get('q', '').strip()
    estado_id = request.GET.get('estado', '')
    genero = request.GET.get('genero', '')
    discapacidad = request.GET.get('discapacidad', '')
    f_inicio = request.GET.get('fecha_inicio', '')
    f_fin = request.GET.get('fecha_fin', '')

    ha_filtrado = any([query, estado_id, genero, discapacidad, f_inicio, f_fin])
    hoy_local = timezone.localtime(timezone.now()).date()

    if ha_filtrado:
        beneficiarios_list = Beneficiario.objects.select_related(
            'estado', 'municipio', 'parroquia', 'ciudad', 'comuna'
        ).all()
        
        if query:
            beneficiarios_list = beneficiarios_list.filter(
                Q(nombre_completo__icontains=query) | 
                Q(documento_identidad__icontains=query)
            )
        
        if estado_id:
            beneficiarios_list = beneficiarios_list.filter(estado_id=estado_id)
            
        if genero:
            beneficiarios_list = beneficiarios_list.filter(genero=genero)
            
        if discapacidad:
            beneficiarios_list = beneficiarios_list.filter(discapacidad=(discapacidad == '1'))

        if f_inicio:
            beneficiarios_list = beneficiarios_list.filter(fecha_creacion__date__gte=f_inicio)
        
        if f_fin:
            beneficiarios_list = beneficiarios_list.filter(fecha_creacion__date__lte=f_fin)
            
        beneficiarios_list = beneficiarios_list.order_by('-fecha_creacion')
    else:
        beneficiarios_list = Beneficiario.objects.none()

    total_beneficiarios = Beneficiario.objects.count()
    visitas_hoy_count = Visita.objects.filter(fecha_registro__date=hoy_local).count()

    context = {
        'beneficiarios': beneficiarios_list,
        'query': query,
        'f_inicio': f_inicio,
        'f_fin': f_fin,
        'estados': Estado.objects.all().order_by('nombre'),
        'total_beneficiarios': total_beneficiarios,
        'visitas_hoy_count': visitas_hoy_count,
        'ha_filtrado': ha_filtrado,
    }
    return render(request, 'beneficiarios/lista.html', context)

@login_required
def crear_beneficiario(request):
    if request.method == 'POST':
        doc_id = request.POST.get('documento_identidad')
        
        # Validación de duplicados antes de intentar guardar
        if Beneficiario.objects.filter(documento_identidad=doc_id).exists():
            messages.error(request, f"Error: Ya existe un ciudadano registrado con el documento {doc_id}.")
            context = {
                'estados': Estado.objects.all().order_by('nombre'),
                'TIPO_DOC_CHOICES': Beneficiario.TIPO_DOC_CHOICES,
                'GENERO_CHOICES': Beneficiario.GENERO_CHOICES,
                'boton': 'Registrar Ciudadano',
                'datos_previos': request.POST 
            }
            return render(request, 'beneficiarios/formulario.html', context)

        try:
            # Capturamos la fecha de nacimiento y el email
            fecha_nac = request.POST.get('fecha_nacimiento')
            email_val = request.POST.get('email')

            beneficiario = Beneficiario(
                tipo_documento=request.POST.get('tipo_documento'),
                documento_identidad=doc_id,
                nombre_completo=request.POST.get('nombre_completo'),
                
                # NUEVO: Asignación de fecha de nacimiento
                fecha_nacimiento=fecha_nac if fecha_nac else None,
                
                genero=request.POST.get('genero'),
                discapacidad=request.POST.get('discapacidad') == 'on',
                telefono=request.POST.get('telefono'),
                
                # Tratamos el email como opcional (si llega vacío se guarda None)
                email=email_val if email_val else None,
                
                direccion_especifica=request.POST.get('direccion_especifica'),
                
                # Campos territoriales completos
                estado_id=request.POST.get('estado') or None,
                municipio_id=request.POST.get('municipio') or None,
                parroquia_id=request.POST.get('parroquia') or None,
                ciudad_id=request.POST.get('ciudad') or None,
                comuna_id=request.POST.get('comuna') or None,
            )
            beneficiario.save()
            
            logger_beneficiarios.info(f"CIUDADANO REGISTRADO: {beneficiario.nombre_completo} (C.I: {doc_id}) por {request.user.username}")
            messages.success(request, f"Ciudadano {beneficiario.nombre_completo} registrado con éxito.")
            return redirect('beneficiarios:lista')

        except IntegrityError:
            messages.error(request, "Error de integridad: El documento ya está en uso.")
            return redirect('beneficiarios:crear')
        except Exception as e:
            logger_beneficiarios.error(f"Error al crear beneficiario: {str(e)}")
            messages.error(request, f"Error inesperado al guardar: {e}")

    context = {
        'estados': Estado.objects.all().order_by('nombre'),
        'TIPO_DOC_CHOICES': Beneficiario.TIPO_DOC_CHOICES,
        'GENERO_CHOICES': Beneficiario.GENERO_CHOICES,
        'boton': 'Registrar Ciudadano',
    }
    return render(request, 'beneficiarios/formulario.html', context)

@login_required
def editar_beneficiario(request, id):
    beneficiario = get_object_or_404(Beneficiario, id=id)
    if request.method == 'POST':
        try:
            # Captura de datos básicos e identidad
            beneficiario.tipo_documento = request.POST.get('tipo_documento')
            beneficiario.documento_identidad = request.POST.get('documento_identidad')
            beneficiario.nombre_completo = request.POST.get('nombre_completo')
            
            # NUEVO: Actualización de fecha de nacimiento
            fecha_nac = request.POST.get('fecha_nacimiento')
            beneficiario.fecha_nacimiento = fecha_nac if fecha_nac else None
            
            beneficiario.genero = request.POST.get('genero')
            beneficiario.discapacidad = request.POST.get('discapacidad') == 'on'
            beneficiario.telefono = request.POST.get('telefono')
            
            # Email opcional: tratar cadena vacía como None
            email_val = request.POST.get('email')
            beneficiario.email = email_val if email_val else None
            
            beneficiario.direccion_especifica = request.POST.get('direccion_especifica')
            
            # Actualización de la jerarquía territorial
            beneficiario.estado_id = request.POST.get('estado') or None
            beneficiario.municipio_id = request.POST.get('municipio') or None
            beneficiario.parroquia_id = request.POST.get('parroquia') or None
            beneficiario.ciudad_id = request.POST.get('ciudad') or None
            beneficiario.comuna_id = request.POST.get('comuna') or None
            
            beneficiario.save()
            
            logger_beneficiarios.info(f"CIUDADANO ACTUALIZADO: {beneficiario.nombre_completo} por {request.user.username}")
            messages.success(request, "Datos actualizados correctamente.")
            return redirect('beneficiarios:lista')
            
        except Exception as e:
            logger_beneficiarios.error(f"Error al actualizar beneficiario {id}: {str(e)}")
            messages.error(request, f"Error al actualizar: {e}")

    return render(request, 'beneficiarios/formulario.html', {
        'titulo': 'Editar Beneficiario',
        'boton': 'Guardar Cambios',
        'beneficiario': beneficiario,
        'estados': Estado.objects.all().order_by('nombre'),
        'TIPO_DOC_CHOICES': Beneficiario.TIPO_DOC_CHOICES,
        'GENERO_CHOICES': Beneficiario.GENERO_CHOICES,
    })

@login_required
def eliminar_beneficiario(request, id):
    beneficiario = get_object_or_404(Beneficiario, id=id)
    nombre = beneficiario.nombre_completo
    beneficiario.delete()
    logger_beneficiarios.warning(f"CIUDADANO ELIMINADO: {nombre} por {request.user.username}")
    messages.warning(request, f"Beneficiario {nombre} eliminado del sistema.")
    return redirect('beneficiarios:lista')

@login_required
def registrar_visita(request):
    if request.method == 'POST':
        b_id = request.POST.get('beneficiario_id')
        if b_id:
            beneficiario = get_object_or_404(Beneficiario, id=b_id)
            fecha_post = request.POST.get('fecha_registro')
            
            funcionario = request.POST.get('funcionario_atiende')
            # El name del HTML es 'unidad_adscrita'
            unidad_id = request.POST.get('unidad_adscrita') 
            desc_original = request.POST.get('descripcion')

            unidad_obj = None
            if unidad_id and unidad_id.isdigit():
                unidad_obj = UnidadAdscrita.objects.filter(id=unidad_id).first()

            # Aquí es donde estaba el choque de nombres
            Visita.objects.create(
                beneficiario=beneficiario,
                motivo=request.POST.get('motivo'),
                descripcion=desc_original,
                funcionario_atiende=funcionario,
                # IZQUIERDA: Nombre en el Modelo (unidad_administrativa)
                # DERECHA: El objeto que encontramos arriba
                unidad_administrativa=unidad_obj, 
                registrado_por=request.user,
                fecha_registro=fecha_post if fecha_post else timezone.now()
            )
            
            messages.success(request, "Visita registrada correctamente.")
            return redirect('beneficiarios:detalle', id=beneficiario.id)
    
    return render(request, 'beneficiarios/form_visita.html', {
        'motivos': Visita.MOTIVO_CHOICES,
        'current_time': timezone.now(),
        'unidades': UnidadAdscrita.objects.all().order_by('nombre')
    })

@login_required
def detalle_beneficiario(request, id): 
    # Optimizamos la consulta con select_related para traer los nombres de territorio de una vez
    beneficiario = get_object_or_404(
        Beneficiario.objects.select_related('estado', 'municipio', 'parroquia', 'ciudad', 'comuna'), 
        id=id
    ) 
    visitas = beneficiario.visitas.all().order_by('-fecha_registro')
    
    return render(request, 'beneficiarios/detalle.html', {
        'beneficiario': beneficiario,
        'visitas': visitas,
        'titulo_pagina': 'Expediente del Ciudadano'
    })

# ================================================================
# 2. SECCIÓN: ESTADÍSTICAS, EXPORTACIÓN Y CANALES API (AJAX)
# ================================================================

@user_passes_test(es_administrador)
def beneficiarios_estadisticas(request):
    # 1. Capturar parámetros de fecha
    f_inicio = request.GET.get('fecha_inicio')
    f_fin = request.GET.get('fecha_fin')

    # 2. Preparar objetos Q para filtrado dinámico
    filtros_beneficiario = Q()
    filtros_visita = Q()

    if f_inicio:
        # En Beneficiario usamos fecha_creacion
        filtros_beneficiario &= Q(fecha_creacion__date__gte=f_inicio)
        # En Visita usamos fecha_registro
        filtros_visita &= Q(fecha_registro__date__gte=f_inicio)
    if f_fin:
        filtros_beneficiario &= Q(fecha_creacion__date__lte=f_fin)
        filtros_visita &= Q(fecha_registro__date__lte=f_fin)

    # 3. Aplicar filtros a los QuerySets base
    total_beneficiarios = Beneficiario.objects.filter(filtros_beneficiario).count()
    total_visitas = Visita.objects.filter(filtros_visita).count()

    # Estadísticas de Beneficiarios (Filtradas por fecha_creacion)
    visitas_por_estado = Beneficiario.objects.filter(filtros_beneficiario)\
        .values('estado__nombre')\
        .annotate(total=Count('id'))\
        .order_by('-total')

    genero_data = Beneficiario.objects.filter(filtros_beneficiario)\
        .values('genero')\
        .annotate(total=Count('id'))\
        .order_by('-total')

    # Estadísticas de Visitas (Filtradas por fecha_registro)
    gestion_por_operador = Visita.objects.filter(filtros_visita).values(
        'registrado_por__username', 
        'registrado_por__first_name', 
        'registrado_por__last_name'
    ).annotate(total=Count('id')).order_by('-total')

    visitas_por_tipo = Visita.objects.filter(filtros_visita).values('motivo')\
        .annotate(total=Count('id')).order_by('-total')

    # Totales destacados
    estado_top = visitas_por_estado.first() if visitas_por_estado else None
    tipo_top = visitas_por_tipo.first() if visitas_por_tipo else None

    context = {
        'total_beneficiarios': total_beneficiarios,
        'total_visitas': total_visitas,
        'visitas_por_estado': visitas_por_estado,
        'gestion_por_operador': gestion_por_operador,
        'genero_data': genero_data,
        'visitas_por_tipo': visitas_por_tipo,
        'estado_top': estado_top,
        'tipo_top': tipo_top,
        'f_inicio': f_inicio,
        'f_fin': f_fin,
    }
    return render(request, 'beneficiarios/estadisticas_beneficiarios.html', context)

from django.db.models import Q
from django.utils.timezone import now

@login_required
def exportar_excel(request):
    try:
        # 1. Capturar los parámetros con los nombres EXACTOS del HTML
        f_inicio = request.GET.get('fecha_inicio', '').strip()
        f_fin = request.GET.get('fecha_fin', '').strip()
        tipo = request.GET.get('tipo', 'parcial')

        # Verificar permisos para reporte completo
        if tipo == 'completo' and not es_administrador(request.user):
            messages.error(request, "No tienes permisos para exportar el reporte completo de ciudadanos.")
            return redirect('beneficiarios:lista')

        # 2. Construir filtros dinámicos (Igual que en estadísticas)
        filtros_visita = Q()
        filtros_beneficiario = Q()

        if f_inicio and f_inicio != 'None':
            filtros_visita &= Q(fecha_registro__date__gte=f_inicio)
            filtros_beneficiario &= Q(fecha_creacion__date__gte=f_inicio)
        if f_fin and f_fin != 'None':
            filtros_visita &= Q(fecha_registro__date__lte=f_fin)
            filtros_beneficiario &= Q(fecha_creacion__date__lte=f_fin)

        # 3. Crear el libro de Excel
        wb = openpyxl.Workbook()
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        white_font = Font(color="FFFFFF", bold=True, size=11)

        # --- HOJA 1: RESUMEN Y FILTROS ---
        ws_resumen = wb.active
        ws_resumen.title = "Control de Reporte"
        ws_resumen["A1"] = f"SICSI INTU - REPORTE {'COMPLETO' if tipo == 'completo' else 'PARCIAL'}"
        ws_resumen["A1"].font = Font(bold=True, size=14)
        ws_resumen.append([])
        ws_resumen.append(["RANGO DESDE:", f_inicio if f_inicio else "HISTÓRICO"])
        ws_resumen.append(["RANGO HASTA:", f_fin if f_fin else "HOY"])
        ws_resumen.append([])
        ws_resumen.append(["FECHA DE GENERACIÓN:", now().strftime("%d/%m/%Y %H:%M")])

        # --- HOJA 2: VISITAS (EL DETALLE QUE NECESITAS) ---
        ws_vis = wb.create_sheet(title="Detalle de Visitas")
        ws_vis.append(['FECHA REGISTRO', 'CEDULA/RIF', 'NOMBRE COMPLETO', 'TRÁMITE / MOTIVO'])
        
        # Filtramos visitas con la lógica de Q
        visitas_qs = Visita.objects.filter(filtros_visita).select_related('beneficiario').order_by('-fecha_registro')
        
        for v in visitas_qs:
            ws_vis.append([
                v.fecha_registro.strftime('%d/%m/%Y %H:%M'),
                f"{v.beneficiario.tipo_documento}-{v.beneficiario.documento_identidad}",
                v.beneficiario.nombre_completo.upper(),
                v.motivo.upper() if v.motivo else "N/A"
            ])

        # --- HOJA 3: BENEFICIARIOS (Solo para reporte completo) ---
        if tipo == 'completo':
            ws_ben = wb.create_sheet(title="Base de Ciudadanos")
            ws_ben.append(['FECHA REGISTRO', 'IDENTIDAD', 'NOMBRE COMPLETO', 'TELÉFONO'])
            
            beneficiarios_qs = Beneficiario.objects.filter(filtros_beneficiario).order_by('-fecha_creacion')
            for b in beneficiarios_qs:
                ws_ben.append([
                    b.fecha_creacion.strftime('%d/%m/%Y') if b.fecha_creacion else "N/A",
                    f"{b.tipo_documento}-{b.documento_identidad}",
                    b.nombre_completo.upper(),
                    b.telefono or "N/A"
                ])

        # 4. Estilos y Ajuste de columnas
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(min_row=1, max_row=1):
                if sheet.title != "Control de Reporte":
                    for cell in row:
                        cell.fill = header_fill
                        cell.font = white_font
            
            for col in sheet.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except: pass
                sheet.column_dimensions[column].width = max_length + 4

        # 5. Envío de respuesta
        tipo_str = "COMPLETO" if tipo == "completo" else "PARCIAL"
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="Reporte_INTU_{tipo_str}_{now().strftime("%d%m%Y")}.xlsx"'
        wb.save(response)
        return response

    except Exception as e:
        logger_beneficiarios.error(f"Error en Excel: {str(e)}")
        messages.error(request, f"Error al generar Excel: {str(e)}")
        return redirect('beneficiarios:lista')

# APIs TERRITORIALES PARA CARGA DINÁMICA (AJAX)
def api_get_municipios(request, estado_id):
    municipios = Municipio.objects.filter(estado_id=estado_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(municipios), safe=False)

def api_get_parroquias(request, municipio_id):
    parroquias = Parroquia.objects.filter(municipio_id=municipio_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(parroquias), safe=False)

def api_get_ciudades(request, estado_id):
    ciudades = Ciudad.objects.filter(estado_id=estado_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(ciudades), safe=False)

def api_get_comunas(request, parroquia_id):
    comunas = Comuna.objects.filter(parroquia_id=parroquia_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(comunas), safe=False)

@login_required
def buscar_beneficiario(request):
    cedula = request.GET.get('cedula', '')
    try:
        b = Beneficiario.objects.get(documento_identidad=cedula)
        return JsonResponse({
            'encontrado': True,
            'id': b.id,
            'nombre': b.nombre_completo,
            'tipo_doc': b.tipo_documento
        })
    except Beneficiario.DoesNotExist:
        return JsonResponse({'encontrado': False})

@login_required
def buscar_beneficiario_api(request):
    query = request.GET.get('cedula', '').strip()
    results = []
    if len(query) >= 2:
        beneficiarios = Beneficiario.objects.filter(
            Q(documento_identidad__icontains=query) | 
            Q(nombre_completo__icontains=query)
        )[:5]  
        for b in beneficiarios:
            results.append({
                'id': b.id,
                'nombre': b.nombre_completo.upper(),
                'cedula': b.documento_identidad,
                'tipo_doc': b.tipo_documento
            })
    return JsonResponse({'encontrado': len(results) > 0, 'results': results})

def check_documento(request):
    doc_id = request.GET.get('doc_id')
    exists = Beneficiario.objects.filter(documento_identidad=doc_id).exists()
    return JsonResponse({'exists': exists})

# ================================================================
# 3. SECCIÓN: ARCHIVO CENTRAL Y EXPEDIENTES DIGITALES
# ================================================================

def gestion_documental(request):
    from apps.personal.models import Personal  # Importación local para evitar circularidad
    query = request.GET.get('q', '').strip()
    tipo_archivo = request.GET.get('tipo', 'beneficiario')
    
    beneficiarios_list = None
    personal_list = None
    total_registros = 0

    if tipo_archivo == 'personal':
        personal_list = Personal.objects.all().order_by('apellidos')
        if query:
            personal_list = personal_list.filter(
                Q(nombres__icontains=query) | Q(apellidos__icontains=query) | Q(cedula__icontains=query)
            )
        total_registros = personal_list.count()
    else:
        beneficiarios_list = Beneficiario.objects.all().order_by('nombre_completo')
        if query:
            beneficiarios_list = beneficiarios_list.filter(
                Q(nombre_completo__icontains=query) | Q(documento_identidad__icontains=query)
            )
        total_registros = beneficiarios_list.count()

    return render(request, 'beneficiarios/gestion_documental.html', {
        'beneficiarios': beneficiarios_list,
        'personal_list': personal_list,
        'query': query,
        'total_beneficiarios': total_registros,
        'tipo_archivo': tipo_archivo,
    })

@login_required
def expediente_beneficiario(request, id):
    beneficiario = get_object_or_404(Beneficiario, id=id)
    if request.method == 'POST':
        archivos_subidos = request.FILES.getlist('archivos')
        nombre_descriptivo = request.POST.get('nombre_documento')
        MAX_FILE_SIZE = 5 * 1024 * 1024 

        if not archivos_subidos:
            messages.error(request, "No seleccionaste archivos.")
        else:
            for f in archivos_subidos:
                if f.size <= MAX_FILE_SIZE:
                    DocumentoExpediente.objects.create(
                        beneficiario=beneficiario,
                        archivo=f,
                        nombre_documento=nombre_descriptivo or f.name
                    )
                else:
                    messages.error(request, f"El archivo {f.name} excede los 5MB.")
            messages.success(request, "Documentación cargada correctamente.")
            return redirect('beneficiarios:expediente', id=beneficiario.id)

    documentos = beneficiario.documentos.all()
    return render(request, 'beneficiarios/expediente.html', {
        'beneficiario': beneficiario,
        'documentos': documentos
    })

@login_required
def eliminar_documento(request, doc_id):
    documento = get_object_or_404(DocumentoExpediente, id=doc_id)
    b_id = documento.beneficiario.id  
    if documento.archivo:
        documento.archivo.delete(save=False)
    documento.delete()
    messages.success(request, "Archivo eliminado del expediente.")
    return redirect('beneficiarios:expediente', id=b_id)

def expediente_detalle(request, pk):
    beneficiario = get_object_or_404(Beneficiario, pk=pk)
    return render(request, 'beneficiarios/expediente_archivo.html', {'beneficiario': beneficiario})