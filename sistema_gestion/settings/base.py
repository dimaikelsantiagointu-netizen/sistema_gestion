import os
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-clave-temporal-cambiar-en-produccion')

DEBUG = os.getenv('DEBUG', 'False') == 'True' # 'True' o 'False' se convierte a bool.

ALLOWED_HOSTS = ['127.0.0.1', 'localhost'] # Añadimos hosts comunes

INSTALLED_APPS = [
    # APPS ESTÁNDAR DE DJANGO
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
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
        'DIRS': [os.path.join(BASE_DIR, 'templates')],        
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

DATABASES = {
    'default': {
        # Motor PostgreSQL. Esta configuración SOBREESCRIBE la de base.py/default.
        'ENGINE': 'django.db.backends.postgresql', 
        
        'NAME': os.environ.get('DB_NAME', 'django_default_db'), 
        'USER': os.environ.get('DB_USER', 'postgres'),  
        'PASSWORD': os.environ.get('DB_PASSWORD', '123456'), 
        
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