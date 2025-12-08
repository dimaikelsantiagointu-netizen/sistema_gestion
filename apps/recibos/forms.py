from django import forms
from .models import Recibo, MAPEO_CATEGORIAS


class ExcelUploadForm(forms.Form):
    """
    Formulario para la subida de archivos Excel.
    Utilizado en la vista ExcelUploadView.
    """
    excel_file = forms.FileField(
        label='Archivo de Recibos (Excel .xlsx)',
        required=True,
        widget=forms.FileInput(attrs={
            'accept': '.xlsx, .xls',
            'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'
        })
    )


class ReciboModelForm(forms.ModelForm):
    """
    Formulario principal para crear o editar un objeto Recibo.
    Utilizado en ReciboCreateView y ReciboUpdateView.
    """
    
    anular_recibo = forms.BooleanField(
        label='Marcar como Anulado', 
        required=False,
        help_text='Marque esta casilla para anular este recibo.',
        widget=forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-red-600 border-gray-300 rounded'})
    )
    
    class Meta:
        model = Recibo
        
        fields = [
            'numero_recibo', 'fecha', 'estado', 'nombre', 'rif_cedula_identidad', 
            'direccion_inmueble', 'ente_liquidado', 'gastos_administrativos', 
            'tasa_dia', 'total_monto_bs', 'numero_transferencia', 'conciliado',
            'concepto', 
            'categoria1', 'categoria2', 'categoria3', 'categoria4', 'categoria5', 
            'categoria6', 'categoria7', 'categoria8', 'categoria9', 'categoria10',
            'anular_recibo', 
        ]
        
        widgets = {
            'numero_recibo': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'}),
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'}),
            'estado': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'}),
            'nombre': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'}),
            'rif_cedula_identidad': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'}),
            'direccion_inmueble': forms.Textarea(attrs={'rows': 2, 'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'}),
            'ente_liquidado': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'}),
            'gastos_administrativos': forms.NumberInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'}),
            'tasa_dia': forms.NumberInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'}),
            'total_monto_bs': forms.NumberInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'}),
            'numero_transferencia': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'}),
            'concepto': forms.Textarea(attrs={'rows': 2, 'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'}),
            'conciliado': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'}),
            **{f'categoria{i}': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500'}) for i in range(1, 11)}
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for i, label in MAPEO_CATEGORIAS.items():
            field_name = f'categoria{i}'
            if field_name in self.fields:
                self.fields[field_name].label = label
                
        if self.instance and self.instance.pk and self.instance.anulado:
            self.fields['anular_recibo'].initial = True

    def save(self, commit=True):
        """
        Sobreescribe el método save para manejar el campo 'anular_recibo' 
        y la lógica de anulación.
        """
        instance = super().save(commit=False)
        
        instance.anulado = self.cleaned_data.get('anular_recibo', False)
        
        if commit:
            instance.save()
        return instance
    
class ReporteFiltrosForm(forms.Form):
    fecha_inicio = forms.DateField(
        label="Fecha Inicio (Opcional)",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'})
    )
    fecha_fin = forms.DateField(
        label="Fecha Fin (Opcional)",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'})
    )
    
    ESTADO_REPORTE_CHOICES = [('Todos', 'Todos')] + list(Recibo.ESTADO_CHOICES) + [
        ('Activo', 'Solo Activos (No Anulados)'), 
        ('Anulado', 'Solo Anulados')
    ]
    estado_filtro = forms.ChoiceField(
        label="Filtrar por Estado",
        choices=ESTADO_REPORTE_CHOICES,
        initial='Todos',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    opciones_categorias = [(k, v) for k, v in MAPEO_CATEGORIAS.items()]
    
    categorias_filtro = forms.MultipleChoiceField(
        label="Categorías (Incluir recibos con alguna de estas marcadas)",
        choices=opciones_categorias,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'space-y-1'})
    )