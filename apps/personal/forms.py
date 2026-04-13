from django import forms
from django.core.exceptions import ValidationError
import re

from .models import Personal, UnidadAdscrita, DocumentoPersonal
from apps.territorio.models import Estado, Municipio, Parroquia, Comuna

# ==============================================================================
# 1. GESTIÓN DE UNIDADES ADSCRITAS
# ==============================================================================
class UnidadAdscritaForm(forms.ModelForm):
    class Meta:
        model = UnidadAdscrita
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': 'EJ: RECURSOS HUMANOS'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-input', 
                'placeholder': 'BREVE DESCRIPCIÓN (OPCIONAL)',
                'rows': 3
            }),
        }

    def clean_nombre(self):
        return self.cleaned_data.get('nombre', '').upper().strip()

# ==============================================================================
# 2. FORMULARIO DE PERSONAL (CON INTEGRACIÓN TERRITORIAL COMPLETA)
# ==============================================================================
class PersonalForm(forms.ModelForm):
    class Meta:
        model = Personal
        fields = [
            'cedula', 'nombres', 'apellidos', 'fecha_ingreso', 'cargo', 
            'unidad_adscrita', 'telefono', 'email', 'activo',
            'estado', 'municipio', 'parroquia', 'comuna', 'direccion_exacta'
        ]
        widgets = {
            'cedula': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'V-12345678'}),
            'nombres': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'NOMBRES'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'APELLIDOS'}),
            'fecha_ingreso': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'cargo': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'EJ: ANALISTA'}),
            'unidad_adscrita': forms.Select(attrs={'class': 'form-input'}),
            'telefono': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '0412-0000000'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'usuario@institucion.gob.ve'}),
            'estado': forms.Select(attrs={'class': 'form-input'}),
            'municipio': forms.Select(attrs={'class': 'form-input'}),
            'parroquia': forms.Select(attrs={'class': 'form-input'}),
            'comuna': forms.Select(attrs={'class': 'form-input'}),
            'direccion_exacta': forms.Textarea(attrs={
                'class': 'form-input', 
                'rows': 2, 
                'placeholder': 'CALLE, NÚMERO DE CASA, PUNTO DE REFERENCIA...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super(PersonalForm, self).__init__(*args, **kwargs)
        
        # Etiquetas iniciales para los Select
        self.fields['unidad_adscrita'].empty_label = "--- SELECCIONE UNIDAD ---"
        self.fields['estado'].empty_label = "--- SELECCIONE ESTADO ---"
        self.fields['municipio'].empty_label = "--- SELECCIONE MUNICIPIO ---"
        self.fields['parroquia'].empty_label = "--- SELECCIONE PARROQUIA ---"
        self.fields['comuna'].empty_label = "--- SELECCIONE COMUNA (OPCIONAL) ---"

        # Inicializamos los querysets como vacíos para optimizar carga inicial
        self.fields['municipio'].queryset = Municipio.objects.none()
        self.fields['parroquia'].queryset = Parroquia.objects.none()
        self.fields['comuna'].queryset = Comuna.objects.none()

        # RECONSTRUCCIÓN DE QUERYSETS: Vital para que Django acepte los datos de AJAX
        data = self.data if self.is_bound else {}
        
        # Cargar Municipios si hay un Estado seleccionado (en POST o en Instancia)
        estado_id = data.get('estado') or (self.instance.pk and self.instance.estado_id)
        if estado_id:
            try:
                self.fields['municipio'].queryset = Municipio.objects.filter(estado_id=estado_id).order_by('nombre')
            except (ValueError, TypeError):
                pass

        # Cargar Parroquias si hay un Municipio seleccionado
        municipio_id = data.get('municipio') or (self.instance.pk and self.instance.municipio_id)
        if municipio_id:
            try:
                self.fields['parroquia'].queryset = Parroquia.objects.filter(municipio_id=municipio_id).order_by('nombre')
            except (ValueError, TypeError):
                pass

        # Cargar Comunas si hay una Parroquia seleccionada
        parroquia_id = data.get('parroquia') or (self.instance.pk and self.instance.parroquia_id)
        if parroquia_id:
            try:
                self.fields['comuna'].queryset = Comuna.objects.filter(parroquia_id=parroquia_id).order_by('nombre')
            except (ValueError, TypeError):
                pass

    # --- Validaciones y Normalización ---
    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula', '').upper().strip()
        if Personal.objects.filter(cedula=cedula).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Ya existe un trabajador registrado con esta cédula.")
        return cedula

    def clean_nombres(self):
        return self.cleaned_data.get('nombres', '').upper().strip()

    def clean_apellidos(self):
        return self.cleaned_data.get('apellidos', '').upper().strip()

    def clean_cargo(self):
        return self.cleaned_data.get('cargo', '').upper().strip()
    
    def clean_direccion_exacta(self):
        return self.cleaned_data.get('direccion_exacta', '').upper().strip()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            return email.lower().strip()
        return email

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if telefono and not re.match(r'^[0-9\-]+$', telefono):
            raise ValidationError("El teléfono solo debe contener números y guiones.")
        return telefono

# ==============================================================================
# 3. GESTIÓN DE DOCUMENTOS (EXPEDIENTE)
# ==============================================================================
class SubirDocumentoForm(forms.ModelForm):
    class Meta:
        model = DocumentoPersonal
        fields = ['nombre_documento', 'categoria', 'archivo']
        widgets = {
            'nombre_documento': forms.TextInput(attrs={'class': 'form-input', 'readonly': 'readonly'}),
            'categoria': forms.HiddenInput(),
            'archivo': forms.FileInput(attrs={'class': 'form-input', 'accept': 'application/pdf'}),
        }
    
    def clean_archivo(self):
        archivo = self.cleaned_data.get('archivo')
        if archivo:
            if archivo.size > 2 * 1024 * 1024:
                raise ValidationError("El archivo excede los 2 MB permitidos.")
            if not archivo.name.lower().endswith('.pdf'):
                raise ValidationError("Solo se permiten archivos en formato PDF.")
        return archivo