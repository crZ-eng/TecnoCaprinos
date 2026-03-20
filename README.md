## TecnoCaprinos

### Descripción

TecnoCaprinos es un proyecto Django para gestionar y monitorear operaciones en granjas caprinas.

### Requisitos

- Python 3.8+
- Django 4.0+
- pip

### Instalación

1. Clonar el repositorio
2. Crear un entorno virtual: `python -m venv venv`
3. Activar el entorno: `source venv/bin/activate` (Linux/Mac) o `venv\Scripts\activate` (Windows)
4. Instalar dependencias: `pip install -r requirements.txt`
5. Aplicar migraciones: `python manage.py migrate`

### Uso

Ejecutar el servidor de desarrollo:
```bash
python manage.py runserver
```

Acceder a `http://127.0.0.1:8000/`

### Estructura del Proyecto

- `manage.py` - Utilidad de línea de comandos
- `TecnoCaprinos/` - Configuración principal
- `apps/` - Aplicaciones Django