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
        fields = ('username', 'first_name', 'last_name', 'email', 'cedula', 'telefono', 'rol', 'user_permissions')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'user_permissions':
                field.widget.attrs.update({'class': 'block w-full px-4 py-2 mt-1 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm'})

# ESTA ES LA CLASE QUE DABA EL ERROR. Asegúrate de que el nombre sea IDÉNTICO
class CustomUserChangeForm(UserChangeForm):
    # Sobreescribimos el campo password para personalizar el mensaje
    password = forms.CharField(
        widget=forms.HiddenInput(), # Lo ocultamos para que no se vea el input
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
        fields = ('username', 'first_name', 'last_name', 'email', 'cedula', 'telefono', 'rol', 'user_permissions')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personalizamos el mensaje de ayuda de la contraseña
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
                field.widget.attrs.update({
                    'class': 'block w-full px-4 py-2 mt-1 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm'
                })