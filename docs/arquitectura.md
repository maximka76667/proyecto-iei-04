# Arquitectura técnica y decisiones

## Componentes de la solución

```text
                           NAVEGADOR
          ┌───────────────────────────────────────┐
          │ Formulario consulta · OpenLayers      │
          │ Formulario carga · Auditoría de ETL   │
          └───────────────────┬───────────────────┘
                              │ REST / GeoJSON
               ┌──────────────▼──────────────┐
               │ INTEGRADOR API :8000        │
               │ /api/entities  /api/map     │
               │ /api/load  /api/loads       │
               │ /api/coordinates/convert    │
               └─────────┬───────────────────┘
                         │ SQLite (E, L, P, auditoría)
           ┌─────────────▼───────────────────┐
           │ Capa ETL: extractores HTTP      │
           │ normalización, validación, UPSERT│
           └────┬──────────┬──────────┬───────┘
                │HTTP      │HTTP      │HTTP
         ┌──────▼───┐ ┌────▼─────┐ ┌──▼─────────┐
         │ CAN :8101│ │CAT :8102 │ │ CV :8103   │
         │ JSON     │ │ XML      │ │ CSV        │
         └──────────┘ └──────────┘ └────────────┘
```

- La lógica `iei.sources` implementa los lectores originales. Cada **wrapper** los publica en HTTP como JSON paginado (`/records`) y publica metadatos (`/schema`). Los extractores en `iei.api.extract_http` **no acceden directamente** a los archivos: llaman al wrapper correspondiente.
- `iei.mapping.map_row` convierte un registro en una entidad E, una localidad L, una provincia P y una secuencia de incidencias. No hace escrituras, por lo que se prueba independientemente.
- `iei.database.process_source` persiste los registros (base SQL relacional), relaciona entidades con localidades y provincias, registra raw JSON, gestiona IDs repetidos, UPSERT idempotente y la auditoría por carga.
- `iei.api` expone endpoints de carga/consulta y mapa; FastAPI genera OpenAPI y documentación interactiva.
- El frontend hace llamadas de mismo origen (same-origin) al servidor. El mapa usa OpenLayers/OpenStreetMap como mashup, y `GET /api/map` devuelve GeoJSON con geometrías `Point`.

## Esquema global inferido

**E: Entidad** (`entidades`) — `id_entidad` PK (`CV-…`, `CAT-…`, `CAN-…`), `fuente`, `id_origen`, `nombre`, `ambito`, `direccion`, `codigo_postal`, `longitud`, `latitud`, `descripcion`, `contacto`, `url`, FKs a L/P, búsqueda normalizada, registro original y huella idempotente.

**L: Localidad** (`localidades`) — `codigo` INE cuando existe, `nombre`, FK a provincia. Como Catalunya no incluye INE, se usa clave interna estable compuesta por fuente + provincia + nombre, pero **L.codigo se deja NULL**, siguiendo el mapping.

**P: Provincia** (`provincias`) — `codigo`, `nombre`; origen CV/CAN o derivación de CP válido en CAT.

**Cargas e incidencias:** (`cargas`, `incidencias`) — cada ejecución contiene el número de filas, altas, actualizaciones, filas sin cambios, descartes, incidencias, reparaciones y detalle por fila/campo. Los valores brutos se conservan en `entidades.raw_json` cuando la entidad se acepta; en incidencia se preservan también valores erróneos rechazados.

El SQL completo está en `docs/esquema_global.sql` y se aplica automáticamente al crear el SQLite.

## Semántica de la búsqueda

- `q`: texto libre (nombre, dirección, descripción, municipio, provincia, ámbito), con insensibilidad a tildes mediante una columna de búsqueda precalculada.
- `municipio`/`provincia`: coincidencia parcial textual.
- `fuente`: CV/CAT/CAN.
- `ambito`: equivalencia exacta desde catálogo admitido.
- `bbox`: `west,south,east,north` en EPSG:4326, con posible cruce de antimeridiano; excluye entidades sin coordenadas. La interfaz permite activarlo opcionalmente para filtrar el listado.
- `limit` y `offset`: paginación de resultados.

## Operaciones incrementales

Al cargar una fuente, los IDs de negocio determinan la unicidad. Si la huella normalizada no cambia, el registro se cuenta como `sin_cambios`; si cambia, UPSERT actualiza ese ID; si es nuevo, se inserta. **No se borran automáticamente entidades ausentes del nuevo fichero**, para evitar pérdida de datos sin una operación explícita de sincronización. Borrar la base entre pruebas sobre datasets completos diferentes.

## Alineación con arquitectura del enunciado

La separación frontend/backend/almacén/extractores/wrappers y el uso de HTTP replican la arquitectura proporcionada. La tecnología concreta SQLite es una decisión de portabilidad, dado que el enunciado permite escoger lenguaje y entorno. El esquema físico es **derivado del mapping** porque no se adjuntó la versión formal del esquema global.
