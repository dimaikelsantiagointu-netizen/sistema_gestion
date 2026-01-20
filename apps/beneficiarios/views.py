from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib import messages
from .models import Beneficiario, DocumentoExpediente

# 1. LISTADO DE BENEFICIARIOS
def lista_beneficiarios(request):
    query = request.GET.get('q', '')
    if query:
        # Filtramos por nombre o documento de identidad
        beneficiarios = Beneficiario.objects.filter(
            Q(nombre_completo__icontains=query) | 
            Q(documento_identidad__icontains=query)
        )
    else:
        beneficiarios = Beneficiario.objects.all()
    
    return render(request, 'beneficiarios/lista.html', {
        'beneficiarios': beneficiarios,
        'query': query
    })

# 2. VISTA DEL EXPEDIENTE (VER CARPETA DIGITAL)
def expediente_beneficiario(request, beneficiario_id):
    beneficiario = get_object_or_404(Beneficiario, id=beneficiario_id)
    
    if request.method == 'POST':
        # Captura la lista de archivos (input name="archivos")
        archivos_subidos = request.FILES.getlist('archivos')
        nombre_descriptivo = request.POST.get('nombre_documento')

        if not archivos_subidos:
            messages.error(request, "No seleccionaste ningún archivo.")
        else:
            for f in archivos_subidos:
                DocumentoExpediente.objects.create(
                    beneficiario=beneficiario,
                    archivo=f,
                    nombre_documento=nombre_descriptivo if nombre_descriptivo else f.name
                )
            messages.success(request, f"Se cargaron {len(archivos_subidos)} archivo(s) correctamente.")
            return redirect('beneficiarios:expediente', beneficiario_id=beneficiario.id)

    documentos = beneficiario.documentos.all()
    return render(request, 'beneficiarios/expediente.html', {
        'beneficiario': beneficiario,
        'documentos': documentos
    })

# 3. ELIMINAR ARCHIVO INDIVIDUAL
def eliminar_documento(request, doc_id):
    documento = get_object_or_404(DocumentoExpediente, id=doc_id)
    beneficiario_id = documento.beneficiario.id
    
    # IMPORTANTE: Eliminar el archivo físico del almacenamiento
    if documento.archivo:
        documento.archivo.delete(save=False)
        
    documento.delete()
    messages.success(request, "Archivo eliminado del expediente.")
    return redirect('beneficiarios:expediente', beneficiario_id=beneficiario_id)

def crear_beneficiario(request):
    if request.method == 'POST':
        tipo_doc = request.POST.get('tipo_documento')
        doc_id = request.POST.get('documento_identidad')
        nombre = request.POST.get('nombre_completo')
        tlf = request.POST.get('telefono')
        mail = request.POST.get('email')
        dir_fiscal = request.POST.get('direccion')

        try:
            beneficiario = Beneficiario.objects.create(
                tipo_documento=tipo_doc,
                documento_identidad=doc_id,
                nombre_completo=nombre,
                telefono=tlf,
                email=mail,
                direccion=dir_fiscal
            )
            messages.success(request, f"Beneficiario {beneficiario.nombre_completo} registrado con éxito.")
            return redirect('beneficiarios:lista')
        except Exception as e:
            messages.error(request, f"Error al registrar: {e}")
    
    # Este return DEBE estar indentado solo una vez (dentro de crear_beneficiario)
    return render(request, 'beneficiarios/formulario.html', {
        'titulo': 'Nuevo Beneficiario',
        'boton': 'Registrar'
    })

# ESTA FUNCIÓN DEBE ESTAR EN LA COLUMNA 0 (Mismo nivel que crear_beneficiario)
def editar_beneficiario(request, id):
    beneficiario = get_object_or_404(Beneficiario, id=id)

    if request.method == 'POST':
        beneficiario.tipo_documento = request.POST.get('tipo_documento')
        beneficiario.documento_identidad = request.POST.get('documento_identidad')
        beneficiario.nombre_completo = request.POST.get('nombre_completo')
        beneficiario.telefono = request.POST.get('telefono')
        beneficiario.email = request.POST.get('email')
        beneficiario.direccion = request.POST.get('direccion')

        try:
            beneficiario.save()
            messages.success(request, f"Beneficiario {beneficiario.nombre_completo} actualizado correctamente.")
            return redirect('beneficiarios:lista')
        except Exception as e:
            messages.error(request, f"Error al actualizar: {e}")

    return render(request, 'beneficiarios/formulario.html', {
        'titulo': 'Editar Beneficiario',
        'boton': 'Guardar Cambios',
        'beneficiario': beneficiario
    })

# No olvides agregar esta si aún no la tienes para evitar errores en la tabla
def eliminar_beneficiario(request, id):
    beneficiario = get_object_or_404(Beneficiario, id=id)
    nombre = beneficiario.nombre_completo
    beneficiario.delete()
    messages.warning(request, f"Beneficiario {nombre} ha sido eliminado.")
    return redirect('beneficiarios:lista')