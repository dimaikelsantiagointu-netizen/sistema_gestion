from django import forms
from .models import UnidadAdscrita

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