# Módulo Sellos Dorados

Documentación rápida del módulo `sellos` (flujo, endpoints, administración y resolución de problemas).

---

## Resumen y objetivo

El módulo `sellos` gestiona protocolos llamados "Sellos Dorados" que agrupan `Recibo` aprobados. Flujo principal:

- Crear un `SelloDorado` (Consultoría).
- Aprobar recibos desde `Administración` (marcar `aprobado_sello_dorado=True`).
- Asignar recibos aprobados a un `SelloDorado` (Asignación masiva o por region).
- Registrar historial y auditoría de cada acción.

El diseño prioriza trazabilidad y seguridad (transacciones + bloqueo de filas).

## Modelos (resumen)

- `SelloDorado`:
  - Campos clave: `codigo_sello` (autogenerado), `nombre`, `region`, `estado`, `observaciones`, `creado_por`.
- `HistorialSello`: historial de acciones por sello.
- `Recibo` (en `apps/recibos`): campos relevantes: `aprobado_sello_dorado`, `estatus_sello_dorado`, `sello_dorado` (FK), `notificado_consultoria`, `anulado`.

## Servicios (lógica de negocio)

- `aprobar_recibos_para_sello(recibo_ids, usuario)`
  - Marca recibos como aprobados, pone `notificado_consultoria=False`, establece `fecha_aprobacion_sello` y registra auditoría.

- `asignar_recibos_a_sello(sello, recibo_ids, usuario)`
  - Ejecuta dentro de `transaction.atomic()` y usa `select_for_update()`.
  - Procesa cada recibo, valida (no asignado a otro sello, aprobado), asigna y registra historial/auditoría.
  - Devuelve objeto con `assigned_count`, `assigned_ids`, `errors` (detallado).

Notas de seguridad: la función ya no aborta al primer error; devuelve resultados parciales para evitar bloqueos de lote.

## Vistas y endpoints

- `GET /sellos/` — listado `PanelConsultoriaView`.
- `GET /sellos/<pk>/` — detalle `SelloDorado` (`SelloDoradoDetailView`) muestra recibos vinculados y una lista seleccionable de recibos aprobados disponibles.
- `POST /sellos/aprobar_recibos/` — aprobar recibos (desde `AdministracionRecibosView` form).
- `POST /sellos/asignar/` — asignación masiva; acepta `recibo_ids` como lista o textarea, o `region` para fallback.
- `POST /sellos/marcar_leidos/` — marca `notificado_consultoria=True` (acepta ids o `region`), devuelve JSON.
- `GET /sellos/export/` — export CSV de recibos aprobados (filtros por estado/region/region_group).

Permisos: `consultoria` puede crear y asignar; `admin` puede aprobar desde `Administracion`.

## Admin

- `SelloDorado` en el admin ahora muestra inline `Recibo` (solo lectura) y columnas con conteos (`Recibos totales`, `Recibos aprobados`).

## Frontend (UX actual)

- `detalle.html` incluye lista filtrable de recibos aprobados (checkboxes), contador de seleccionados y botones Select/Clear.
- `administracion.html` incluye tabla de pendientes con selección masiva y botón "Aprobar Seleccionados".
- Badge en `panel_consultoria` muestra `nuevos_count` (recibos aprobados no notificados).

## Diagnóstico y resolución de problemas comunes

- "No hay recibos aprobados disponibles para asignar":
  - Ver el bloque "Diagnóstico" en la ficha del sello (muestra `total_aprobados`, `aprobados_sin_sello`, `aprobados_asignados`).
  - Si `aprobados_sin_sello == 0` pero `total_aprobados > 0`, los aprobados ya están vinculados a otros sellos.
  - Si ambos 0, no hay aprobaciones: usa `Administración` para aprobar (mensajes visibles).

- Mensajes: revisa la cabecera de la página (`messages`) — ahora se muestran con estilo para ver confirmaciones/errores.

Comandos útiles (shell):

```bash
python manage.py shell
```
```python
from apps.recibos.models import Recibo
from apps.sellos.models import SelloDorado
# recibos aprobados sin sello
Recibo.objects.filter(aprobado_sello_dorado=True, sello_dorado__isnull=True)
# recibos aprobados por id
Recibo.objects.filter(pk__in=[...]).values('pk','numero_recibo','aprobado_sello_dorado','sello_dorado')

# historial de un sello
from apps.sellos.models import HistorialSello
HistorialSello.objects.filter(sello__pk=1).order_by('-created')[:20]
```

## Configuración opcional

- `settings.SELLOS_REGION_GROUPS`: diccionario opcional para mapear `region_group` a listas de estados. Ejemplo:

```py
SELLOS_REGION_GROUPS = {
    'occidente': ['Zulia','Falcón'],
    'capital': ['Caracas','Distrito Capital'],
}
```

## Tests y verificación

- Tests unitarios en `apps/sellos/tests.py` cubren flujo de aprobación, asignación por región, asignación parcial y export CSV.
- Ejecutar tests:

```bash
python manage.py test apps.sellos.tests
```

## Recomendaciones y próximos pasos

- Añadir paginación/lazy-load para la lista de recibos aprobados si el volumen es alto.
- Añadir un modal de confirmación que liste N recibos antes de asignar (prevención de errores masivos).
- Considerar export XLSX/PDF y notificaciones en tiempo real (Channels) si se requiere experiencia en vivo.

---

Si quieres, actualizo este README con capturas, ejemplos concretos de `curl` o una sección de `FAQ` con los casos que te han ocurrido.
