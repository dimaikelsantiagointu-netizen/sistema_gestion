import os
from dotenv import load_dotenv
from .base import * 

load_dotenv() 

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Configuración de email para desarrollo
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# -----------------------------------------------------------------
# Base de datos PostgreSQL (SOBRESCRITA desde .env)
# -----------------------------------------------------------------
DATABASES = {
    'default': {
        # Motor PostgreSQL
        'ENGINE': 'django.db.backends.postgresql', 
        
        # Lectura de variables de entorno con valores por defecto (fallback)
        # Esto previene errores si la variable no se encuentra en el .env
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        
        # Host y Puerto
        'HOST': os.environ.get('DB_HOST', 'localhost'), # Si no está en .env, usa 'localhost'
        'PORT': os.environ.get('DB_PORT', '5432'),     # Si no está en .env, usa '5432'
    }
}