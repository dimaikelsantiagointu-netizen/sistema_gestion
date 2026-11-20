from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.territorio.models import Comuna, Estado, Municipio, Parroquia

from .models import (
    EstatusDocumento,
    Expediente,
    Titular,
    validate_pdf_file,
)


INPUT_CLASS = (
    'block w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 '
    'text-sm font-semibold text-slate-700 outline-none transition '
    'focus:border-intu-blue focus:bg-white focus:ring-4 focus:ring-intu-blue/5'
)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiplePDFField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            if self.required:
                raise ValidationError(self.error_messages['required'], code='required')
            return []

        uploads = data if isinstance(data, (list, tuple)) else [data]
        archivos_limpios = []
        for upload in uploads:
            archivo = super().clean(upload, initial)
            validate_pdf_file(archivo)
            archivos_limpios.append(archivo)
        return archivos_limpios


class ExpedienteForm(forms.ModelForm):
    archivos = MultiplePDFField(
        required=False,
        label='Archivos PDF (máximo 5 MB cada uno)',
        help_text='Puedes seleccionar varios PDF. Cada archivo puede pesar hasta 5 MB.',
    )

    class Meta:
        model = Expediente
        fields = [
            'estado',
            'municipio',
            'parroquia',
            'comuna',
            'titular',
            'numero_protocolo',
            'numero_tomo',
            'fecha_registro',
            'superficie_m2',
            'direccion',
            'lindero_norte',
            'lindero_sur',
            'lindero_este',
            'lindero_oeste',
            'estatus',
            'observaciones',
        ]
        widgets = {
            'estado': forms.Select(attrs={'class': INPUT_CLASS}),
            'municipio': forms.Select(attrs={'class': INPUT_CLASS}),
            'parroquia': forms.Select(attrs={'class': INPUT_CLASS}),
            'comuna': forms.Select(attrs={'class': INPUT_CLASS}),
            'titular': forms.Select(attrs={'class': INPUT_CLASS}),
            'numero_protocolo': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'numero_tomo': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'fecha_registro': forms.DateInput(
                attrs={'class': INPUT_CLASS, 'type': 'date'},
                format='%Y-%m-%d',
            ),
            'superficie_m2': forms.NumberInput(
                attrs={'class': INPUT_CLASS, 'min': '0.01', 'step': '0.01'},
            ),
            'direccion': forms.Textarea(
                attrs={'class': INPUT_CLASS, 'rows': 3},
            ),
            'lindero_norte': forms.Textarea(
                attrs={'class': INPUT_CLASS, 'rows': 2},
            ),
            'lindero_sur': forms.Textarea(
                attrs={'class': INPUT_CLASS, 'rows': 2},
            ),
            'lindero_este': forms.Textarea(
                attrs={'class': INPUT_CLASS, 'rows': 2},
            ),
            'lindero_oeste': forms.Textarea(
                attrs={'class': INPUT_CLASS, 'rows': 2},
            ),
            'estatus': forms.Select(attrs={'class': INPUT_CLASS}),
            'observaciones': forms.Textarea(
                attrs={'class': INPUT_CLASS, 'rows': 3},
            ),
            'archivos': MultipleFileInput(
                attrs={'class': 'sr-only', 'accept': '.pdf,application/pdf'},
            ),
        }
        labels = {
            'numero_protocolo': 'Número de protocolo',
            'numero_tomo': 'Número de tomo',
            'superficie_m2': 'Superficie en metros cuadrados',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        estado_id = self.data.get('estado') if self.is_bound else self.instance.estado_id
        municipio_id = (
            self.data.get('municipio') if self.is_bound else self.instance.municipio_id
        )
        parroquia_id = (
            self.data.get('parroquia') if self.is_bound else self.instance.parroquia_id
        )

        self.fields['estado'].queryset = Estado.objects.order_by('nombre')
        self.fields['municipio'].queryset = Municipio.objects.none()
        self.fields['parroquia'].queryset = Parroquia.objects.none()
        self.fields['comuna'].queryset = Comuna.objects.none()
        if estado_id:
            self.fields['municipio'].queryset = Municipio.objects.filter(
                estado_id=estado_id,
            ).order_by('nombre')
        if municipio_id:
            self.fields['parroquia'].queryset = Parroquia.objects.filter(
                municipio_id=municipio_id,
            ).order_by('nombre')
        if parroquia_id:
            self.fields['comuna'].queryset = Comuna.objects.filter(
                parroquia_id=parroquia_id,
            ).order_by('nombre')

        titulares = Titular.objects.filter(activo=True)
        estatuses = EstatusDocumento.objects.filter(activo=True)
        if self.instance.pk:
            titulares = Titular.objects.filter(
                Q(pk=self.instance.titular_id) | Q(activo=True)
            )
            estatuses = EstatusDocumento.objects.filter(
                Q(pk=self.instance.estatus_id) | Q(activo=True)
            )
        self.fields['titular'].queryset = titulares.order_by('nombre')
        self.fields['estatus'].queryset = estatuses.order_by('orden', 'nombre')
        self.fields['archivos'].widget.attrs.update(
            {'class': 'sr-only', 'accept': '.pdf,application/pdf', 'multiple': True},
        )
        if self.instance.pk:
            self.fields['archivos'].help_text = (
                'Los archivos nuevos se agregan al expediente. '
                'Cada PDF puede pesar hasta 5 MB.'
            )

    def clean_archivos(self):
        archivos = self.cleaned_data.get('archivos', [])
        if not self.instance.pk and not archivos:
            raise ValidationError('Adjunta al menos un archivo PDF.')
        return archivos


class TitularForm(forms.ModelForm):
    class Meta:
        model = Titular
        fields = ['nombre', 'documento_identidad', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': INPUT_CLASS, 'autofocus': True}),
            'documento_identidad': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'activo': forms.CheckboxInput(
                attrs={'class': 'h-4 w-4 rounded border-slate-300 text-intu-blue'},
            ),
        }


class EstatusDocumentoForm(forms.ModelForm):
    class Meta:
        model = EstatusDocumento
        fields = ['nombre', 'orden', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': INPUT_CLASS, 'autofocus': True}),
            'orden': forms.NumberInput(
                attrs={'class': INPUT_CLASS, 'min': 0, 'step': 1},
            ),
            'activo': forms.CheckboxInput(
                attrs={'class': 'h-4 w-4 rounded border-slate-300 text-intu-blue'},
            ),
        }


class ExpedienteDashboardFilterForm(forms.Form):
    estado = forms.ModelChoiceField(
        queryset=Estado.objects.none(),
        required=False,
        empty_label='Todos los estados',
        widget=forms.Select(attrs={'class': INPUT_CLASS}),
    )
    estatus = forms.ModelChoiceField(
        queryset=EstatusDocumento.objects.none(),
        required=False,
        empty_label='Todos los estatus',
        widget=forms.Select(attrs={'class': INPUT_CLASS}),
    )
    titular = forms.ModelChoiceField(
        queryset=Titular.objects.none(),
        required=False,
        empty_label='Todos los titulares',
        widget=forms.Select(attrs={'class': INPUT_CLASS}),
    )
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': INPUT_CLASS, 'type': 'date'}),
    )
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': INPUT_CLASS, 'type': 'date'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['estado'].queryset = Estado.objects.order_by('nombre')
        self.fields['estatus'].queryset = EstatusDocumento.objects.order_by(
            'orden',
            'nombre',
        )
        self.fields['titular'].queryset = Titular.objects.order_by('nombre')

    def clean(self):
        cleaned_data = super().clean()
        desde = cleaned_data.get('fecha_desde')
        hasta = cleaned_data.get('fecha_hasta')
        if desde and hasta and desde > hasta:
            self.add_error('fecha_hasta', 'La fecha final debe ser posterior a la inicial.')
        return cleaned_data
