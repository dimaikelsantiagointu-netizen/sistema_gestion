from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import Permission
from .models import Usuario

# Clase auxiliar para mostrar el nombre legible del permiso en lugar del código técnico
class PermissionModelChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name}"

# Lista unificada de tus 9 permisos para evitar errores de escritura
MODULO_PERMISSIONS = [
    "ver_gestor_recibos", 
    "ver_gestor_clientes", 
    "ver_gestor_pagos",
    "ver_gestor_contratos", 
    "ver_gestor_sellos", 
    "ver_gestor_documental",
    "ver_gestor_bienes",
    "ver_gestion_geografica",
    "ver_gestor_personal"
]

class CustomUserCreationForm(UserCreationForm):
    user_permissions = PermissionModelChoiceField(
        queryset=Permission.objects.filter(codename__in=MODULO_PERMISSIONS),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Accesos a Módulos"
    )

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email', 'telefono', 'rol', 'observacion', 'user_permissions')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'user_permissions':
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
        queryset=Permission.objects.filter(codename__in=MODULO_PERMISSIONS),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Accesos a Módulos"
    )

    class Meta:
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email', 'telefono', 'rol', 'observacion', 'user_permissions')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Help text estilizado para la contraseña
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
                
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ('first_name', 'last_name', 'email', 'telefono')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'mt-1 block w-full bg-gray-50 border-none rounded-xl text-sm focus:ring-2 focus:ring-intu-blue/10 font-bold'
            })
        self.fields['email'].required = True