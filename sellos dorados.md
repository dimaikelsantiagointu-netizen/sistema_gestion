# Sellos Dorados

## ¿Qué es este módulo?

El módulo de Sellos Dorados es una funcionalidad institucional para gestionar la validación y certificación de recibos dentro del sistema. Permite crear un sello, aprobar recibos, asignarlos a un sello específico y hacer seguimiento del estado del proceso desde una vista de consultoría.

Este módulo está integrado con el flujo general de la aplicación y se enlaza desde el panel de gestores mediante la ruta /sellos/.

---

## ¿Qué funcionalidades tiene?

### 1. Creación de sellos
Los usuarios de Consultoría pueden crear sellos dorados con:
- un nombre identificatorio,
- una región,
- observaciones,
- y un código automático generado por el sistema.

Cada sello recibe un código en formato tipo:
- SD-2026-0001

### 2. Aprobación de recibos
El módulo permite aprobar recibos para que puedan luego ser relacionados con un sello dorado.

Este paso lo realiza el rol de Administración.

### 3. Asignación de recibos a sellos
Una vez aprobado, un recibo puede asignarse a un sello específico.

La asignación tiene reglas de negocio importantes:
- un recibo no puede asignarse a dos sellos distintos,
- solo puede asignarse si ya fue aprobado,
- y el proceso queda registrado en historial y auditoría.

### 4. Cambio de estado
Cada sello puede pasar por estados como:
- Borrador
- Aprobado
- Asignado
- Protocolizado
- Rechazado

### 5. Panel de Consultoría
Existe un panel especializado para Consultoría donde se pueden ver:
- recibos aprobados,
- sellos registrados,
- filtros por estado y región,
- y una vista más clara para seguimiento operativo.

### 6. Historial y auditoría
Toda acción relevante queda registrada en:
- el historial del sello,
- y en el módulo de auditoría del sistema.

---

## ¿En qué se compone?

### Modelos principales

#### 1. SelloDorado
Representa el sello institucional.

Campos principales:
- codigo_sello: identificador único generado automáticamente.
- nombre: nombre del sello.
- region: región asociada.
- estado: estado operativo del sello.
- observaciones: comentarios o notas.
- fecha_creacion: fecha de creación.
- fecha_actualizacion: fecha de última modificación.
- creado_por: usuario que lo creó.

Archivo principal:
- [apps/sellos/models.py](apps/sellos/models.py)

#### 2. HistorialSello
Guarda el registro de acciones realizadas sobre un sello.

Campos principales:
- sello: referencia al sello.
- usuario: quien realizó la acción.
- accion: tipo de acción.
- descripcion: detalle.
- fecha: momento en que ocurrió.

Archivo principal:
- [apps/sellos/models.py](apps/sellos/models.py)

### Integración con recibos
El módulo se relaciona con los recibos mediante campos agregados al modelo de recibos, tales como:
- sello_dorado
- aprobado_sello_dorado
- estatus_sello_dorado
- fecha_aprobacion_sello

Archivo principal:
- [apps/recibos/models.py](apps/recibos/models.py)

### Vistas del módulo
Las vistas principales están en:
- [apps/sellos/views.py](apps/sellos/views.py)

Incluyen:
- listado de sellos,
- creación,
- detalle,
- administración de recibos,
- panel de consultoría,
- aprobación de recibos,
- asignación de recibos,
- cambio de estado.

### Servicios de negocio
La lógica más importante está centralizada en:
- [apps/sellos/services.py](apps/sellos/services.py)

Incluye funciones para:
- aprobar recibos,
- asignar recibos a un sello,
- registrar historial,
- y registrar auditoría.

### URLs
Las rutas del módulo están definidas en:
- [apps/sellos/urls.py](apps/sellos/urls.py)

Rutas principales:
- /sellos/ → listado de sellos.
- /sellos/panel/ → panel de consultoría.
- /sellos/crear/ → creación de sellos.
- /sellos/administracion/ → administración de recibos para aprobar.
- /sellos/<id>/ → detalle del sello.

### Acceso desde el gestor
El módulo también está enlazado desde el panel principal de gestión en:
- [templates/gestores.html](templates/gestores.html)

---

## ¿Cómo se usa?

### Flujo básico
1. Ingresar al sistema con un usuario autorizado.
2. Acceder al módulo desde el panel de gestores o desde la ruta /sellos/.
3. Crear un sello dorado desde la opción de creación.
4. Aprobar recibos desde la administración.
5. Asignar los recibos aprobados al sello correspondiente.
6. Revisar el detalle del sello y su estado.
7. Consultar el panel de Consultoría para seguimiento y filtros.

### Roles involucrados

#### Consultoría
Puede:
- crear sellos,
- ver sellos,
- asignar recibos a un sello,
- cambiar estados,
- y revisar el panel de consultoría.

#### Administración
Puede:
- aprobar recibos para su posterior asignación.

---

## Reglas de negocio importantes

- Un recibo solo puede estar asociado a un único sello.
- Solo un recibo aprobado puede asignarse a un sello.
- Las operaciones quedan registradas automáticamente.
- El estado del sello cambia según el flujo del proceso.

---

## Archivos principales del módulo

- [apps/sellos/models.py](apps/sellos/models.py)
- [apps/sellos/views.py](apps/sellos/views.py)
- [apps/sellos/services.py](apps/sellos/services.py)
- [apps/sellos/urls.py](apps/sellos/urls.py)
- [apps/sellos/templates/sellos/lista.html](apps/sellos/templates/sellos/lista.html)
- [apps/sellos/templates/sellos/crear.html](apps/sellos/templates/sellos/crear.html)
- [apps/sellos/templates/sellos/detalle.html](apps/sellos/templates/sellos/detalle.html)
- [apps/sellos/templates/sellos/administracion.html](apps/sellos/templates/sellos/administracion.html)
- [apps/sellos/templates/sellos/panel_consultoria.html](apps/sellos/templates/sellos/panel_consultoria.html)

---

## Resumen rápido

Los Sellos Dorados funcionan como un flujo de certificación y trazabilidad para recibos aprobados. Están compuestos por:
- un modelo central de sello,
- un historial de acciones,
- integración con recibos,
- vistas de gestión y consultoría,
- y reglas que aseguran control y seguimiento institucional.
