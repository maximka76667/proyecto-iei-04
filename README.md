# IEI · Entrega 2 — Buscador integrado de entidades sociales

**Asignatura:** Integración e Interoperabilidad · Curso 2026–27  
**Objetivo:** Aplicación final con formularios de búsqueda y de carga, tres fuentes heterogéneas, integrador ETL, almacén relacional, APIs HTTP documentadas y visualización en OpenLayers.

## 1. Arrancar en local (recomendado)

Requisitos: **Python 3.10+**, conexión a Internet para los mosaicos del mapa y CDN de OpenLayers, y puertos libres **8000, 8101, 8102 y 8103**.

Desde esta carpeta:

1. Comprobar que pip está instalado (normalmente viene con Python):

   ```bash
   python -m pip --version
   ```

   Solo si responde `No module named pip`:

   ```bash
   python -m ensurepip --upgrade
   ```

2. Crear y activar el entorno virtual (`.venv/` está en `.gitignore`):

   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # Linux / macOS:
   source .venv/bin/activate
   ```

   El prompt debe empezar por `(.venv)`. Si PowerShell responde que la ejecución de scripts está deshabilitada, ejecutar una vez lo siguiente y volver a activar:

   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   ```

   En cada terminal nueva hay que volver a activar el entorno.

3. Instalar las dependencias:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

4. Ejecutar las pruebas y la demo:

   ```bash
   python -m pytest -q
   python run_demo.py
   ```

Abrir **http://127.0.0.1:8000** en el navegador. Swagger interactivo: **http://127.0.0.1:8000/docs**.

`run_demo.py` arranca 4 servidores HTTP, ejecuta automáticamente la carga de los 3 datasets y muestra los resultados. Para iniciar sin ejecutar una carga nueva: `python run_demo.py --no-load`. Para detener todos los servicios, `Ctrl+C`.

> La base de datos `data/integrador.sqlite3` se incluye precargada como **snapshot de demostración**. Al cargar otra vez, el proceso es idempotente y comprueba registros sin cambios. Puedes borrar el fichero SQLite (con los servidores parados) para probar la primera carga desde cero.

## 2. Alternativa mediante Docker Compose

```bash
docker compose up --build
```

Acceder a **http://localhost:8000** y pulsar **Administrar datos → Ejecutar carga ETL**. Docker crea un volumen `iei_database` persistente. Los wrappers `can`, `cat` y `cv` se comunican por HTTP con `integrador` dentro de la red Compose. No necesitas Python local si usas Docker.

## 3. Estructura del proyecto

```text
IEI_Entrega2/
├── iei/
│   ├── wrapper.py          # Wrapper HTTP genérico desplegado 3 veces
│   ├── sources.py          # Lectores CSV, XML, JSON de las fuentes originales
│   ├── mapping.py          # Mappings semánticos y validaciones
│   ├── database.py         # Almacén relacional, ETL, calidad y consultas
│   └── api.py              # Backend HTTP, búsqueda, carga, mapa, coordenadas
├── frontend/
│   ├── index.html          # Formularios, tarjetas, panel de auditoría
│   ├── styles.css          # Interfaz adaptable
│   └── app.js              # Cliente REST y OpenLayers
├── data/
│   ├── sources/
│   │   ├── cv.csv          # Datos CV reales del ZIP
│   │   ├── cat.xml         # Datos CAT reales del ZIP
│   │   └── can.json        # Datos CAN reales del ZIP
│   └── integrador.sqlite3  # BBDD inicial de demostración
├── docs/
│   ├── arquitectura.md
│   ├── API.md
│   ├── ETL_y_calidad.md
│   ├── DEMOSTRACION.md
│   ├── esquema_global.sql
│   ├── enunciado.pdf
│   └── mapping_semantico_equipo4.pdf
├── tests/                  # Pruebas unitarias y de integración
├── run_demo.py
├── compose.yaml
├── Dockerfile
└── requirements.txt
```

## 4. Funcionalidades entregadas

