# Proceso ETL, mappings y control de calidad

## Identificación de fuentes

El ZIP original tiene **carpetas con nombres discordantes respecto al contenido**: el JSON ubicado en `Catalunya` contiene registros de Canarias; el XML ubicado en `Euskadi` contiene entidades de Catalunya. Se han identificado por sus campos y raíz XML, y reubicado como `can.json` y `cat.xml`. `cv.csv` corresponde a Comunitat Valenciana. No se han modificado manualmente los contenidos.

## Mappings por campo

| Campo global | CV (CSV) | CAT (XML) | CAN (JSON) |
|---|---|---|---|
| E.id_entidad | `CV-` + `id` | `CAT-` + `n_mero_registre` | `CAN-` + `numero_registro` |
| E.nombre | `nombre` | `nom_de_l_entitat` | `denominacion` |
| E.ambito | `sector` + tabla aprobada | `NULL` (sin ámbito) | `area_nombre`, sin forzar propuestas |
| E.direccion | `domici` | `adre_a` | componentes de dirección |
| E.codigo_postal | `NULL` | `codi_postal` validado | `NULL` |
| E.longitud,latitud | `x_25830`,`y_25830` y WKT → EPSG:4326 | `NULL` | `NULL` |
| E.descripcion | `tipo_centro` | `naturalesa` | `subarea_nombre` |
| E.contacto | `telefono`,`email` | teléfono fijo/móvil y email | `telefono_1`,`telefono_2` |
| E.url | `NULL` | `web` validada | `pagina_web` validada |
| L.codigo | `cod_ine_mun` | `NULL` | `direccion_municipio_id` |
| L.nombre | `municipio` | `municipi` | `direccion_municipio_nombre` |
| P.codigo | Prefijo del INE válido | Prefijo CP si 08/17/25/43 | `direccion_provincia_id` |
| P.nombre | `provincia` | Tabla de 4 provincias CAT | `direccion_provincia_nombre` |

**Fuente de verdad para la semántica:** `docs/mapping_semantico_equipo4.pdf`, redactado por el equipo. La documentación del mapping utiliza `E`, `L` y `P` para Entidad, Localidad y Provincia, respectivamente.

## Controles y decisiones

1. **Campos vacíos:** trim y normalización de espacios; `_U` y valores nulos explícitos se interpretan como `NULL` sólo si son el valor completo.
2. **Claves:** IDs obligatorios y únicos dentro de lote; prefijos por autonomía, sin derivar CAN de NIF. Si no hay ID o nombre, se descarta, dejando incidencia. Si hay ID duplicado en el mismo lote, se mantiene la primera fila y se rechaza la repetición con `duplicado_lote`.
3. **Códigos:** CP/INE como texto, preservando 0 inicial. Códigos INE con menos de 5 dígitos se rellenan cuando son numéricos y válidos por longitud, informando una reparación. Las discordancias geográficas se registran en lugar de inventar provincias.
4. **Coordenadas:** CV usa la pareja UTM (x,y) y comprueba acuerdo con WKT (tolerancia 5 m); si faltan ambos ejes pero WKT es válido, se recuperan y registra reparación. Se calculan longitud/latitud en EPSG:4326. Ejes incompletos, WKT malo y coordenadas absurdas generan incidencias.
5. **Contacto y URL:** se descartan de los campos limpios los correos sin formato válido, pero se conserva el valor en `raw_json` y en la incidencia. No se reparan dominios malformados por intuición. Se antepone `https://` sólo a un dominio inequívoco que comienza con `www.`.
6. **Semántica:** CV sigue la equivalencia explícita `sector→ambito`; CAT no dispone de ámbito. CAN usa las correspondencias directas aprobadas (Tercera Edad, Discapacidad, Menores Y Juventud, Mujer, Exclusión Social). Drogodependencia, Voluntariado, Centros Ocupacionales y subáreas ambiguas se dejan `NULL`, con advertencia. El caso CAN Varios/Migración se mantiene provisional hasta validación.
7. **Trazabilidad:** tabla `incidencias`, fila fuente, código de error, valor anterior y reparado; se guarda `raw_json` del registro aceptado. Las ejecuciones dejan registro en `cargas` con sumario.
8. **Reejecuciones:** UPSERT idempotente y huella del registro normalizado, para distinguir nuevo / actualizado / sin cambios. Una segunda carga conserva la misma cantidad de entidades.

## Resultados observados en la carga inicial

| Fuente | Filas | Insertados | Descartados | Incidencias (incl. advertencias) | Reparaciones |
|---|---:|---:|---:|---:|---:|
| CV | 1.697 | 1.697 | 0 | 14 | 0 |
| CAT | 765 | 765 | 0 | 1.268 | 1 |
| CAN | 810 | 749 | 61 | 769 | 142 |
| **Total** | **3.272** | **3.211** | **61** | **2.051** | **143** |

Las incidencias no equivalen a filas descartadas: gran parte son avisos o datos de contacto inválidos. Los datos de Catalunya presentan muchos correos con dominios sin punto (`gmailcom`) y URL sin puntos en el nombre del host; no sería legítimo repararlos masivamente por intuición. Los IDs repetidos de Canarias sí provocan descarte controlado de la fila repetida, evitando sobreescrituras.

## Pruebas de fallo

Las pruebas automatizadas incluyen: WKT recuperable, WKT mal formado, coordenadas fuera de rango, CP inválido, URL mal formada, marcador `_U`, propuesta de ámbito sin validar, teléfono repetido, falta de ID, ID repetido, UPSERT sin cambios, actualización por ID, filtros y bbox, respuesta GeoJSON, validación de bbox, Swagger y wrapper XML paginado.

> Los códigos para categorías globales que aparecen en el mapping como *provisional* deben contrastarse con el esquema formal de asignatura cuando éste esté disponible.
