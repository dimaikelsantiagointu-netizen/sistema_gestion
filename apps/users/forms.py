# apps/users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import Permission
from .models import Usuario

# Creamos una clase personalizada para que los permisos se vean limpios
class PermissionModelChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        # En lugar de devolver el string por defecto, devolvemos solo la descripción
        return f"{obj.name}"

class CustomUserCreationForm(UserCreationForm):
    # Usamos nuestra nueva clase de campo aquí
    user_permissions = PermissionModelChoiceField(
        queryset=Permission.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Accesos a Módulos"
    )

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = (
            'username', 
            'first_name', 
            'last_name', 
            'email', 
            'cedula', 
            'telefono', 
            'rol',
            'user_permissions'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # FILTRO ESTRICTO: Solo tus 6 permisos personalizados
        codigos_permitidos = [
            "ver_gestor_recibos",
            "ver_gestor_clientes",
            "ver_gestor_pagos",
            "ver_gestor_contratos",
            "ver_gestor_sellos",
            "ver_gestor_documental",
        ]
        
        self.fields['user_permissions'].queryset = Permission.objects.filter(
            codename__in=codigos_permitidos
        ).order_by('name')

        # Estilización Tailwind para el resto de campos
        for field_name, field in self.fields.items():
            if field_name != 'user_permissions':
                field.widget.attrs.update({
                    'class': 'block w-full px-4 py-2 mt-1 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm',
                })