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
# Importa tus modelos (Asegúrate que Contrato exista si lo vas a usar)
from .models import Beneficiario, DocumentoExpediente, Visita
from django.core.paginator import Paginator
logger = logging.getLogger(__name__)

# --- 1. GESTIÓN DE BENEFICIARIOS ---

@login_required
def lista_beneficiarios(request):
    query = request.GET.get('q')
    if query:
        # Mejora: busca por nombre o documento
        lista = Beneficiario.objects.filter(
            Q(nombre_completo__icontains=query) | 
            Q(documento_identidad__icontains=query)
        ).distinct()
    else:
        lista = Beneficiario.objects.all().order_by('-id')

    # --- LÓGICA PARA LAS TARJETAS (ESTADÍSTICAS) ---
    hoy = timezone.now().date()
    
    # 1. Visitas agendadas para hoy
    visitas_hoy_count = Visita.objects.filter(fecha_registro__date=hoy).count()
    
    # 2. Beneficiarios que tienen al menos un documento (Digitalizados)
    # Usamos annotate para contar documentos por beneficiario y filtrar los que tengan > 0
    beneficiarios_con_docs = Beneficiario.objects.annotate(
        num_docs=Count('documentos')
    ).filter(num_docs__gt=0).count()

    # Paginación
    paginator = Paginator(lista, 10) 
    page_number = request.GET.get('page')
    beneficiarios_paginados = paginator.get_page(page_number)

    context = {
        'beneficiarios': beneficiarios_paginados,
        'query': query,
        'total_beneficiarios': Beneficiario.objects.count(),
        'visitas_hoy_count': visitas_hoy_count,        # <--- Agregado
        'beneficiarios_con_docs': beneficiarios_con_docs, # <--- Agregado
    }
    return render(request, 'beneficiarios/lista.html', context)

@login_required
def crear_beneficiario(request):
    if request.method == 'POST':
        try:
            beneficiario = Beneficiario.objects.create(
                tipo_documento=request.POST.get('tipo_documento'),
                documento_identidad=request.POST.get('documento_identidad'),
                nombre_completo=request.POST.get('nombre_completo'),
                telefono=request.POST.get('telefono'),
                email=request.POST.get('email'),
                direccion=request.POST.get('direccion')
            )
            messages.success(request, f"Beneficiario {beneficiario.nombre_completo} registrado.")
            return redirect('beneficiarios:lista')
        except Exception as e:
            messages.error(request, f"Error al registrar: {e}")
    
    return render(request, 'beneficiarios/formulario.html', {
        'titulo': 'Nuevo Beneficiario',
        'boton': 'Registrar'
    })

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
def expediente_beneficiario(request, id): # <--- CAMBIADO: debe ser 'id' para coincidir con urls.py
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
    b_id = documento.beneficiario.id  # Guardamos el ID antes de borrar
    
    if documento.archivo:
        documento.archivo.delete(save=False)
    
    documento.delete()
    messages.success(request, "Archivo eliminado correctamente.")
    
    # LA CORRECCIÓN CRÍTICA: Cambiar 'beneficiario_id' por 'id'
    return redirect('beneficiarios:expediente', id=b_id)

# --- 3. GESTIÓN DE VISITAS ---