- Lectura **JSON Canarias / XML Catalunya / CSV Comunitat Valenciana** con wrappers independientes por HTTP, paginación y esquema disponible en `/schema`.
- Extractores que consultan los wrappers por HTTP y aplican el mapping del equipo 4, sin saltarse la capa de wrappers.
- Almacén relacional **Provincia → Localidad → Entidad**, con IDs de origen, campo fuente y auditoría del dato original.
- Validaciones de códigos INE/CP, teléfono/correo/URL, campos obligatorios, duplicados, semántica, coherencia territorial y coordenadas; separa **errores, advertencias y reparaciones**.
- Conversión EPSG:25830 → EPSG:4326 (longitud, latitud) mediante `pyproj` y comprobación con WKT.
- API de **carga** con UPSERT idempotente, historial e incidencias por registro, exportación CSV.
- API de **búsqueda** con texto libre, municipio, provincia, fuente, ámbito, paginación y rectángulo geográfico (bbox).
- **Mapa OpenLayers** con marcadores geolocalizados y consulta GeoJSON por extensión visible.
- Documentación OpenAPI/Swagger autogenerada (`/docs`) y guía de endpoints.
- Pruebas automáticas: `python -m pytest -q`.

## 5. Resultado real sobre los datasets originales

| Fuente | Leídos | Únicos guardados | Descartados |
| --- | ---: | ---: | ---: |
| CV | 1.697 | 1.697 | 0 |
| CAT | 765 | 765 | 0 |
| CAN | 810 | 749 | 61 |
| **TOTAL** | **3.272** | **3.211** | **61** |

Se detectaron **61 identificadores repetidos dentro de Canarias**: se retiene la primera aparición y se registra una incidencia para cada repetición. En el conjunto original, **1.697 entidades tienen coordenadas** (todas procedentes de CV). CAT y CAN no las suministran: permanecen visibles en el buscador, pero no reciben coordenadas inventadas.

La fuente catalana contiene gran número de emails y URLs mal formados: se conservan los valores originales en la columna `raw_json` y se reportan las incidencias en la auditoría, en vez de inventar puntos o letras. Algunos mappings CAN son propuestas pendientes de confirmación, por lo que esos ámbitos quedan sin clasificar (`NULL`).

## 6. Cómo presentar la demostración

Consulta `docs/DEMOSTRACION.md` para una secuencia de demo de 5 minutos, incluido un ejemplo de reparación y una carga repetida sin duplicados. Consultar detalles técnicos en `docs/ETL_y_calidad.md` y `docs/arquitectura.md`.

## 7. Limitaciones y decisiones justificadas

1. **Esquema global oficial no aportado:** en el ZIP sí aparece el enunciado y el mapping del equipo, pero **no el esquema formal suministrado por la asignatura**. Se ha implementado un **esquema relacional inferido** de los campos `E`, `L` y `P` descritos en el mapping. Si el profesorado entrega un DDL canónico distinto, hay que alinearlo antes de la entrega.
2. **Geolocalización faltante:** CAT y CAN carecen de coordenadas originales. Geocodificarlos requeriría una fuente adicional, validación de coincidencia y registrar procedencia/precisión. No se ha realizado una geocodificación no verificable.
3. **Mapping semántico provisional:** los casos indicados como “propuesta” o “validar” en el PDF del equipo no se fuerzan automáticamente.
4. **Mosaicos/JS del mapa:** OpenLayers y OpenStreetMap se obtienen de Internet en el navegador. Sin conexión, las búsquedas y APIs siguen funcionando.
5. **SQLite:** elegida por portabilidad para la demo; no es un despliegue multiusuario de producción. Las consultas geográficas se hacen con rango/bbox sobre índices, sin PostGIS. Si el esquema global oficial exige otro motor, puede migrarse el repositorio de acceso a datos.
6. **Seguridad:** esta es una herramienta académica para entorno local; `/api/load` no tiene autenticación. No debe exponerse a Internet sin protección y sin limitar acciones de escritura.

## 8. Reprobar los casos con datos de evaluación

Sustituir, con servidores detenidos, los ficheros `data/sources/cv.csv`, `cat.xml`, `can.json` por los de evaluación **con el mismo formato**. El wrapper detecta cambios de mtime/tamaño y los lee de nuevo. Los datos previos permanecen hasta reiniciar la BD o actualizar por ID (no hay borrado en cargas incrementales). Antes de evaluar un dataset íntegramente nuevo, borrar/renombrar `data/integrador.sqlite3` para una base limpia. Se rechazan registros sin ID/nombre o duplicados de lote; se registran incidencias de los demás casos.
