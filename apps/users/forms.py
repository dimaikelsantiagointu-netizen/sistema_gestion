# apps/users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Usuario

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        # Incluimos los campos básicos de Django + tus campos personalizados
        fields = (
            'username', 
            'first_name', 
            'last_name', 
            'email', 
            'cedula', 
            'telefono', 
            'rol'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Bucle para aplicar estilos de Tailwind a todos los campos automáticamente
        for field_name, field in self.fields.items():
            # Clases base de Tailwind para tus inputs
            field.widget.attrs.update({
                'class': 'block w-full px-4 py-2 mt-1 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm',
            })
            
            # Si el campo tiene etiquetas (labels), las limpiamos o ajustamos
            if field.label:
                field.widget.attrs['placeholder'] = f'Ingrese {field.label.lower()}'

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = Usuario
        fields = ('username', 'email', 'rol', 'cedula', 'telefono')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'block w-full px-4 py-2 mt-1 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm',
            })