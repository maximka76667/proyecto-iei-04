# Contrato REST y ejemplos

Documentación interactiva autogenerada en **http://localhost:8000/docs** (Swagger). JSON OpenAPI en `/openapi.json`.

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/health` | Estado del integrador |
| GET | `/api/sources` | Orígenes HTTP de wrappers configurados |
| POST | `/api/load` | Carga mediante extractores HTTP + mappings + almacenamiento |
| GET | `/api/entities` | Consulta textual/geográfica filtrada y paginada |
| GET | `/api/entities/{id}` | Detalle de una entidad |
| GET | `/api/map` | FeatureCollection GeoJSON de puntos geolocalizados |
| GET | `/api/stats` | Totales por fuente y geolocalización |
| GET | `/api/metadata` | Catálogos disponibles de ámbitos/provincias |
| GET | `/api/loads` | Historial de cargas |
| GET | `/api/loads/{id}/issues` | Incidencias paginadas, errores y reparaciones |
| GET | `/api/loads/{id}/issues.csv` | Exportar auditoría completa a CSV |
| POST | `/api/coordinates/convert` | EPSG:25830 → EPSG:4326 |

## Wrappers independientes

Los wrappers funcionan en puertos **8101 CAN, 8102 CAT, 8103 CV**. Cada uno expone:

| Método | Ruta | Resultado |
|---|---|---|
| GET | `/health` | Salud y nº registros |
| GET | `/schema` | Campos y cantidad de registros |
| GET | `/records?page=1&page_size=250` | Registros de origen sin mapping en JSON, máximo 500 por página |
| GET | `/docs` | OpenAPI del wrapper |

## Ejemplos

**Búsqueda libre con paginación:**

```bash
curl 'http://localhost:8000/api/entities?q=mayores&fuente=CV&limit=10&offset=0'
```

**Filtro geográfico:**

```bash
curl 'http://localhost:8000/api/map?bbox=-1,38,0,40'
```

**Carga sólo Catalunya:**

```bash
curl -X POST http://localhost:8000/api/load \
  -H 'Content-Type: application/json' \
  -d '{"sources":["CAT"]}'
```

**Cargar todas las fuentes:**

```bash
curl -X POST http://localhost:8000/api/load \
  -H 'Content-Type: application/json' \
  -d '{"sources":["CV","CAT","CAN"]}'
```

**Conversión de coordenadas:**

```bash
curl -X POST http://localhost:8000/api/coordinates/convert \
  -H 'Content-Type: application/json' \
  -d '{"x_25830":698055,"y_25830":4211247}'
```

**Auditoría de calidad:**

```bash
curl http://localhost:8000/api/loads
curl 'http://localhost:8000/api/loads/3/issues?limit=30'
curl -OJ http://localhost:8000/api/loads/3/issues.csv
```

## Respuestas y errores

Los endpoints GET de búsqueda retornan `total`, `limit`, `offset` e `items`. Los registros llevan campos `id_entidad`, `fuente`, `nombre`, `ambito`, `direccion`, `codigo_postal`, `longitud`, `latitud`, `descripcion`, `contacto`, `url`, `localidad`, `provincia` y códigos correspondientes.

`POST /api/load` retorna un resultado por fuente: `leidos`, `insertados`, `actualizados`, `sin_cambios`, `descartados`, `incidencias`, `reparaciones` y `carga_id`. Si falla una fuente, el objeto superior lleva `status: partial_error` y se detalla el error sin ocultar el resultado de las otras fuentes. La carga de cada fuente es atómica.

Los errores de validación de parámetros devuelven HTTP **422**; los IDs desconocidos devuelven **404**. Si un wrapper no responde, `POST /api/load` reporta un error individual de esa fuente; el frontend muestra el detalle y no inventa resultados.
