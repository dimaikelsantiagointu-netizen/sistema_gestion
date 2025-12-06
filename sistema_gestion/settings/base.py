import os
from pathlib import Path
from dotenv import load_dotenv


# Cargar las variables de entorno del archivo .env (debe estar en el BASE_DIR)
load_dotenv()

# Construye rutas dentro del proyecto como esta: BASE_DIR / 'sub_path'
# Nota: Asumiendo que settings.py está en sistema_gestion/, y la raíz del proyecto es dos niveles arriba.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# -----------------------------------------------------------------
# 1. SEGURIDAD Y DEBUG
# -----------------------------------------------------------------
# Lee la clave secreta desde el .env
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-clave-temporal-cambiar-en-produccion')

# DEBUG: Aseguramos que se lea como booleano si la variable existe
DEBUG = os.getenv('DEBUG', 'False') == 'True' # 'True' o 'False' se convierte a bool.

# ALLOWED_HOSTS: Debe configurarse si DEBUG=False
ALLOWED_HOSTS = ['127.0.0.1', 'localhost'] # Añadimos hosts comunes

INSTALLED_APPS = [
    # APPS ESTÁNDAR DE DJANGO
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # NUEVAS APPS: Añade aquí las nuevas apps que vayas creando
    'apps.recibos.apps.RecibosConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sistema_gestion.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # DIRS: Busca plantillas globales (base.html, landing_page.html, registration/login.html)
        # en la carpeta raíz del proyecto (SISTEMA_GESTION-MAIN/templates/)
        'DIRS': [BASE_DIR / 'templates'], 
        
        # APP_DIRS: Busca plantillas específicas de la aplicación (apps/nombre_app/templates/nombre_app/...)
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sistema_gestion.wsgi.application'

# -----------------------------------------------------------------
# 2. CONFIGURACIÓN DE LA BASE DE DATOS POSTGRESQL (LEÍDA DESDE .ENV)
# -----------------------------------------------------------------
DATABASES = {
    'default': {
        # Motor PostgreSQL. Esta configuración SOBREESCRIBE la de base.py/default.
        'ENGINE': 'django.db.backends.postgresql', 
        
        # Lectura de variables de entorno. 
        # Si la variable no existe en el .env, usa el valor por defecto ('fallback_...')
        # Se ha cambiado el valor por defecto de NAME a un nombre genérico
        'NAME': os.environ.get('DB_NAME', 'django_default_db'), 
        'USER': os.environ.get('DB_USER', 'postgres'),  
        'PASSWORD': os.environ.get('DB_PASSWORD', '123456'), 
        
        # Host y Puerto
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# -----------------------------------------------------------------
# 3. AUTENTICACIÓN Y LOCALIZACIÓN
# -----------------------------------------------------------------

# Configuración de URLs de autenticación
# Se usan los valores predeterminados de Django
LOGIN_URL = '/accounts/login/' 

# Se usan los valores predeterminados de Django
LOGIN_REDIRECT_URL = '/accounts/profile/'

# Se usan los valores predeterminados de Django
LOGOUT_REDIRECT_URL = '/' 

AUTH_PASSWORD_VALIDATORS = [
    # ... (Sin cambios)
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

LANGUAGE_CODE = 'es-ve'
TIME_ZONE = 'America/Caracas'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# -----------------------------------------------------------------
# 4. ARCHIVOS ESTÁTICOS Y MEDIA
# -----------------------------------------------------------------
STATIC_URL = 'static/'
# Usamos la sintaxis moderna con Path
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static'),]

STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'