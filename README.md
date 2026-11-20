# 📊 Sistema de Gestión Documental

## 🚀 Guía Completa de Incorporación al Proyecto

### 📋 Tabla de Contenidos
- [Requisitos del Sistema](#-requisitos-del-sistema)
- [Configuración Inicial](#-configuración-inicial)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Flujo de Desarrollo](#-flujo-de-desarrollo)
- [Convenciones de Código](#-convenciones-de-código)
- [Módulos del Sistema](#-módulos-del-sistema)
- [Git y GitHub](#-git-y-github)
- [Despliegue](#-despliegue)
- [Soporte](#-soporte)

---

## 💻 Requisitos del Sistema

### Software Requerido
- **Python 3.8+** - [Descargar aquí](https://www.python.org/downloads/)
- **Git** - [Descargar aquí](https://git-scm.com/)
- **VS Code** (Recomendado) - [Descargar aquí](https://code.visualstudio.com/)
- **PostgreSQL** - [Descargar aquí](https://www.postgresql.org/)

### Extensiones VS Code Recomendadas
```json
{
    "recommendations": [
        "ms-python.python",
        "batisteo.vscode-django",
        "bibhasdn.django-html",
        "eamodio.gitlens",
        "rangav.vscode-thunder-client"
    ]
}
```

---

## ⚙️ Configuración Inicial

### 1. Clonar el Repositorio
```bash
git clone https://github.com/dimaikelsantiagointu-netizen/sistema_gestion.git
cd sistema_gestion
```

### 2. Configurar Entorno Virtual
```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Verificar que esté activado (debe aparecer (venv))
```

### 3. Instalar Dependencias
```bash
pip install --upgrade pip
pip install -r requirements/development.txt
```

### 4. Configurar Variables de Entorno
```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar .env con tus configuraciones
# SECRET_KEY=tu-clave-secreta-aqui
# DEBUG=True
```

### 5. Configurar Base de Datos
```bash
# Aplicar migraciones iniciales
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser
# Usuario: admin
# Email: admin@example.com
# Password: admin123
```

### 6. Verificar Instalación
```bash
# Ejecutar servidor de desarrollo
python manage.py runserver

# Abrir en navegador: http://127.0.0.1:8000/
# Deberías ver el sistema funcionando
```

---

# 📁 **Estructura del Proyecto - Sistema de Gestión Documental**

## 🏗️ **Arquitectura General del Proyecto**

```
sistema_gestion/                          # 🎯 RAÍZ DEL PROYECTO
├── 📁 .github/                           # ⚙️ Configuración GitHub
├── 📁 apps/                              # 🚀 Aplicaciones Django
├── 📁 requirements/                      # 📦 Dependencias del Proyecto
├── 📁 sistema_gestion/                   # ⚙️ Configuración Django
├── 📁 static/                            # 🎨 Archivos Estáticos
├── 📁 templates/                         # 🖥️ Plantillas HTML
├── 📄 .gitignore                         # 🙈 Archivos ignorados por Git
├── 📄 CONTRIBUTING.md                    # 👥 Guía para Colaboradores
├── 📄 manage.py                          # 🛠️ Script de Gestión Django
└── 📄 README.md                          # 📚 Documentación Principal
```

---

## 🔍 **Estructura Detallada por Carpeta**

### **1. 📁 .github/ - Configuración GitHub**
```
.github/
├── 📁 workflows/                         # 🤖 CI/CD Automatización
│   └── 📄 django-ci.yml                  # Pipeline de tests Django
├── 📁 ISSUE_TEMPLATE/                    # 📋 Plantillas de Issues
│   ├── 📄 bug_report.md                  # 🐛 Reporte de errores
│   ├── 📄 configuracion.md               # ⚙️ Solicitudes de configuración
│   └── 📄 feature_request.md             # ✨ Solicitudes de nuevas features
└── 📄 pull_request_template.md           # 🔄 Plantilla para Pull Requests
```

### **2. 📁 apps/ - Aplicaciones Django**
```
apps/
├── 📄 .gitkeep                           # 📌 Mantener estructura en Git
└── 📄 README.md                          # 📖 Documentación de apps
```
**Propósito:** Contiene todas las aplicaciones Django del sistema. Cada módulo (Clientes, Pagos, Contratos) será una app independiente aquí.

### **3. 📁 requirements/ - Gestión de Dependencias**
```
requirements/
└── 📄 development.txt                    # 🛠️ Dependencias desarrollo
```
**Archivos planeados:**
- `production.txt` - Dependencias producción
- `testing.txt` - Dependencias para testing

### **4. 📁 sistema_gestion/ - Configuración Django**
```
sistema_gestion/
├── 📁 settings/                          # ⚙️ Configuración Modular
│   ├── 📄 __init__.py                    # 🔗 Inicialización del módulo
│   ├── 📄 base.py                        # 🏗️ Configuración base común
│   ├── 📄 development.py                 # 💻 Configuración desarrollo
│   └── 📄 production.py                  # 🌐 Configuración producción
├── 📄 __init__.py                        # 🐍 Paquete Python
├── 📄 asgi.py                           # 🚀 ASGI configuration
├── 📄 urls.py                           # 🌐 URLs principales
└── 📄 wsgi.py                           # 🌐 WSGI configuration
```

### **5. 📁 static/ - Archivos Estáticos**
```
static/
├── 📁 css/                               # 🎨 Hojas de estilo
│   ├── 📄 .gitkeep                       # 📌 Mantener estructura
│   └── 📄 README.md                      # 📖 Documentación CSS
├── 📁 images/                            # 🖼️ Imágenes y assets
│   ├── 📄 .gitkeep                       # 📌 Mantener estructura
│   └── 📄 README.md                      # 📖 Documentación imágenes
└── 📁 js/                                # ⚡ JavaScript
    ├── 📄 .gitkeep                       # 📌 Mantener estructura
    └── 📄 README.md                      # 📖 Documentación JS
```

### **6. 📁 templates/ - Sistema de Plantillas**
```
templates/
├── 📁 registration/                      # 🔐 Autenticación
│   └── 📄 login.html                     # 🖥️ Pantalla de login personalizada
└── 📄 base.html                          # 🏗️ Plantilla base del proyecto
```

---

## 🗂️ **Estructura de Módulos Futuros**

### **📁 Apps Planeadas:**
```
apps/
├── 📁 clientes/                          # 👥 Gestión de Clientes
│   ├── 📁 migrations/
│   ├── 📁 static/clientes/
│   ├── 📁 templates/clientes/
│   ├── 📄 admin.py
│   ├── 📄 apps.py
│   ├── 📄 models.py
│   ├── 📄 tests.py
│   ├── 📄 urls.py
│   └── 📄 views.py
├── 📁 pagos/                             # 💰 Sistema de Pagos
├── 📁 contratos/                         # 📑 Gestión de Contratos
├── 📁 sellos/                            # 🏷️ Sellos Dorados
├── 📁 recibos/                           # 🧾 Generación de Recibos
└── 📁 expedientes/                       # 📂 Gestión de Expedientes
```

---

## 🔄 Flujo de Desarrollo

### Para Cada Nueva Funcionalidad

#### 1. Preparar Entorno
```bash
# Activar entorno virtual
venv\Scripts\activate

# Sincronizar con main
git checkout main
git pull origin main
```

#### 2. Crear Rama de Feature
```bash
git checkout -b feature/nombre-feature
# Ejemplos:
git checkout -b feature/agregar-modulo-pagos
git checkout -b feature/integrar-api-saime
git checkout -b fix/corregir-error-clientes
```

#### 3. Desarrollar la Funcionalidad

**Crear Nueva App:**
```bash
python manage.py startapp nombre_app apps/
```

**Estructura de Desarrollo:**
1. **Modelos** → `apps/nombre_app/models.py`
2. **Migraciones** → `python manage.py makemigrations`
3. **Admin** → `apps/nombre_app/admin.py`
4. **Vistas** → `apps/nombre_app/views.py`
5. **URLs** → `apps/nombre_app/urls.py`
6. **Templates** → `templates/nombre_app/`
7. **Forms** → `apps/nombre_app/forms.py`

#### 4. Commits Frecuentes
```bash
# Ejemplo de commits organizados:
git add apps/pagos/models.py
git commit -m "feat: crear modelo Pago con campos básicos"

git add apps/pagos/admin.py
git commit -m "feat: configurar interfaz admin para Pagos"

git add templates/pagos/
git commit -m "feat: crear plantillas para lista de pagos"
```

#### 5. Probar Localmente
```bash
# Aplicar migraciones
python manage.py makemigrations
python manage.py migrate

# Ejecutar servidor
python manage.py runserver

# Probar en: http://127.0.0.1:8000/
```

#### 6. Subir Cambios
```bash
git push origin feature/nombre-feature
```

#### 7. Crear Pull Request en GitHub
1. Ir a **Pull Requests** → **New Pull Request**
2. Seleccionar: `base: main` ← `compare: feature/nombre-feature`
3. Completar template del PR
4. Asignar revisores
5. **Create Pull Request**

---

## 📝 Convenciones de Código

### Commits
```bash
# Estructura: tipo: descripción
git commit -m "feat: agregar módulo de clientes"
git commit -m "fix: corregir validación de email"
git commit -m "docs: actualizar instrucciones de instalación"
git commit -m "refactor: optimizar consultas a BD"
git commit -m "style: formatear código según PEP8"
```

### Python/Django
- Seguir **PEP 8**
- Máximo **88 caracteres** por línea
- Usar **docstrings** en funciones y clases
- Nombres descriptivos en inglés

### Templates HTML
- Indentación de **2 espacios**
- Usar **Bootstrap 5** para estilos
- Seguir convenciones de **Django templates**

### Estructura de Apps
Cada app debe contener:
```python
# apps/nombre_app/apps.py
class NombreAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.nombre_app'
    verbose_name = 'Nombre Descriptivo'
```

---

## 🏗️ Módulos del Sistema

### Módulos Planificados
- **🔲 Clientes** - Gestión de información de clientes
- **🔲 Sellos Dorados** - Generación y gestión de sellos
- **🔲 Contratos** - Creación y seguimiento de contratos
- **🔲 Pagos** - Registro y control de pagos
- **🔲 Recibos** - Generación de comprobantes
- **🔲 Gestión de Expedientes** - Expedientes digitales de ciudadanos y personal

### Crear Nuevo Módulo
```bash
# Crear app del módulo
python manage.py startapp nombre_modulo apps/

# Configurar en settings.py
# INSTALLED_APPS += ['apps.nombre_modulo']

# Configurar URLs en sistema_gestion/urls.py
# path('nombre_modulo/', include('apps.nombre_modulo.urls')),
```

---

## 🔧 Git y GitHub

### Comandos Esenciales
```bash
# Estado del repositorio
git status

# Ver ramas
git branch

# Ver historial
git log --oneline -10

# Descargar cambios
git pull origin main

# Subir cambios
git push origin nombre-rama
```

### Resolución de Conflictos
Si hay conflictos al hacer pull:
```bash
git pull origin main
# Editar archivos con conflictos
git add .
git commit -m "Resolve merge conflicts"
git push origin main
```

### Flujo de Ramas
```
main (estable)
└── develop (desarrollo)
    ├── feature/nueva-funcionalidad
    ├── feature/otra-funcionalidad
    └── fix/correccion-error
```

---

## 🚀 Despliegue

### Entorno de Desarrollo
```bash
# Variables de entorno desarrollo
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
SECRET_KEY=clave-desarrollo
```

### Entorno de Producción
```env
DEBUG=False
ALLOWED_HOSTS=.dominio.com
DATABASE_URL=postgres://usuario:clave@host:puerto/bd
SECRET_KEY=clave-secreta-segura
```

### Comandos de Despliegue
```bash
# Colectar archivos estáticos
python manage.py collectstatic

# Aplicar migraciones
python manage.py migrate

# Crear superusuario producción
python manage.py createsuperuser
```

---

## 🆘 Soporte

### Canales de Comunicación
- **📧 Email**: equipo@empresa.com
- **💬 Slack**: #proyecto-gestion
- **🐛 Issues**: GitHub Issues

### Reportar Problemas
1. Verificar que no sea un error ya reportado
2. Usar template de bug report en GitHub
3. Incluir pasos para reproducir
4. Agregar capturas de pantalla si aplica

### Solicitar Características
1. Usar template de feature request
2. Describir el problema a resolver
3. Proponer solución si es posible
4. Definir criterios de aceptación

---

## ✅ Checklist de Incorporación

- [ ] Clonar repositorio
- [ ] Configurar entorno virtual
- [ ] Instalar dependencias
- [ ] Configurar variables de entorno
- [ ] Aplicar migraciones
- [ ] Crear superusuario
- [ ] Ejecutar servidor de desarrollo
- [ ] Probar acceso al sistema
- [ ] Leer convenciones de código
- [ ] Entender flujo de Git
- [ ] Probar crear PR en GitHub

---

## 🎯 Próximos Pasos

1. **Asignar módulo** según habilidades e interés
2. **Revisar documentación** específica del módulo
3. **Coordinar con equipo** dependencias entre módulos
4. **Establecer metas** y fechas de entrega
5. **Comenzar desarrollo** con rama feature

---

**¿Necesitas ayuda?** ¡No dudes en preguntar! El equipo está para apoyarte. 🚀

---
*Última actualización: $(date)*
