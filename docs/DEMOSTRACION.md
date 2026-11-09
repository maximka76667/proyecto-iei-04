# Guion de demostración — entrega 2 (aprox. 5 minutos)

## Antes de empezar

`python run_demo.py` y abrir `http://localhost:8000`.

## Demostración de funcionalidades

**1. Arquitectura de servicios (30 s):** abrir `/docs` del backend y los tres `/schema` de wrappers (8101, 8102, 8103) para evidenciar datos CSV/XML/JSON servidos por HTTP. Mostrar `/api/sources` y la página de documentación.

**2. Búsqueda única (45 s):** en Explorar, escribir `discapacidad` o buscar `Los Montesinos`; filtrar por `Comunitat Valenciana`. Mostrar la tarjeta de centro y municipio, luego pulsar “Ver en el mapa” (CV dispone de coordenadas).

**3. Mashup geográfico (40 s):** mover y ampliar el mapa y observar nuevas ubicaciones dentro de la vista. Activar “Limitar resultados al mapa visible” para consultar entidades con `bbox`.

**4. Varias fuentes (45 s):** quitar filtros y elegir `Catalunya`; mostrar los resultados y explicar por qué no tienen marcadores: la fuente XML carece de coordenadas. Repetir con `Canarias`, cuyo JSON tampoco las incluye.

**5. Carga y auditoría (60 s):** abrir “Administrar datos”, seleccionar las tres fuentes y pulsar “Ejecutar carga ETL”. Mostrar totales, reparaciones y duplicados. En “Últimas cargas”, elegir una carga CAN y enseñar la incidencia `duplicado_lote`; elegir CAT y mostrar correos/URLs inválidos sin reconstrucciones arbitrarias. Exportar el CSV de incidencias.

**6. Idempotencia (45 s):** cargar de nuevo CV y verificar `0 insertados`, `0 actualizados`, `1697 sin cambios`. La cifra total sigue en **3211** registros (61 duplicados de origen CAN controlados).

**7. Conversor EPSG (15 s):** mostrar en Swagger `POST /api/coordinates/convert`, con `x_25830=698055` y `y_25830=4211247`, comprobando que devuelve longitud/latitud.

## Preguntas previsibles

- **¿Por qué solo CV sale en el mapa?** CAT y CAN no incluyen coordenadas. Se evitan posiciones inventadas; los resultados textuales siguen completos.
- **¿Qué ocurre con los 61 duplicados de CAN?** Primera fila por ID conservada; repetición descartada y documentada con número de fila, identificador y fuente.
- **¿Qué ocurre con los correos como `gmailcom`?** Se dejan fuera del campo normalizado; se preservan en origen/bitácora, y no se inventa el punto del dominio.
- **¿Dónde está el mapping?** `docs/mapping_semantico_equipo4.pdf`, implementado en `iei/mapping.py` y documentado en `ETL_y_calidad.md`.
- **¿Qué motor se utiliza?** SQLite relacional (tables E/L/P + auditoría), elegido para ejecutar sin infraestructura externa. Si el esquema global oficial exige otra DDL, hay que migrarlo.

## Repetir con una base vacía

Detener servidores, renombrar `data/integrador.sqlite3` y ejecutar `python run_demo.py` para carga desde cero. Si se desea restaurar el snapshot, conservar copia antes de borrar.
