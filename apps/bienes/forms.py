from django import forms
from .models import *

# ==========================
# FORMULARIOS DE EMPLEADOS
# ==========================
class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = '__all__'
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control'}),
            'cargo': forms.TextInput(attrs={'class': 'form-control'}),
            'unidad_trabajo': forms.Select(attrs={'class': 'form-control'}),
            'estatus': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
#==========================
# FORMULARIOS DE BIENES
# ==========================



class BienForm(forms.ModelForm):
    class Meta:
        model = BienNacional
        fields = '__all__'
        widgets = {
            'nro_identificacion': forms.TextInput(attrs={'class': 'form-control'}),
            'subcuenta': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'serial': forms.TextInput(attrs={'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control'}),
            'estado_bien': forms.Select(attrs={'class': 'form-control'}),
            'empleado_uso': forms.Select(attrs={'class': 'form-control'}),
            'unidad_trabajo': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_serial(self):
        serial = self.cleaned_data['serial']
        if BienNacional.objects.filter(serial=serial).exists():
            raise forms.ValidationError("Este serial ya está registrado.")
        return serial

    def clean_nro_identificacion(self):
        nro = self.cleaned_data['nro_identificacion']
        if BienNacional.objects.filter(nro_identificacion=nro).exists():
            raise forms.ValidationError("Este número de identificación ya existe.")
        return nro


#==========================
# carga masiva de bienes
# ==========================
class CargaMasivaForm(forms.Form):
    archivo = forms.FileField()