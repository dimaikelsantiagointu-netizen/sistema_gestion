from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import Permission
from .models import Usuario

# Clase auxiliar para etiquetas limpias
class PermissionModelChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name}"

class CustomUserCreationForm(UserCreationForm):
    user_permissions = PermissionModelChoiceField(
        queryset=Permission.objects.filter(
            codename__in=[
                "ver_gestor_recibos", "ver_gestor_clientes", "ver_gestor_pagos",
                "ver_gestor_contratos", "ver_gestor_sellos", "ver_gestor_documental"
            ]
        ),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Accesos a Módulos"
    )

    class Meta(UserCreationForm.Meta):
        model = Usuario
        # Se elimina 'cedula' y se agrega 'observacion'
        fields = ('username', 'first_name', 'last_name', 'email', 'telefono', 'rol', 'observacion', 'user_permissions')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'user_permissions':
                # Widget específico para observación para que sea un cuadro de texto más grande
                if name == 'observacion':
                    field.widget = forms.Textarea(attrs={'rows': 3})
                
                field.widget.attrs.update({
                    'class': 'block w-full px-4 py-2 mt-1 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm'
                })

class CustomUserChangeForm(UserChangeForm):
    password = forms.CharField(
        widget=forms.HiddenInput(), 
        required=False,
        label="Contraseña"
    )

    user_permissions = PermissionModelChoiceField(
        queryset=Permission.objects.filter(
            codename__in=[
                "ver_gestor_recibos", "ver_gestor_clientes", "ver_gestor_pagos",
                "ver_gestor_contratos", "ver_gestor_sellos", "ver_gestor_documental"
            ]
        ),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Accesos a Módulos"
    )

    class Meta:
        model = Usuario
        # Se elimina 'cedula' y se agrega 'observacion'
        fields = ('username', 'first_name', 'last_name', 'email', 'telefono', 'rol', 'observacion', 'user_permissions')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if 'password' in self.fields:
            self.fields['password'].help_text = (
                '<span class="text-indigo-700 font-bold">'
                '<i class="fas fa-info-circle mr-1"></i> '
                'Para cambiar la contraseña de este usuario, por favor diríjase al '
                '<a href="/admin/users/usuario/" class="underline hover:text-indigo-900">Centro de Administración de Django</a>.'
                '</span>'
            )
            
        for name, field in self.fields.items():
            if name != 'user_permissions':
                if name == 'observacion':
                    field.widget = forms.Textarea(attrs={'rows': 3})
                
                field.widget.attrs.update({
                    'class': 'block w-full px-4 py-2 mt-1 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm'
                })