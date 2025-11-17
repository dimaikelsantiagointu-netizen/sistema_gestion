# Guía de Contribución

## 🚀 Empezando

### Prerrequisitos
- Python 3.8+
- Git
- VS Code (recomendado)

### Configuración del Entorno
```bash
# Clonar el repositorio
git clone https://github.com/dimaikelsantiagointu-netizen/sistema_gestion.git
cd sistema_gestion

# Configurar entorno virtual
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements/development.txt

# Configurar variables de entorno
cp .env.example .env

# Ejecutar migraciones
python manage.py migrate

# Ejecutar servidor de desarrollo
python manage.py runserver