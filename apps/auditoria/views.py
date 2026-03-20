from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from .models import LogAuditoria
import openpyxl
from openpyxl.styles import Font
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

def es_administrador(user):
    return user.is_superuser or user.groups.filter(name='Auditores').exists()

def obtener_logs_filtrados(request):
    """Función auxiliar para reutilizar la lógica de filtros en web, excel y pdf"""
    usuario_id = request.GET.get('usuario')
    modulo = request.GET.get('modulo')
    fecha_inicio = request.GET.get('desde')
    fecha_fin = request.GET.get('hasta')

    logs = LogAuditoria.objects.all().select_related('usuario').order_by('-timestamp')

    if usuario_id:
        logs = logs.filter(usuario_id=usuario_id)
    if modulo:
        logs = logs.filter(modulo__icontains=modulo)
    if fecha_inicio and fecha_fin:
        logs = logs.filter(timestamp__range=[fecha_inicio, fecha_fin])
    
    return logs

@login_required
@user_passes_test(es_administrador)
def lista_auditoria(request):
    logs = obtener_logs_filtrados(request)
    return render(request, 'auditoria/bitacora.html', {
        'logs': logs[:100], 
        'modulos': LogAuditoria.objects.values_list('modulo', flat=True).distinct()
    })

@login_required
@user_passes_test(es_administrador)
def exportar_auditoria_excel(request):
    logs = obtener_logs_filtrados(request)
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="Reporte_Auditoria.xlsx"'
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Auditoría"
    
    # Cabecera
    columns = ['Fecha', 'Usuario', 'Módulo', 'Acción', 'Descripción', 'IP']
    ws.append(columns)
    
    # Estilo para la cabecera
    for cell in ws[1]:
        cell.font = Font(bold=True)
        
    # Datos
    for log in logs:
        ws.append([
            log.timestamp.strftime('%d/%m/%Y %H:%M'),
            str(log.usuario),
            log.modulo,
            log.get_accion_display(),
            log.descripcion,
            log.direccion_ip
        ])
            
    wb.save(response)
    return response

@login_required
@user_passes_test(es_administrador)
def exportar_auditoria_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Reporte_Auditoria.pdf"'
    
    logs = obtener_logs_filtrados(request)[:100] # Limitamos para evitar PDFs infinitos
    
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    
    data = [['FECHA', 'USUARIO', 'MODULO', 'ACCION', 'IP']]
    for log in logs:
        data.append([
            log.timestamp.strftime('%d/%m/%y %H:%M'),
            str(log.usuario)[:15], # Truncamos para que quepa en la tabla
            log.modulo[:15],
            log.get_accion_display(),
            log.direccion_ip
        ])
    
    table = Table(data, colWidths=[100, 100, 100, 80, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')), # Slate-900
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    
    elements.append(table)
    doc.build(elements)
    return response