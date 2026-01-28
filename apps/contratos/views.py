import io, openpyxl
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, HttpResponse
from django.db.models import Count
from django.db.models.functions import ExtractMonth, ExtractYear
from django.utils import timezone
from datetime import datetime

# Modelos
from .models import Contrato, HistorialContrato, ConfiguracionInstitucional
from apps.beneficiarios.models import Beneficiario

# ReportLab
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER

# --- MOTOR DE REDACCIÓN AUTOMÁTICA ---
def generar_cuerpo_legal(beneficiario, datos, config):
    """
    Genera la totalidad del texto legal sin omisiones, 
    ajustando géneros y pluralidad según el formato original.
    """
    # 1. Lógica de género y artículos
    es_fem = getattr(beneficiario, 'genero', 'M') == 'F'
    
    opciones = {
        'art_ciudadano': "a la ciudadana" if es_fem else "al ciudadano",
        'estado_civil': beneficiario.get_estado_civil_display().upper() if hasattr(beneficiario, 'get_estado_civil_display') else "SOLTERO",
        'identificado_pron': "identificada" if es_fem else "identificado",
        'yo_nos': "yo", # Para este formato específico se usa minúscula según tu texto
        'declaro_nos': "declaro",
        'acepto_nos': "acepto",
        'me_nos': "me",
        'conozco_nos': "conozco",
        'recibo_nos': "recibo",
        'acuerdo_nos': "acuerdo y acepto",
        'mi_nos': "mi",
        'obligo_nos': "obligándome",
        'renuncio_nos': "renuncio",
        'comprometo_nos': "me comprometo",
    }

    # 2. EL TEXTO COMPLETO E ÍNTEGRO (PEGADO EXACTAMENTE)
    texto_final = f"""Quien suscribe, {config.nombre_gerente.upper()}, venezolano, mayor de edad, con domicilio en Caracas, titular de la cédula de identidad Nº {config.cedula_gerente}, procediendo en mi carácter como Gerente del Distrito Capital. Estadal, Designado mediante Nº Providencia Administrativa N {config.providencia_nro} de fecha {config.fecha_providencia.strftime('%d-%m-%y') if config.fecha_providencia else '03-12-24'}, Publicada en Gaceta Oficial de la República Bolivariana de Venezuela N° {config.gaceta_nro} para actuar en nombre del INSTITUTO NACIONAL DE TIERRAS URBANAS (INTU); Ente creado y adscrito al Ministerio del Poder Popular para Hábitat y Vivienda, el cual acredita mediante documento Carta Poder, (el cual se anexa) según lo establecido en el artículo 34 del Decreto con Rango, Valor y Fuerza de Ley Especial de Regularización Integral de la Tenencia de la Tierra de los Asentamientos Urbanos o Periurbanos, Número 8.198 de fecha 05 de mayo de 2.011, publicado en Gaceta Oficial de la República Bolivariana de Venezuela Nº 39.668 de fecha 06/05/2011, inscrito en el Registro de Información Fiscal bajo el Número G-200101873, y fundamentado en los artículos 35, numerales 1 y 2; 36 numeral 19 y  65 de dicho Decreto, mediante el cual se inicia el proceso de regularización integral de la tenencia de la tierra de los asentamientos urbanos o periurbanos en tierras públicas y en concordancia con la Ley Orgánica de Procedimientos Administrativos publicada en la Gaceta Oficial Extraordinaria Nº 2.818 de fecha 01 de julio de 1981, declaro: con fines de garantizar a las familias que viven asentadas en forma espontánea y que han conformado comunidades de largo arraigo, la atención por parte del Estado  para  que se le reconozca la posesión de la tierra, haciéndolas acreedoras del derecho de propiedad de la tierra, por ende, el uso, goce, disfrute y disposición de la misma, cuyo objeto principal es el de mejorar y elevar su calidad de vida y garantizarles el derecho a la vivienda y a la seguridad social que consagra la Constitución de la República Bolivariana de Venezuela, por medio del presente documento el INSTITUTO NACIONAL DE TIERRAS URBANAS (INTU). 

En nombre de mi representado: doy en venta pura y simple, perfecta e irrevocable {opciones['art_ciudadano']}: {beneficiario.nombre_completo.upper()}, de nacionalidad venezolana, mayor de edad, {opciones['estado_civil']}, de este domicilio y titular de la cédula de identidad N° {beneficiario.documento_identidad}, una parcela de terreno, asignada con el código catastral {datos['catastro']}, con una superficie de: {datos['sup_letras'].upper()} ({datos['sup_num']} M2), ubicada en la {datos['direccion'].upper()}, la cual pertenece a un lote de terreno de mayor extensión, propiedad del Instituto Nacional de la Vivienda (INAVI), según se evidencia de Documento Protocolizado por ante la Oficina Subalterna del Primer Circuito de Registro Público del Departamento Libertador del Distrito Federal (hoy Municipio Libertador del Distrito Capital), de fecha 20 de mayo de 1.986, anotado bajo el N°36, Tomo 11, Protocolo Primero, con una extensión total de SEISCIENTAS HECTARIAS (600,00 H), con los siguientes linderos generales: NORTE: Autopista Caracas-La Guaira; SUR: Alío de Guayabal, Loma La Paila, y Hoyo del Diablo; ESTE: Terrenos Propiedad de Inversiones Chellini; y OESTE: Divisoria de la Quebrada Tacagua Arriba y Lindero Parroquia Carayaca. 

Los linderos específicos de la parcela objeto del presente contrato, son los siguientes: NORTE: {datos['norte']}; SUR: {datos['sur']}; ESTE: {datos['este']}; OESTE: {datos['oeste']}, según consta en su respectivo levantamiento planímetro y plano avalado por la Dirección de documentación e información Catastral de la Alcaldía del Municipio Bolivariano Libertador, del Distrito Capital los cuales se anexa para ser agregado al cuaderno de comprobantes. El precio de esta venta es por la cantidad de una milésima de Bolívar soberano (0,001) por metro cuadrado, correspondiente a la alícuota de la parcela, por la cantidad de UN BOLIVAR SOBERANO (Bs.1,0), el cual fue depositado en su totalidad al INTU bajo el Nº 139504167, de conformidad con el Articulo 58 de Decreto con Rango, Valor y Fuerza de Ley Especial de Regularización Integral de la Tenencia de la Tierra de los Asentamientos Urbanos o Periurbanos, anexo al presente documento para que sea agregado al cuaderno de comprobantes respectivo. 

Con el otorgamiento de este documento se transmite la propiedad del terreno, el cual ya está en posesión de la persona adquiriente, quedando el INSTITUTO NACIONAL DE TIERRAS URBANAS (INTU), obligado solo al saneamiento por evicción. El mencionado terreno se encuentra libre de todo gravamen y nada adeuda por impuestos estatales y municipales, ni por ningún otro concepto. Y {opciones['yo_nos']}, {beneficiario.nombre_completo.upper()}, anteriormente {opciones['identificado_pron']}, {opciones['declaro_nos']} que {opciones['acepto_nos']} la venta que se {opciones['me_nos']} hace en los términos y condiciones señaladas en el presente documento, de lo expuesto, queda por sentado que {opciones['conozco_nos']} perfectamente el inmueble y lo {opciones['recibo_nos']} en el estado y condiciones en que se encuentra. Asimismo, {opciones['acuerdo_nos']} renunciar a cualquier eventual reclamo que se pueda ejercer por asumir a {opciones['mi_nos']} cuenta y riesgo el inmueble aquí adjudicado, {opciones['obligo_nos']} a cumplir con lo establecido en el Código Civil, Ley Orgánica de Ordenación Urbanística, Ley Orgánica del Poder Público Municipal y la Ordenanza de Zonificación vigente que rige el sector y demás leyes que regulen la materia. 

De la misma manera, {opciones['declaro_nos']} que, si el área de terreno objeto de esta adjudicación se encontrare afectada por de ramales, acueductos, o por instalaciones para el funcionamiento de conductores destinado a los servicios públicos o privados de luz eléctrica, teléfono o radio a recepción, así como también por el desagüe de los predios superiores o cualquier otro tipo de instalaciones, construcciones o bienhechurías, todo lo cual pudo haber ocurrido por desconocimiento del INSTITUTO NACIONAL DE TIERRAS URBANAS (INTU), {opciones['renuncio_nos']} expresamente a ejercer cualquier derecho o acción que pueda derivarse contra dicho Instituto en virtud de los hechos enunciado, {opciones['obligo_nos']} a permitir que continúe en el sitio en que se encontraren los mencionados ramales o instalaciones, y a solicitar el permiso correspondiente para realizar su reubicación en otro espacio dentro de la misma área geográfica, sin que ello menoscabe, lo señalado en el artículo 5 de la Resolución Nº 004 de fecha 16 de abril de 2015, ejusdem. Igualmente, {opciones['comprometo_nos']} a respetar las servidumbres que hubieran sido legalmente constituidas. Es convenio entre las partes que el INSTITUTO NACIONAL DE TIERRAS URBANAS (INTU), queda libre del saneamiento por vicios ocultos conforme a lo establecido en el artículo 1.520 del Código Civil. La adjudicación contenida en el presente documento estará regida por el Decreto con Rango Valor y Fuerza de Ley Especial de Regularización Integral de la Tenencia de la Tierra de los Asentamientos Urbanos o Periurbanos, publicada en la Gaceta Oficial de la República Bolivariana de Venezuela Nº 39.668 de fecha 06 de Mayo de 2011. Se elige como domicilio especial para ambas partes la ciudad de Caracas. Se invocan a favor del INSTITUTO NACIONAL DE TIERRAS URBANAS (INTU), las exenciones legales. Se hacen tres (03) ejemplares a un solo tenor y a un mismo efecto. En la ciudad de Caracas, Municipio Bolivariano Libertador, Distrito Capital, a la fecha de su Protocolización."""
    
    return texto_final

