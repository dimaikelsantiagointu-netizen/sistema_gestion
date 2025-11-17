# Sistema de Gestión Documental

## 🚀 Configuración para Desarrolladores

### Prerrequisitos
- Python 3.8+
- Git
- VS Code (recomendado)

### Instalación
```bash
# 1. Clonar el proyecto
git clone https://github.com/dimaikelsantiagointu-netizen/sistema_gestion.git
cd sistema_gestion

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements/development.txt

# 5. Configurar variables de entorno
# Copiar .env.example a .env y editar

# 6. Ejecutar migraciones
python manage.py migrate

# 7. Crear superusuario (opcional)
python manage.py createsuperuser

# 8. Ejecutar servidor
python manage.py runserver
