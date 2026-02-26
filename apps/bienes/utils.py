import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from django.conf import settings


def generar_etiqueta_pdf(bien):

    carpeta = os.path.join(settings.MEDIA_ROOT, "etiquetas")
    os.makedirs(carpeta, exist_ok=True)

    nombre_archivo = f"etiqueta_{bien.uuid}.pdf"
    ruta_archivo = os.path.join(carpeta, nombre_archivo)

    doc = SimpleDocTemplate(
        ruta_archivo,
        pagesize=A4
    )

    elementos = []

    estilo = ParagraphStyle(
        name='NormalStyle',
        fontSize=12,
        textColor=colors.black
    )

    elementos.append(Paragraph(f"<b>BIEN NACIONAL</b>", estilo))
    elementos.append(Spacer(1, 10))

    elementos.append(Paragraph(f"Descripción: {bien.descripcion}", estilo))
    elementos.append(Paragraph(f"Nro Identificación: {bien.nro_identificacion}", estilo))
    elementos.append(Paragraph(f"Marca: {bien.marca}", estilo))
    elementos.append(Paragraph(f"Modelo: {bien.modelo}", estilo))
    elementos.append(Paragraph(f"Serial: {bien.serial}", estilo))
    elementos.append(Paragraph(f"Unidad: {bien.unidad_trabajo.nombre}", estilo))

    elementos.append(Spacer(1, 20))

    # Agregar imagen QR
    if bien.qr_imagen:
        ruta_qr = os.path.join(settings.MEDIA_ROOT, bien.qr_imagen.name)
        elementos.append(Image(ruta_qr, width=50*mm, height=50*mm))

    doc.build(elementos)

    return f"etiquetas/{nombre_archivo}"