from django import forms

from .models import CategoriaVisita


class CategoriaVisitaForm(forms.ModelForm):
    class Meta:
        model = CategoriaVisita
        fields = ['nombre', 'orden', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'block w-full rounded-lg border border-slate-300 px-3 py-2',
                'autofocus': True,
            }),
            'orden': forms.NumberInput(attrs={
                'class': 'block w-full rounded-lg border border-slate-300 px-3 py-2',
                'min': 0,
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 rounded border-slate-300 text-intu-blue focus:ring-intu-blue',
            }),
        }
        labels = {
            'nombre': 'Nombre de la categoría',
            'orden': 'Orden en el selector',
            'activa': 'Disponible para nuevas visitas',
        }
