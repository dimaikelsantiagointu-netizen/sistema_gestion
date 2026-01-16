from django.contrib.auth.models import AbstractUser, Permission
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class Usuario(AbstractUser):
    ADMIN = 'admin'
    USER = 'user'
    SUPERADMIN = 'superadmin'
    
    ROLES_CHOICES = [
        (SUPERADMIN, 'SuperUsuario'),
        (ADMIN, 'Administrador'),
        (USER, 'Usuario'),
    ]
    
    rol = models.CharField(
        max_length=15, 
        choices=ROLES_CHOICES, 
        default=USER,
        verbose_name="Rol del sistema"
    )
    
    cedula = models.CharField(max_length=20, unique=True, verbose_name="Cédula/ID", null=True, blank=True)
    telefono = models.CharField(max_length=20, verbose_name="Teléfono", null=True, blank=True)

    class Meta:
        permissions = [
            ("ver_gestor_recibos", "Acceso al Gestor de Recibos"),
            ("ver_gestor_clientes", "Acceso al Gestor de Clientes"),
            ("ver_gestor_pagos", "Acceso al Sistema de Pagos"),
            ("ver_gestor_contratos", "Acceso al Gestor de Contratos"),
            ("ver_gestor_sellos", "Acceso al Gestor de Sellos"),
            ("ver_gestor_documental", "Acceso a la Gestión Documental"),
        ]

    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"

# --- SEÑAL PARA AUTOMATIZAR SUPERUSUARIOS DE TERMINAL ---
@receiver(post_save, sender=Usuario)
def configurar_superusuario_nuevo(sender, instance, created, **kwargs):

    if created and instance.is_superuser:
        # 1. Asignar el rol visual
        if instance.rol != Usuario.SUPERADMIN:
            instance.rol = Usuario.SUPERADMIN
            # Usamos update para evitar disparar la señal de nuevo infinitamente
            Usuario.objects.filter(pk=instance.pk).update(rol=Usuario.SUPERADMIN)

        # 2. Asignar todos tus permisos personalizados automáticamente
        # Accedemos a los permisos definidos en el Meta de forma correcta:
        codigos_permisos = [p[0] for p in instance._meta.permissions]
        
        permisos = Permission.objects.filter(codename__in=codigos_permisos)
        instance.user_permissions.add(*permisos)