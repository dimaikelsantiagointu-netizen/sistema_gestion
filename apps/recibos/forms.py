from django import forms

class UploadFileForm(forms.Form):
    """
    Define el formulario necesario para subir el archivo de Excel.
    """
    # FileField es el tipo de campo necesario para manejar archivos en Django
    file = forms.FileField(label='Seleccione Archivo Excel (.xlsx o .xls)')