import logging
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Count
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Beneficiario, DocumentoExpediente, Visita
from django.core.paginator import Paginator
from apps.territorio.models import Estado, Municipio, Parroquia
from django.db import IntegrityError

logger = logging.getLogger(__name__)

# --- 1. GESTIÓN DE BENEFICIARIOS ---

@login_required
def lista_beneficiarios(request):
    # 1. Obtener parámetros de búsqueda
    query = request.GET.get('q', '').strip()
    estado_id = request.GET.get('estado', '')
    genero = request.GET.get('genero', '')
    discapacidad = request.GET.get('discapacidad', '')

    # 2. Lógica de "No mostrar nada si no hay filtro"
    ha_filtrado = any([query, estado_id, genero, discapacidad])

    # 3. FILTRADO LOCAL DE TIEMPO (Solución al error de visitas hoy)
    # Obtenemos la fecha exacta del lugar donde estás (Venezuela/Local)
    hoy_local = timezone.localtime(timezone.now()).date()

    if ha_filtrado:
        # Usamos select_related para traer los nombres de estados de una vez y no saturar
        beneficiarios_list = Beneficiario.objects.select_related('estado', 'municipio', 'parroquia').all()
        
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
            # Convertimos el string '1'/'0' a Booleano real
            beneficiarios_list = beneficiarios_list.filter(discapacidad=(discapacidad == '1'))
            
        beneficiarios_list = beneficiarios_list.order_by('nombre_completo')
    else:
        beneficiarios_list = Beneficiario.objects.none()

    # 4. CONTEOS PARA KPI
    total_beneficiarios = Beneficiario.objects.count()
    # Usamos hoy_local para asegurar que la visita aparezca apenas se registre
    visitas_hoy_count = Visita.objects.filter(fecha_registro__date=hoy_local).count()

    context = {
        'beneficiarios': beneficiarios_list,
        'query': query,
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
        
        # 1. VERIFICACIÓN DE UNICIDAD: Evita el IntegrityError
        if Beneficiario.objects.filter(documento_identidad=doc_id).exists():
            messages.error(request, f"Error: Ya existe un ciudadano registrado con el documento {doc_id}.")
            # Retornamos el render con los datos actuales para que el usuario no pierda lo que escribió
            context = {
                'estados': Estado.objects.all().order_by('nombre'),
                'TIPO_DOC_CHOICES': Beneficiario.TIPO_DOC_CHOICES,
                'GENERO_CHOICES': Beneficiario.GENERO_CHOICES,
                'boton': 'Registrar Ciudadano',
                'datos_previos': request.POST # Para recuperar datos si tu template lo permite
            }
            return render(request, 'beneficiarios/formulario.html', context)

        try:
            # 2. PROCESO DE GUARDADO (Ya corregido con los _id)
            beneficiario = Beneficiario(
                tipo_documento=request.POST.get('tipo_documento'),
                documento_identidad=doc_id,
                nombre_completo=request.POST.get('nombre_completo'),
                genero=request.POST.get('genero'),
                discapacidad=request.POST.get('discapacidad') == 'on',
                telefono=request.POST.get('telefono'),
                email=request.POST.get('email'),
                direccion_especifica=request.POST.get('direccion_especifica'),
                estado_id=request.POST.get('estado') or None,
                municipio_id=request.POST.get('municipio') or None,
                parroquia_id=request.POST.get('parroquia') or None,
                ciudad_id=request.POST.get('ciudad') or None,
                comuna_id=request.POST.get('comuna') or None,
            )
            beneficiario.save()
            messages.success(request, f"Ciudadano {beneficiario.nombre_completo} registrado con éxito.")
            return redirect('beneficiarios:lista')

        except IntegrityError:
            # Una segunda capa de seguridad por si acaso
            messages.error(request, "Error de integridad: El documento ya está en uso.")
            return redirect('beneficiarios:crear')

    # Para el GET
    context = {
        'estados': Estado.objects.all().order_by('nombre'),
        'TIPO_DOC_CHOICES': Beneficiario.TIPO_DOC_CHOICES,
        'GENERO_CHOICES': Beneficiario.GENERO_CHOICES,
        'boton': 'Registrar Ciudadano',
    }
    return render(request, 'beneficiarios/formulario.html', context)

#--FUNCIONES AUXILIARES PARA CARGA DINÁMICA DE MUNICIPIOS Y PARROQUIAS EN EL FORMULARIO ---
def api_get_municipios(request, estado_id):
    municipios = Municipio.objects.filter(estado_id=estado_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(municipios), safe=False)

def api_get_parroquias(request, municipio_id):
    parroquias = Parroquia.objects.filter(municipio_id=municipio_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(parroquias), safe=False)
#-------------------------

@login_required
def editar_beneficiario(request, id):
    beneficiario = get_object_or_404(Beneficiario, id=id)
    if request.method == 'POST':
        try:
            beneficiario.tipo_documento = request.POST.get('tipo_documento')
            beneficiario.documento_identidad = request.POST.get('documento_identidad')
            beneficiario.nombre_completo = request.POST.get('nombre_completo')
            beneficiario.telefono = request.POST.get('telefono')
            beneficiario.email = request.POST.get('email')
            beneficiario.direccion = request.POST.get('direccion')
            beneficiario.save()
            messages.success(request, "Datos actualizados correctamente.")
            return redirect('beneficiarios:lista')
        except Exception as e:
            messages.error(request, f"Error al actualizar: {e}")

    return render(request, 'beneficiarios/formulario.html', {
        'titulo': 'Editar Beneficiario',
        'boton': 'Guardar Cambios',
        'beneficiario': beneficiario
    })

@login_required
def eliminar_beneficiario(request, id):
    beneficiario = get_object_or_404(Beneficiario, id=id)
    nombre = beneficiario.nombre_completo
    beneficiario.delete()
    messages.warning(request, f"Beneficiario {nombre} eliminado.")
    return redirect('beneficiarios:lista')

# --- 2. EXPEDIENTE DIGITAL ---

@login_required
def expediente_beneficiario(request, id):
    beneficiario = get_object_or_404(Beneficiario, id=id)
    
    if request.method == 'POST':
        archivos_subidos = request.FILES.getlist('archivos')
        nombre_descriptivo = request.POST.get('nombre_documento')
        MAX_FILE_SIZE = 5 * 1024 * 1024 # 5MB

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
            
            messages.success(request, "Proceso de carga finalizado.")
            # Asegúrate de pasar 'id' aquí también en el redirect
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
    messages.success(request, "Archivo eliminado correctamente.")
    
    return redirect('beneficiarios:expediente', id=b_id)

# --- 3. GESTIÓN DE VISITAS ---

@login_required
def registrar_visita(request):
    if request.method == 'POST':
        b_id = request.POST.get('beneficiario_id')
        if b_id:
            beneficiario = get_object_or_404(Beneficiario, id=b_id)
            fecha_post = request.POST.get('fecha_registro')
            
            Visita.objects.create(
                beneficiario=beneficiario,
                motivo=request.POST.get('motivo'),
                descripcion=request.POST.get('descripcion'),
                registrado_por=request.user,
                fecha_registro=fecha_post if fecha_post else timezone.now()
            )
            
            messages.success(request, "Visita registrada correctamente.")
            
            return redirect('beneficiarios:detalle', id=beneficiario.id)
    
    return render(request, 'beneficiarios/form_visita.html', {
        'motivos': Visita.MOTIVO_CHOICES,
        'current_time': timezone.now() 
    })

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
def detalle_beneficiario(request, id): 
    beneficiario = get_object_or_404(Beneficiario, id=id) 
    visitas = beneficiario.visitas.all().order_by('-fecha_registro')
    
    return render(request, 'beneficiarios/detalle.html', {
        'beneficiario': beneficiario,
        'visitas': visitas,
        'titulo_pagina': 'Historial de Visitas'
    })

# --- 4. EXPORTACIÓN Y ESTADÍSTICAS ---

@login_required
def exportar_excel(request):
    try:
        wb = openpyxl.Workbook()
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        white_font = Font(color="FFFFFF", bold=True, size=11)
        title_font = Font(bold=True, size=14, color="1E293B")

        # --- Hoja 1: Resumen ---
        ws_stats = wb.active
        ws_stats.title = "Resumen Ejecutivo"
        ws_stats["A1"] = "INFORME ESTRATÉGICO DE GESTIÓN"
        ws_stats["A1"].font = title_font
        ws_stats.append([]) 
        ws_stats.append(["INDICADOR", "VALOR ACTUAL"])
        
        # Consultas de conteo para los indicadores del resumen
        ws_stats.append(["Total Beneficiarios", Beneficiario.objects.count()])
        ws_stats.append(["Total de Visitas", Visita.objects.count()])

        # --- Hoja 2: Base de Beneficiarios ---
        ws_ben = wb.create_sheet(title="Base de Beneficiarios")
        headers_ben = ['TIPO ID', 'DOCUMENTO', 'NOMBRE COMPLETO', 'TELÉFONO', 'EMAIL', 'DIRECCIÓN ESPECÍFICA']
        ws_ben.append(headers_ben)
        
        # Recuperación de la base de datos de ciudadanos
        beneficiarios = Beneficiario.objects.all() 
        
        for b in beneficiarios:
            ws_ben.append([
                b.tipo_documento,
                b.documento_identidad,
                b.nombre_completo.upper() if b.nombre_completo else "SIN NOMBRE",
                b.telefono or "N/A",
                b.email or "Sin correo",
                # Se utiliza direccion_especifica según el modelo de Beneficiario
                b.direccion_especifica or "Sin dirección"
            ])

        # --- Hoja 3: Historial de Visitas ---
        ws_visitas = wb.create_sheet(title="Historial de Visitas")
        headers_vis = ['FECHA Y HORA', 'BENEFICIARIO', 'CÉDULA', 'MOTIVO', 'ATENDIDO POR']
        ws_visitas.append(headers_vis)
        
        # Optimización de consulta mediante select_related para evitar múltiples hits a la BD
        visitas = Visita.objects.select_related('beneficiario', 'registrado_por').all()
        for v in visitas:
            # Formateo de fecha y hora para legibilidad en el archivo Excel
            f_fecha = v.fecha_registro.strftime("%d/%m/%Y %H:%M") if hasattr(v, 'fecha_registro') and v.fecha_registro else "N/A"
            
            ws_visitas.append([
                f_fecha,
                v.beneficiario.nombre_completo,
                v.beneficiario.documento_identidad,
                v.get_motivo_display(),
                v.registrado_por.username if v.registrado_por else "Sistema"
            ])

        # --- AUTO-AJUSTE DE COLUMNAS Y ESTILOS ---
        for sheet in wb.worksheets:
            # Aplicación de estilos a la fila de encabezados
            for row in sheet.iter_rows(min_row=1, max_row=1):
                for cell in row:
                    cell.fill = header_fill
                    cell.font = white_font
            
            # Cálculo de ancho de columna basado en el contenido más largo
            for column_cells in sheet.columns:
                length = max(len(str(cell.value)) for cell in column_cells)
                sheet.column_dimensions[get_column_letter(column_cells[0].column)].width = length + 5

        # Construcción de la respuesta HTTP con el tipo de contenido adecuado para archivos .xlsx
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Reporte_SIG_INTU.xlsx"'
        wb.save(response)
        return response

    except Exception as e:
        # Captura de excepciones generales para prevenir el cierre inesperado de la aplicación
        messages.error(request, f"Error técnico al generar Excel: {str(e)}")
        return redirect('beneficiarios:lista')

@login_required
def buscar_beneficiario_api(request):
    query = request.GET.get('cedula', '').strip()
    results = []
    
    if len(query) >= 2:
        # Busca por cédula o por nombre
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



def gestion_documental(request):
    query = request.GET.get('q', '')
    beneficiarios_list = Beneficiario.objects.all().order_by('nombre_completo')
    
    if query:
        beneficiarios_list = beneficiarios_list.filter(
            Q(nombre_completo__icontains=query) | 
            Q(documento_identidad__icontains=query)
        )
    
    context = {
        'beneficiarios': beneficiarios_list,
        'query': query,
        'total_beneficiarios': beneficiarios_list.count(),
    }
    return render(request, 'beneficiarios/gestion_documental.html', context)

def expediente_detalle(request, pk):
    # Esta es la función que te falta
    beneficiario = get_object_or_404(Beneficiario, pk=pk)
    
    # Aquí puedes agregar la lógica para traer sus documentos digitalizados
    # documentos = beneficiario.documentos.all() 
    
    context = {
        'beneficiario': beneficiario,
        # 'documentos': documentos,
    }
    return render(request, 'beneficiarios/expediente_archivo.html', context)




def beneficiarios_estadisticas(request):
    # 1. Totales base
    total_beneficiarios = Beneficiario.objects.count()
    total_visitas = Visita.objects.count()

    # 2. Densidad por Estado (Usando el nombre real del estado registrado)
    visitas_por_estado = Beneficiario.objects.values('estado__nombre')\
        .annotate(total=Count('id'))\
        .order_by('-total')

    # 3. Productividad del Personal (AHORA SÍ: Usando 'registrado_por' de Visita)
    gestion_por_operador = Visita.objects.values(
        'registrado_por__username', 
        'registrado_por__first_name', 
        'registrado_por__last_name'
    ).annotate(total=Count('id')).order_by('-total')

    # 4. Demografía por Género
    genero_data = Beneficiario.objects.values('genero')\
        .annotate(total=Count('id'))\
        .order_by('-total')

    # 5. Frecuencia por Motivo (De la tabla Visita)
    visitas_por_tipo = Visita.objects.values('motivo')\
        .annotate(total=Count('id')).order_by('-total')

    # 6. Preparación de KPIs superiores
    estado_top = visitas_por_estado.first() if visitas_por_estado else None
    # Obtenemos el motivo más frecuente de la lista ya consultada
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
    }
    
    return render(request, 'beneficiarios/estadisticas_beneficiarios.html', context)