# --- VISTAS DEL MÓDULO ---

@login_required
def lista_contratos(request):
    contratos = Contrato.objects.select_related('beneficiario').all().order_by('-fecha_creacion')
    return render(request, 'contratos/lista_contratos.html', {'contratos': contratos})

@login_required
def crear_contrato(request):
    if request.method == 'POST':
        try:
            beneficiario = get_object_or_404(Beneficiario, id=request.POST.get('beneficiario'))
            config = ConfiguracionInstitucional.objects.first()
            if not config:
                config = ConfiguracionInstitucional.objects.create()

            datos_tecnicos = {
                'catastro': request.POST.get('codigo_catastral'),
                'sup_num': request.POST.get('superficie_num'),
                'sup_letras': request.POST.get('superficie_letras'),
                'direccion': request.POST.get('direccion_plano'),
                'norte': request.POST.get('lindero_norte'),
                'sur': request.POST.get('lindero_sur'),
                'este': request.POST.get('lindero_este'),
                'oeste': request.POST.get('lindero_oeste'),
            }

            cuerpo_auto = generar_cuerpo_legal(beneficiario, datos_tecnicos, config)

            contrato = Contrato.objects.create(
                beneficiario=beneficiario,
                codigo_contrato=request.POST.get('codigo'),
                tipo_contrato="VENTA PURA Y SIMPLE",
                cuerpo_contrato=cuerpo_auto,
                # Guardamos datos técnicos en los nuevos campos del modelo
                codigo_catastral=datos_tecnicos['catastro'],
                superficie_num=datos_tecnicos['sup_num'],
                superficie_letras=datos_tecnicos['sup_letras'],
                direccion_inmueble=datos_tecnicos['direccion'],
                lindero_norte=datos_tecnicos['norte'],
                lindero_sur=datos_tecnicos['sur'],
                lindero_este=datos_tecnicos['este'],
                lindero_oeste=datos_tecnicos['oeste'],
                creado_por=request.user
            )

            HistorialContrato.objects.create(
                contrato=contrato, usuario=request.user, accion='CREACIÓN',
                descripcion="Contrato generado automáticamente con datos técnicos."
            )

            messages.success(request, f"Contrato {contrato.codigo_contrato} creado.")
            return redirect('contratos:lista')
        except Exception as e:
            messages.error(request, f"Error: {e}")
            
    beneficiarios = Beneficiario.objects.all()
    return render(request, 'contratos/form_contrato.html', {'beneficiarios': beneficiarios})

