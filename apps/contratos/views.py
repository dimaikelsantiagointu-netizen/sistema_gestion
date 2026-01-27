import io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse

# Modelos
from .models import Contrato
from apps.beneficiarios.models import Beneficiario

# ReportLab (Generación de PDF)
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib import colors

import openpyxl
from django.http import HttpResponse
from django.db.models import Count
from datetime import datetime

@login_required
def lista_contratos(request):
    """Listado general de contratos con optimización de base de datos."""
    contratos = Contrato.objects.select_related('beneficiario').all().order_by('-fecha_creacion')
    return render(request, 'contratos/lista_contratos.html', {'contratos': contratos})

@login_required
def crear_contrato(request):
    """Vista para generar un nuevo contrato borrador."""
    if request.method == 'POST':
        try:
            beneficiario_id = request.POST.get('beneficiario')
            beneficiario = get_object_or_404(Beneficiario, id=beneficiario_id)
            
            contrato = Contrato.objects.create(
                beneficiario=beneficiario,
                codigo_contrato=request.POST.get('codigo'),
                tipo_contrato=request.POST.get('tipo'),
                cuerpo_contrato=request.POST.get('cuerpo'),
                creado_por=request.user,
                estado='borrador'
            )
            messages.success(request, f"Contrato {contrato.codigo_contrato} generado exitosamente.")
            return redirect('contratos:lista')
        except Exception as e:
            messages.error(request, f"Error al crear el contrato: {e}")
            
    beneficiarios = Beneficiario.objects.all()
    return render(request, 'contratos/form_contrato.html', {
        'beneficiarios': beneficiarios,
        'titulo': 'Generar Nuevo Contrato',
        'boton': 'Guardar Contrato'
    })

@login_required
def detalle_contrato(request, pk):
    """Vista de detalle tipo 'Hoja de Papel' con lógica de aprobación."""
    contrato = get_object_or_404(Contrato, pk=pk)
    
    # Procesar la aprobación mediante POST
    if request.method == 'POST' and 'aprobar' in request.POST:
        if request.user.is_superuser or request.user.has_perm('users.ver_gestor_contratos'):
            contrato.estado = 'aprobado'
            contrato.aprobado_por = request.user
            contrato.save()
            messages.success(request, f"El contrato {contrato.codigo_contrato} ha sido APROBADO.")
            return redirect('contratos:detalle', pk=contrato.pk)
        else:
            messages.error(request, "No tiene permisos para realizar esta acción.")

    return render(request, 'contratos/detalle_contrato.html', {'contrato': contrato})

@login_required
def descargar_contrato_pdf(request, pk):
    """Generador de PDF profesional usando ReportLab."""
    contrato = get_object_or_404(Contrato, pk=pk)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)
    
    story = []
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para el cuerpo del texto legal
    estilo_cuerpo = ParagraphStyle(
        name='Justificado',
        fontSize=11,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=12
    )

    # 1. Encabezado Institucional
    story.append(Paragraph("<b>INSTITUTO NACIONAL DE TIERRAS URBANAS (INTU)</b>", styles['Title']))
    story.append(Paragraph("Gerencia de Consultoría Jurídica", styles['Normal']))
    story.append(Spacer(1, 0.4 * inch))

    # 2. Metadatos del Documento
    story.append(Paragraph(f"<b>CÓDIGO DE EXPEDIENTE:</b> {contrato.codigo_contrato}", styles['Normal']))
    story.append(Paragraph(f"<b>FECHA DE EMISIÓN:</b> {contrato.fecha_creacion.strftime('%d/%m/%Y')}", styles['Normal']))
    story.append(Spacer(1, 0.3 * inch))

    # 3. Título Central
    titulo_estilo = ParagraphStyle(name='TituloDoc', fontSize=13, alignment=TA_CENTER, 
                                  spaceAfter=25, fontName='Helvetica-Bold')
    story.append(Paragraph(contrato.tipo_contrato.upper(), titulo_estilo))

    # 4. Cuerpo del Contrato (Tratamiento de saltos de línea)
    # Reemplazamos saltos de línea de Python por etiquetas <br/> de ReportLab
    texto_html = contrato.cuerpo_contrato.replace('\n', '<br/>')
    story.append(Paragraph(texto_html, estilo_cuerpo))

    # 5. Sección de Firmas (Tabla alineada)
    story.append(Spacer(1, 1.2 * inch))
    
    data_firmas = [
        ["__________________________", "__________________________"],
        ["POR EL INTU", f"EL BENEFICIARIO:\n{contrato.beneficiario.nombre_completo}"]
    ]
    
    tabla = Table(data_firmas, colWidths=[3*inch, 3*inch])
    tabla.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,1), (-1,1), 8),
        ('TOPPADDING', (0,1), (-1,1), 12),
    ]))
    
    story.append(tabla)

    # Construcción final del PDF
    doc.build(story)
    
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f'Contrato_{contrato.codigo_contrato}.pdf')

@login_required
def estadisticas_contratos(request):
    """Submódulo de analítica de contratos."""
    # Contamos cuántos contratos hay por cada estado disponible
    stats_por_estado = Contrato.objects.values('estado').annotate(total=Count('estado'))
    
    total_general = Contrato.objects.count()
    
    # Calculamos porcentajes para las barras de progreso
    stats_procesadas = []
    for item in stats_por_estado:
        porcentaje = (item['total'] / total_general * 100) if total_general > 0 else 0
        stats_procesadas.append({
            'estado': item['estado'],
            'total': item['total'],
            'porcentaje': round(porcentaje, 1)
        })

    return render(request, 'contratos/estadisticas.html', {
        'stats': stats_procesadas,
        'total_general': total_general
    })

@login_required
def exportar_contratos_excel(request):
    """Genera un reporte en Excel de todos los contratos."""
    # Crear el libro de trabajo y la hoja activa
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte de Contratos"

    # Definir encabezados
    headers = ['Código', 'Tipo', 'Beneficiario', 'Documento', 'Estado', 'Fecha Creación', 'Creado Por']
    ws.append(headers)

    # Estilo para los encabezados (opcional pero profesional)
    for cell in ws[1]:
        cell.font = openpyxl.styles.Font(bold=True)
        cell.fill = openpyxl.styles.PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

    # Obtener todos los datos
    contratos = Contrato.objects.select_related('beneficiario', 'creado_por').all()

    for c in contratos:
        ws.append([
            c.codigo_contrato,
            c.tipo_contrato,
            c.beneficiario.nombre_completo,
            f"{c.beneficiario.tipo_documento}-{c.beneficiario.documento_identidad}",
            c.get_estado_display() if hasattr(c, 'get_estado_display') else c.estado,
            c.fecha_creacion.strftime('%d/%m/%Y'),
            c.creado_por.username
        ])

    # Preparar la respuesta del servidor
    nombre_archivo = f"reporte_contratos_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    
    wb.save(response)
    return response