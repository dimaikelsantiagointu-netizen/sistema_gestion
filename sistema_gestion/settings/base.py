import os
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-clave-temporal-cambiar-en-produccion')

DEBUG = os.getenv('DEBUG', 'False') == 'True' 

# En producción, asegúrate de configurar ALLOWED_HOSTS correctamente
ALLOWED_HOSTS = ['192.168.0.102', 'localhost', '127.0.0.1']

INSTALLED_APPS = [
    # APPS ESTÁNDAR DE DJANGO
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django.contrib.humanize',
    # NUEVAS APPS:
    'apps.recibos.apps.RecibosConfig',
    'apps.users',
    'apps.beneficiarios',#Tambien encargada de los expedientes de los beneficiarios y personal
    'apps.personal',#App para gestion de personal
    'apps.contratos', 
    #'apps.bienes', #App para gestion de bienes nacionales, actualmente en desarrollo
    'apps.territorio',#app para gestion de estados, municipios, ciudades, parroquias y comunas
    'apps.auditoria', #App para gestion de auditoria y bitacora de eventos
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.auditoria.middleware.AuditoriaMiddleware', # Middleware personalizado para APP de auditoría
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
        # Motor PostgreSQL.
        'ENGINE': 'django.db.backends.postgresql', 
        
        'NAME': os.environ.get('DB_NAME', 'django_default_db'), 
        'USER': os.environ.get('DB_USER', 'postgres'),  
        'PASSWORD': os.environ.get('DB_PASSWORD', '123456'), 
        
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# 3. AUTENTICACIÓN Y LOCALIZACIÓN

LOGIN_URL = 'login' 

LOGIN_REDIRECT_URL = 'home'

LOGOUT_REDIRECT_URL = 'login' 

AUTH_USER_MODEL = 'users.Usuario'
AUTH_PASSWORD_VALIDATORS = [
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

# 4. ARCHIVOS ESTÁTICOS Y MEDIA
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static'),]

STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 5. DOMINIO PARA GENERACIÓN DE CÓDIGOS QR usanndo el modelo BienNacional
SITE_DOMAIN = os.getenv('SITE_DOMAIN', 'http://127.0.0.1:8000')
#Agregar SITE_DOMAIN al .env con el dominio real en producción, ej: 'https://www.tu-sitio.com'


# --- CONFIGURACIÓN DE SESIÓN POR INACTIVIDAD ---
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE =  5 * 60
SESSION_SAVE_EVERY_REQUEST = True