@login_required
def registrar_visita(request):
    if request.method == 'POST':
        b_id = request.POST.get('beneficiario_id')
        if b_id:
            beneficiario = get_object_or_404(Beneficiario, id=b_id)
            
            # 1. Limpieza de fecha: datetime-local envía 'YYYY-MM-DDTHH:MM'
            # Django necesita convertir eso o usar timezone.now()
            fecha_post = request.POST.get('fecha_registro')
            
            Visita.objects.create(
                beneficiario=beneficiario,
                motivo=request.POST.get('motivo'),
                descripcion=request.POST.get('descripcion'),
                registrado_por=request.user,
                fecha_registro=fecha_post if fecha_post else timezone.now()
            )
            
            messages.success(request, "Visita registrada correctamente.")
            
            # 2. CORRECCIÓN DE RUTA: 
            # Según tus errores anteriores, tu parámetro es 'id', no 'pk'.
            return redirect('beneficiarios:detalle', id=beneficiario.id)
    
    # 3. Datos para el template
    return render(request, 'beneficiarios/form_visita.html', {
        'motivos': Visita.MOTIVO_CHOICES,
        'current_time': timezone.now() # Necesario para el valor inicial del input de fecha
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
def detalle_beneficiario(request, id): # Cambiado pk por id
    beneficiario = get_object_or_404(Beneficiario, id=id) # Cambiado pk por id
    # Traemos las visitas relacionadas
    visitas = beneficiario.visitas.all().order_by('-fecha_registro')
    
    # IMPORTANTE: Asegúrate de que este template sea diferente al de expediente.html
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
        
        # Usamos counts simples para evitar errores de campos
        ws_stats.append(["Total Beneficiarios", Beneficiario.objects.count()])
        ws_stats.append(["Total de Visitas", Visita.objects.count()])

        # --- Hoja 2: Base de Beneficiarios ---
        ws_ben = wb.create_sheet(title="Base de Beneficiarios")
        # Quitamos 'FECHA REGISTRO' de los headers porque el error dice que no existe
        headers_ben = ['TIPO ID', 'DOCUMENTO', 'NOMBRE COMPLETO', 'TELÉFONO', 'EMAIL', 'DIRECCIÓN']
        ws_ben.append(headers_ben)
        
        # Eliminamos .order_by('-fecha_registro') que es lo que causaba el error
        beneficiarios = Beneficiario.objects.all() 
        
        for b in beneficiarios:
            ws_ben.append([
                b.tipo_documento,
                b.documento_identidad,
                b.nombre_completo.upper() if b.nombre_completo else "SIN NOMBRE",
                b.telefono or "N/A",
                b.email or "Sin correo",
                b.direccion or "Sin dirección"
            ])

        # --- Hoja 3: Historial de Visitas ---
        ws_visitas = wb.create_sheet(title="Historial de Visitas")
        headers_vis = ['FECHA Y HORA', 'BENEFICIARIO', 'CÉDULA', 'MOTIVO', 'ATENDIDO POR']
        ws_visitas.append(headers_vis)
        
        # En Visita parece que sí existe fecha_registro, pero por si acaso lo manejamos
        visitas = Visita.objects.select_related('beneficiario', 'registrado_por').all()
        for v in visitas:
            # Verificamos si fecha_registro existe en el objeto v
            f_fecha = v.fecha_registro.strftime("%d/%m/%Y %H:%M") if hasattr(v, 'fecha_registro') and v.fecha_registro else "N/A"
            
            ws_visitas.append([
                f_fecha,
                v.beneficiario.nombre_completo,
                v.beneficiario.documento_identidad,
                v.get_motivo_display(),
                v.registrado_por.username if v.registrado_por else "Sistema"
            ])

        # --- AUTO-AJUSTE DE COLUMNAS ---
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(min_row=1, max_row=1):
                for cell in row:
                    cell.fill = header_fill
                    cell.font = white_font
            
            for column_cells in sheet.columns:
                length = max(len(str(cell.value)) for cell in column_cells)
                sheet.column_dimensions[get_column_letter(column_cells[0].column)].width = length + 5

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Reporte_SIG_INTU.xlsx"'
        wb.save(response)
        return response

    except Exception as e:
        # Esto te dirá exactamente en qué parte falla ahora si persiste el error
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
        )[:5]  # Limitamos a 5 resultados para mayor velocidad
        
        for b in beneficiarios:
            results.append({
                'id': b.id,
                'nombre': b.nombre_completo.upper(),
                'cedula': b.documento_identidad,
                'tipo_doc': b.tipo_documento
            })
            
    return JsonResponse({'encontrado': len(results) > 0, 'results': results})