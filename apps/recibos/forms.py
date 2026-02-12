from django import forms
from .models import Recibo 
from django.core.exceptions import ValidationError
from unidecode import unidecode

# CLASE BASE PARA LA MAYORÍA DE LOS INPUTS
TAILWIND_CLASS = 'form-input w-full rounded-lg border border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 transition duration-150'
DATE_INPUT_CLASS = TAILWIND_CLASS

class ReciboForm(forms.ModelForm):
    # 1. NORMALIZACIÓN DE DATOS (clean methods)

    def clean_nombre(self):
        data = self.cleaned_data.get('nombre', '').strip()
        return data.title()

    def clean_rif_cedula_identidad(self):
        data = self.cleaned_data.get('rif_cedula_identidad', '').strip().upper()
        return data.replace(' ', '').replace('-', '')
    
    def clean_ente_liquidado(self):
        data = self.cleaned_data.get('ente_liquidado', '').strip()
        return data.upper()
    
    def clean_estado(self):
        data = self.cleaned_data.get('estado', '').strip()
        if data:
            data_sin_acentos = unidecode(data)
            return data_sin_acentos.upper()
        return data
    
    def clean_numero_transferencia(self):
        # 1. Obtenemos el dato y normalizamos a Mayúsculas
        data = self.cleaned_data.get('numero_transferencia', '').strip().upper()
        
        # 2. Si el campo está vacío, no validamos duplicados
        if not data:
            return None

        # 3. VALIDACIÓN DE DUPLICADOS
        # Buscamos si existe otro recibo con este número.
        # .exclude(pk=self.instance.pk) es vital para que al EDITAR no te diga que ya existe.
        qs = Recibo.objects.filter(numero_transferencia=data)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise ValidationError(
                f"ALERTA: El número de transferencia '{data}' ya fue registrado en otro recibo. Por favor, verifique el comprobante."
            )
            
        return data

    # 2. META y WIDGETS
    class Meta:
        model = Recibo
        
        fields = [
            'numero_recibo', 
            'estado',
            'nombre',
            'rif_cedula_identidad',
            'direccion_inmueble',
            'ente_liquidado',
            'categoria1',
            'categoria2',
            'categoria3',
            'categoria4',
            'categoria5',
            'categoria6',
            'categoria7',
            'categoria8',
            'categoria9',
            'categoria10',
            'gastos_administrativos',
            'tasa_dia',
            'total_monto_bs',
            'numero_transferencia',
            'conciliado',
            'fecha', 
            'concepto',
        ]
        
        labels = {
            'categoria1': '1.Título Tierra Urbana',
            'categoria2': '2.Título + Vivienda',
            'categoria3': '3.Municipal',
            'categoria4': '4.Tierra Privada',
            'categoria5': '5.Tierra INAVI',
            'categoria6': '6.Excedentes Título',
            'categoria7': '7.Excedentes INAVI',
            'categoria8': '8.Estudios Técnico',
            'categoria9': '9.Locales Comerciales',
            'categoria10': '10.Arrendamiento Terrenos',
            'conciliado': 'Conciliado (Pago Confirmado)',
            'gastos_administrativos': 'Gastos Admin.',
            'tasa_dia': 'Tasa del Día (BCV)',
        }
        
        widgets = {
            'numero_recibo': forms.TextInput(attrs={
                'readonly': 'readonly', 
                'class': 'mt-1 block w-full rounded-lg border border-gray-300 bg-gray-100 shadow-inner text-gray-700 font-semibold' 
            }),

            'estado': forms.TextInput(attrs={'class': TAILWIND_CLASS}),
            'nombre': forms.TextInput(attrs={'class': TAILWIND_CLASS}),
            'rif_cedula_identidad': forms.TextInput(attrs={'class': TAILWIND_CLASS}),
            'direccion_inmueble': forms.Textarea(attrs={'class': TAILWIND_CLASS, 'rows': 2}),
            'ente_liquidado': forms.TextInput(attrs={'class': TAILWIND_CLASS}),
            
            'gastos_administrativos': forms.NumberInput(attrs={'class': TAILWIND_CLASS, 'step': '0.01'}),
            'tasa_dia': forms.NumberInput(attrs={'class': TAILWIND_CLASS, 'step': '0.0001'}),
            'total_monto_bs': forms.NumberInput(attrs={'class': TAILWIND_CLASS, 'step': '0.01'}),
            
            'numero_transferencia': forms.TextInput(attrs={
                'class': TAILWIND_CLASS,
                'placeholder': 'Ingrese el número de referencia'
            }),
            
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': DATE_INPUT_CLASS}), 
            'concepto': forms.Textarea(attrs={'class': TAILWIND_CLASS, 'rows': 2}),
        }