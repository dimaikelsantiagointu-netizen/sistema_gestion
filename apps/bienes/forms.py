from django import forms
from .models import *

# Clase base para todos los inputs para mantener consistencia
CLASS_INPUT = (
    "w-full px-4 py-3 rounded-xl border border-gray-100 bg-gray-50/50 "
    "focus:border-intu-blue focus:ring-4 focus:ring-blue-50 outline-none "
    "transition-all text-sm font-medium placeholder:text-gray-300"
)

# ==========================
# FORMULARIOS DE EMPLEADOS
# ==========================
class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = '__all__'
        widgets = {
            'nombre': forms.TextInput(attrs={'class': CLASS_INPUT, 'placeholder': 'Ej. Juan'}),
            'apellido': forms.TextInput(attrs={'class': CLASS_INPUT, 'placeholder': 'Ej. Pérez'}),
            'cedula': forms.TextInput(attrs={'class': CLASS_INPUT, 'placeholder': 'V-00.000.000'}),
            'cargo': forms.TextInput(attrs={'class': CLASS_INPUT}),
            'unidad_trabajo': forms.Select(attrs={'class': CLASS_INPUT}),
            'estatus': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-gray-300 text-intu-blue focus:ring-intu-blue'}),
        }

# ==========================
# FORMULARIOS DE BIENES
# ==========================
class BienForm(forms.ModelForm):
    class Meta:
        model = BienNacional
        # En lugar de __all__, mejor deja que exclude maneje el resto
        exclude = ['qr_imagen', 'uuid', 'fecha_registro'] 
        
        widgets = {
            'nro_identificacion': forms.TextInput(attrs={'class': CLASS_INPUT}),
            'subcuenta': forms.TextInput(attrs={'class': CLASS_INPUT}),
            'descripcion': forms.Textarea(attrs={'class': CLASS_INPUT, 'rows': '2', 'placeholder': 'Descripción...'}),
            'marca': forms.TextInput(attrs={'class': CLASS_INPUT}),
            'modelo': forms.TextInput(attrs={'class': CLASS_INPUT}),
            'color': forms.TextInput(attrs={'class': CLASS_INPUT}),
            'serial': forms.TextInput(attrs={'class': CLASS_INPUT}),
            'monto': forms.NumberInput(attrs={'class': CLASS_INPUT, 'step': '0.01'}),
            'estado_bien': forms.Select(attrs={'class': CLASS_INPUT}),
            'empleado_uso': forms.Select(attrs={'class': CLASS_INPUT}),
            'unidad_trabajo': forms.Select(attrs={'class': CLASS_INPUT}),
        }

    # Optimizamos las validaciones para evitar errores si el campo viene vacío
    def clean_serial(self):
        serial = self.cleaned_data.get('serial')
        if not serial:
            return serial
        
        qs = BienNacional.objects.filter(serial=serial)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise forms.ValidationError("Este serial ya está registrado.")
        return serial

    def clean_nro_identificacion(self):
        nro = self.cleaned_data.get('nro_identificacion')
        if not nro:
            return nro
            
        qs = BienNacional.objects.filter(nro_identificacion=nro)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
            
        if qs.exists():
            raise forms.ValidationError("Este número de identificación ya existe.")
        return nro

# ==========================
# CARGA MASIVA
# ==========================
class CargaMasivaForm(forms.Form):
    archivo = forms.FileField(widget=forms.FileInput(attrs={'class': CLASS_INPUT}))