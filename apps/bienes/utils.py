import os
from io import BytesIO
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

def generar_etiqueta_pdf(bien_o_queryset):

    buffer = BytesIO()
    ancho_pagina = 5 * cm
    alto_pagina = 2.5 * cm
    
    c = canvas.Canvas(buffer, pagesize=(ancho_pagina, alto_pagina))

    # Convertimos a lista si es un solo objeto para usar el mismo bucle
    if hasattr(bien_o_queryset, 'nro_identificacion'):
        bienes = [bien_o_queryset]
    else:
        bienes = bien_o_queryset

    # Rutas de logos (Ajusta los nombres de archivo según los tengas en tu carpeta static)
    ruta_logo1 = os.path.join(settings.BASE_DIR, 'static/images/logo_institucion.png')
    ruta_logo2 = os.path.join(settings.BASE_DIR, 'static/images/logo_gobierno.png')

    for bien in bienes:
        # --- 1. ENCABEZADO (Logos) ---
        y_logos = alto_pagina - 0.93 * cm 
        if os.path.exists(ruta_logo1):
            c.drawImage(ruta_logo1, 0.1 * cm, y_logos, width=1.6 * cm, height=0.8 * cm, preserveAspectRatio=True)
        if os.path.exists(ruta_logo2):
            c.drawImage(ruta_logo2, 1.8 * cm, y_logos, width=3.0 * cm, height=0.8 * cm, preserveAspectRatio=True)

        # --- 2. CUERPO: CÓDIGO QR ---
        if bien.qr_imagen:
            try:
                # Usamos la ruta física del QR generado por el modelo
                c.drawImage(bien.qr_imagen.path, 0.0 * cm, 0.0 * cm, width=1.65 * cm, height=1.65 * cm)
            except Exception:
                pass

        # --- 3. CUERPO: DATOS ---
        x_texto = 1.85 * cm
        y_texto_base = 1.3 * cm

        c.setFont("Helvetica-Bold", 5)
        c.drawString(x_texto, y_texto_base, "DESCRIPCIÓN:")
        c.setFont("Helvetica", 5)
        desc = (bien.descripcion[:22] + '..') if len(bien.descripcion) > 22 else bien.descripcion
        c.drawString(x_texto, y_texto_base - 0.20 * cm, desc.upper())

        c.setFont("Helvetica-Bold", 5)
        c.drawString(x_texto, y_texto_base - 0.45 * cm, "CÓDIGO:")
        c.setFont("Helvetica", 6)
        c.drawString(x_texto, y_texto_base - 0.65 * cm, str(bien.nro_identificacion))

        c.setFont("Helvetica-Bold", 5)
        c.drawString(x_texto, y_texto_base - 0.90 * cm, "UBICACIÓN:")
        c.setFont("Helvetica", 4.5)
        ubica = (bien.unidad_trabajo.nombre[:25] + '..') if len(bien.unidad_trabajo.nombre) > 25 else bien.unidad_trabajo.nombre
        c.drawString(x_texto, y_texto_base - 1.10 * cm, ubica.upper())

        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer