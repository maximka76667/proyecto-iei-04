# Pendiente para la Entrega 1

Entrega: **23/11/2026**. Alcance: wrappers, extractores, mappings (con las correcciones del profesor), carga en el almacén, informe de errores y reparaciones, y demo (`demo_entrega-1.py`).

Los casos de `data/samples/casos.json` marcados `pendiente` corresponden a esta lista: al implementar un punto, sus casos pasan de `xfailed` a `XPASS` y hay que quitarles la marca.

## Decisiones abiertas

| Decisión | Opciones | Propuesta |
| --- | --- | --- |
| Duplicados por contenido (mismo nombre, dirección y municipio con distinto id) | rechazar el segundo / cargarlo con aviso | rechazar, igual que un id repetido |
| CAN: mismo id con distinta subárea (p. ej. `ERE2021TF00082`) | quedarse con el primero (actual) / unir subáreas en `descripcion` | por decidir |
| Conversor: guardar la caché de geocodificación en git | sí / no | sí (primera carga de los compañeros rápida) |
| Conversor: peticiones simultáneas | 1 / 4 | 4 (primera carga ~5 min en lugar de ~20) |
| Codificación de los ficheros de evaluación | ver `preguntas_profesor.md` | preguntar al profesor |

## Comunitat Valenciana (CV)

- [ ] **Normalizar `sector`**: comparar sin mayúsculas, tildes ni espacios sobrantes; informar como reparación (`ambito_normalizado`). Casos CV 20, 21.
- [ ] **Teléfono `"0"` como vacío** (aparece en el fichero real). Casos CV 10, 14, 45.
- [ ] **Duplicados por contenido** (`duplicado_contenido`). Caso CV 30. Requiere la decisión de arriba.
- [ ] **Código postal por geocodificación inversa** («BUSCAR» del profesor), vía el conversor. Caso CV 50.

## Conversor de coordenadas (servicio HTTP, arquitectura de la diapositiva 9)

- [ ] Servicio `iei/conversor.py` en su propio puerto (p. ej. 8104), llamado por el back-end durante la carga.
  - UTM → lat/lon (CV; hoy se hace dentro de `mapping.py`).
  - Geocodificación inversa lat/lon → código postal (CV).
  - Geocodificación dirección + CP + municipio → lat/lon, con alternativa por CP y por municipio e indicación de precisión (CAT, CAN).
  - Caché de resultados (`data/geo_cache.json`).
- [ ] Servicio elegido: **CartoCiudad** (IGN). Probado: más preciso que Nominatim (portal frente a calle) y con CP correcto donde Nominatim falló. Funciona con `httpx` sin dependencias nuevas.
- [ ] La demo arranca el conversor junto a los wrappers.
- [ ] Los tests usan un conversor falso (sin Internet).

## Catalunya (CAT)

- [ ] **Re-espaciar direcciones compactadas** (`PladelVinyet,9BlocDbaixos` → `Pla del Vinyet, 9 Bloc D baixos`) sin tocar el fichero original; aceptar la geocodificación solo si el CP devuelto coincide con `codi_postal`. Caso CAT 32.
- [ ] **Geocodificación** de todas las entidades (no tienen coordenadas). Casos CAT 31, 32.
- [ ] **Punto perdido en emails de dominios conocidos** (`gmailcom` → `gmail.com`). Caso CAT 3.
- [ ] **Id con separador de miles** (`1.011` → `1011`). Caso CAT 11.
- [ ] **Varios teléfonos en un mismo campo** separados por salto de línea. Caso CAT 13.
- [ ] **CP sin cero inicial** (`8172` → `08172`). Caso CAT 18.
- [ ] Ámbito: el profesor anotó «LLM» (CAT no tiene campo de ámbito). Sin decidir si entra en la Entrega 1.

## Canarias (CAN)

- [ ] **Ámbitos que existen en el catálogo global** y hoy quedan NULL: Drogodependencia → `SALUD_Y_ATENCION_SOCIOSANITARIA`, Centros Ocupacionales → `EMPLEO_E_INSERCION_LABORAL`, Voluntariado → `VOLUNTARIADO_Y_PARTICIPACION_COMUNITARIA`, Varios + Migración → `MIGRACION`, Varios + subárea socio-sanitaria → `SALUD_Y_ATENCION_SOCIOSANITARIA`. Casos CAN 2, 11, 19, 21, 26.
- [ ] **Normalizar `area_nombre`** (mayúsculas/tildes). Caso CAN 27.
- [ ] **Número repetido** cuando ya está en el nombre de vía (`Avenida De Escaleritas 64` + `64`). Caso CAN 2.
- [ ] **Geocodificación** (no tienen coordenadas) y **código postal**, vía el conversor.
- [ ] Mismo id con distinta subárea: ver decisión de arriba.

## Para la entrega

- [ ] Ejecutar la demo completa sobre `data/sources` y revisar el informe.
- [ ] Repasar `docs/esquema_global.sql`, `docs/ETL_y_calidad.md` y `docs/arquitectura.md` tras los cambios (conversor, nuevas reparaciones).
- [ ] Actualizar o retirar `SEMANTIC_MAPPINGS.md` y `OBJETIVOS.md`: contradicen el mapping entregado (ids, ámbitos con tilde, PostgreSQL).

## Después (Entrega 2, 07/01)

- Filtro por código postal en la API de búsqueda (el formulario del enunciado lo tiene).
- API y formulario de carga, búsqueda, mapa: ya existen en el código del compañero (`iei/api.py`, `frontend/`), pendientes de revisar tras los cambios de la Entrega 1.
