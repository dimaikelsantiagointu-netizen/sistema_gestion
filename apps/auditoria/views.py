from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.utils import timezone
from .models import LogAuditoria

# Librerías para Excel
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill

# Librerías para PDF
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

def es_administrador(user):
    """Verifica si el usuario es superuser o pertenece al grupo de Auditores"""
    return user.is_superuser or user.groups.filter(name='Auditores').exists()

def obtener_logs_filtrados(request):
    """Lógica unificada de filtrado para web y reportes"""
    usuario_id = request.GET.get('usuario')
    modulo = request.GET.get('modulo')
    fecha_inicio = request.GET.get('desde')
    fecha_fin = request.GET.get('hasta')

    # Optimizamos la consulta con select_related
    logs = LogAuditoria.objects.all().select_related('usuario').order_by('-timestamp')

    if usuario_id:
        logs = logs.filter(usuario_id=usuario_id)
    if modulo:
        logs = logs.filter(modulo__icontains=modulo)
    
    # Filtro de fecha robusto
    if fecha_inicio:
        logs = logs.filter(timestamp__date__gte=fecha_inicio)
    if fecha_fin:
        logs = logs.filter(timestamp__date__lte=fecha_fin)
    
    return logs

@login_required
@user_passes_test(es_administrador)
def lista_auditoria(request):
    """Vista principal de la bitácora"""
    logs_completos = obtener_logs_filtrados(request)
    # Lista de módulos únicos para el buscador
    modulos = LogAuditoria.objects.values_list('modulo', flat=True).distinct()
    
    return render(request, 'auditoria/bitacora.html', {
        'logs': logs_completos[:150], # Limitamos la vista web por rendimiento
        'modulos': modulos,
        'total_logs': logs_completos.count()
    })

@login_required
@user_passes_test(es_administrador)
def exportar_auditoria_excel(request):
    """Generación de reporte en formato Excel (.xlsx)"""
    logs = obtener_logs_filtrados(request)
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Auditoria_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bitácora de Eventos"
    
    # Estilos
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    
    # Cabeceras
    columns = ['FECHA/HORA', 'USUARIO', 'MÓDULO', 'ACCIÓN', 'DESCRIPCIÓN', 'DIRECCIÓN IP']
    ws.append(columns)
    
    for col_num, column_title in enumerate(columns, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

    # Datos
    for log in logs:
        usuario_str = log.usuario.username if log.usuario else "SISTEMA/DESCONOCIDO"
        ws.append([
            log.timestamp.replace(tzinfo=None).strftime('%d/%m/%Y %H:%M:%S'),
            usuario_str,
            log.modulo,
            log.get_accion_display(),
            log.descripcion,
            log.direccion_ip
        ])
        
    # Ajuste automático de columnas
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except: pass
        ws.column_dimensions[column].width = max_length + 2

    wb.save(response)
    return response

@login_required
@user_passes_test(es_administrador)
def exportar_auditoria_pdf(request):
    """Generación de reporte en formato PDF (Landscape para mayor espacio)"""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Auditoria_{timezone.now().strftime("%Y%m%d")}.pdf"'
    
    # Usamos landscape para que la tabla no se vea apretada
    doc = SimpleDocTemplate(response, pagesize=landscape(letter), topMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    
    # Título y metadatos del reporte
    titulo = Paragraph(f"<b>REPORTE DE AUDITORÍA - SICSI INTU</b>", styles['Title'])
    subtitulo = Paragraph(f"Generado por: {request.user.username} | Fecha: {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal'])
    elements.append(titulo)
    elements.append(subtitulo)
    elements.append(Spacer(1, 20))
    
    logs = obtener_logs_filtrados(request)[:500] # Límite razonable para PDF
    
    # Encabezados de tabla
    data = [['FECHA/HORA', 'USUARIO', 'MÓDULO', 'ACCIÓN', 'DESCRIPCIÓN', 'IP']]
    
    for log in logs:
        usuario_str = log.usuario.username if log.usuario else "SISTEMA"
        # Truncamos descripción para que no rompa la tabla
        desc = (log.descripcion[:50] + '..') if len(log.descripcion) > 50 else log.descripcion
        
        data.append([
            log.timestamp.strftime('%d/%m/%y %H:%M'),
            usuario_str,
            log.modulo[:15],
            log.get_accion_display(),
            desc,
            log.direccion_ip
        ])
    
    # Diseño de la tabla
    # Definimos anchos fijos para las columnas (total ~700 pts en landscape)
    table = Table(data, colWidths=[90, 80, 80, 90, 260, 90])
    
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])
    table.setStyle(style)
    
    elements.append(table)
    doc.build(elements)
    return response