@login_required
def detalle_contrato(request, pk):
    contrato = get_object_or_404(Contrato, pk=pk)
    historial = contrato.historial.all()
    
    if request.method == 'POST' and 'aprobar' in request.POST:
        contrato.estado = 'aprobado'
        contrato.aprobado_por = request.user
        contrato.fecha_aprobacion = timezone.now()
        contrato.save()

        HistorialContrato.objects.create(
            contrato=contrato, usuario=request.user, accion='APROBACIÓN',
            descripcion="Documento validado por Gerencia."
        )
        messages.success(request, "Contrato aprobado.")
        return redirect('contratos:detalle', pk=contrato.pk)

    return render(request, 'contratos/detalle_contrato.html', {'contrato': contrato, 'historial': historial})

@login_required
def cronograma_trabajo(request):
    datos_mes = Contrato.objects.annotate(
        mes=ExtractMonth('fecha_creacion'),
        anio=ExtractYear('fecha_creacion')
    ).values('mes', 'anio', 'estado').annotate(total=Count('id')).order_by('-anio', '-mes')
    return render(request, 'contratos/cronograma.html', {'reporte_mensual': datos_mes, 'hoy': timezone.now()})

@login_required
def descargar_contrato_pdf(request, pk):
    contrato = get_object_or_404(Contrato, pk=pk)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    
    story = []
    styles = getSampleStyleSheet()
    estilo_cuerpo = ParagraphStyle(name='Justificado', fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=12)

    story.append(Paragraph("<b>INSTITUTO NACIONAL DE TIERRAS URBANAS (INTU)</b>", styles['Title']))
    story.append(Spacer(1, 0.4 * inch))
    
    texto_html = contrato.cuerpo_contrato.replace('\n', '<br/>')
    story.append(Paragraph(texto_html, estilo_cuerpo))

    doc.build(story)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f'Contrato_{contrato.codigo_contrato}.pdf')

@login_required
def estadisticas_contratos(request):
    stats_por_estado = Contrato.objects.values('estado').annotate(total=Count('estado'))
    total_general = Contrato.objects.count()
    stats_procesadas = [
        {'estado': item['estado'], 'total': item['total'], 
         'porcentaje': round((item['total']/total_general*100), 1) if total_general > 0 else 0}
        for item in stats_por_estado
    ]
    return render(request, 'contratos/estadisticas.html', {'stats': stats_procesadas, 'total_general': total_general})

@login_required
def exportar_contratos_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['Código', 'Tipo', 'Beneficiario', 'Estado', 'Fecha'])
    for c in Contrato.objects.all():
        ws.append([c.codigo_contrato, c.tipo_contrato, c.beneficiario.nombre_completo, c.estado, c.fecha_creacion.strftime('%d/%m/%Y')])
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="reporte.xlsx"'
    wb.save(response)
    return response