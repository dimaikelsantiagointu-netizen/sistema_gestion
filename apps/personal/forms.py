from django import forms
from .models import Personal
from apps.beneficiarios.models import DocumentoExpediente 
from django.core.exceptions import ValidationError
import re

class PersonalForm(forms.ModelForm):
    class Meta:
        model = Personal
        fields = [
            'cedula', 'nombres', 'apellidos', 'fecha_ingreso', 
            'cargo', 'unidad_adscrita', 'telefono', 'email'
        ]
        widgets = {
            'cedula': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'V-12345678'}),
            'nombres': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'NOMBRES'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'APELLIDOS'}),
            'fecha_ingreso': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'cargo': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'EJ: ANALISTA'}),
            'unidad_adscrita': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'EJ: TECNOLOGÍA'}),
            'telefono': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '0412-0000000'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'usuario@institucion.gob.ve'}),
        }

    # --- Validaciones de Normalización (Mayúsculas y Espacios) ---
    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula').upper().strip()
        if Personal.objects.filter(cedula=cedula).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Ya existe un trabajador registrado con esta cédula.")
        return cedula

    def clean_nombres(self):
        return self.cleaned_data.get('nombres', '').upper().strip()

    def clean_apellidos(self):
        return self.cleaned_data.get('apellidos', '').upper().strip()

    def clean_cargo(self):
        return self.cleaned_data.get('cargo', '').upper().strip()

    def clean_unidad_adscrita(self):
        return self.cleaned_data.get('unidad_adscrita', '').upper().strip()

    # --- Validación de Teléfono (Evita caracteres basura) ---
    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if telefono:
            # Solo permite números y guiones
            if not re.match(r'^[0-9\-]+$', telefono):
                raise ValidationError("El teléfono solo debe contener números y guiones.")
        return telefono

class SubirDocumentoForm(forms.ModelForm):
    class Meta:
        model = DocumentoExpediente
        fields = ['nombre_documento', 'categoria', 'archivo']
        widgets = {
            'nombre_documento': forms.TextInput(attrs={'class': 'form-input', 'readonly': 'readonly'}),
            'categoria': forms.HiddenInput(),
            'archivo': forms.FileInput(attrs={'class': 'form-input', 'accept': 'application/pdf'}),
        }
    
    def clean_archivo(self):
        archivo = self.cleaned_data.get('archivo')
        if archivo:
            # Validación del Punto 6 de la nota técnica: Tamaño máx 2MB
            if archivo.size > 2 * 1024 * 1024:
                raise ValidationError("El archivo excede los 2 MB permitidos.")
            
            if not archivo.name.lower().endswith('.pdf'):
                raise ValidationError("Solo se permiten archivos en formato PDF para el expediente.")
        return archivo