from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    ADMIN = 'admin'
    USER = 'user'
    SUPERADMIN = 'superadmin' # Nuevo Rol
    
    ROLES_CHOICES = [
        (SUPERADMIN, 'SuperUsuario'),
        (ADMIN, 'Administrador'),
        (USER, 'Usuario '),
    ]
    
    rol = models.CharField(
        max_length=15, 
        choices=ROLES_CHOICES, 
        default=USER,
        verbose_name="Rol del sistema"
    )
    
    # Nuevos campos solicitados
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