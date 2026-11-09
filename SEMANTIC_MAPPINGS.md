# MAPPINGS SEMÁNTICOS - DOCUMENTO OFICIAL

## PROYECTO BUSCADOR DE ONGD

### Integración e Interoperabilidad - Curso 2026-27

---

## 📋 RESUMEN EJECUTIVO

Este documento define cómo los campos de cada fuente de datos regional se mapean al esquema global unificado. Cada región usa nombres de campos diferentes y estructuras distintas. Los mappings aseguran que todos los datos se normalicen a un formato común en la base de datos.

**Nota Crítica:**

- ⚠️ **Canarias y Catalunya NO tienen coordenadas lat/lon** en sus datos
- ✅ **Valencia SÍ tiene coordenadas** (columnas x_25830, y_25830 en UTM)
- Solución: Usar geocoding para obtener lat/lon de direcciones donde no existan

---

## 🗺️ FUENTES DE DATOS ANALIZADAS

| Región        | Formato | Registros | Campos | Coordenadas                  |
| ------------- | ------- | --------- | ------ | ---------------------------- |
| **Canarias**  | JSON    | N/A       | 22     | ❌ NO (necesita geocoding)   |
| **Catalunya** | XML     | N/A       | 10     | ❌ NO (necesita geocoding)   |
| **Valencia**  | CSV     | 9+        | 21     | ✅ SÍ (x_25830, y_25830 UTM) |

---

## 1️⃣ MAPPING CANARIAS (JSON)

### Esquema Fuente - Campos Disponibles

```json
{
  "nif": "G35068824",
  "denominacion": "Asociacion Adepsi",
  "numero_registro": "ERE1986CA00001",
  "direccion_tipo_via": "Calle",
  "direccion_nombre_via": "Lomo La Plana",
  "direccion_numero": "28",
  "direccion_complemento": "_U",
  "direccion_provincia_id": "35",
  "direccion_provincia_nombre": "Las Palmas",
  "direccion_municipio_id": "35001",
  "direccion_municipio_nombre": "Palmas de Gran Canaria (Las)",
  "direccion_isla_id": "GC",
  "direccion_isla_nombre": "Gran Canaria",
  "telefono_1": "(34)928414484",
  "telefono_2": "_U",
  "pagina_web": "wwwadepsi.org",
  "area_id": "03",
  "area_nombre": "Discapacidad",
  "subarea_id": "_U",
  "subarea_nombre": "_U"
}
```

### Tabla de Mappings: Canarias → Esquema Global

```
┌─────────────────────────────┬──────────────────┬─────────────────────┬─────────────────┐
│ Campo Fuente (Canarias)     │ Campo Global     │ Transformación      │ Notas           │
├─────────────────────────────┼──────────────────┼─────────────────────┼─────────────────┤
│ nif                         │ cod_entidad      │ Directo              │ Identificador   │
│ denominacion                │ nombre           │ Directo (rename)     │ Nombre entidad  │
│ numero_registro             │ (no usado)       │ Ignorar              │ Solo para audit │
│ direccion_tipo_via +        │ dirección        │ Concatenar           │ "Calle" + "Nombre" │
│ direccion_nombre_via +      │ dirección        │ Concatenar           │ + "Número"      │
│ direccion_numero +          │ dirección        │ Concatenar           │ Ej: "Calle ...  │
│ direccion_complemento       │ dirección        │ Concatenar           │ 28"             │
│ direccion_provincia_id      │ provincia_id     │ Directo (cast INT)   │ Clave foránea   │
│ direccion_provincia_nombre  │ (verificar)      │ Lookup Provincia     │ Validación      │
│ direccion_municipio_id      │ código_postal    │ MAPPING*             │ Ver abajo       │
│ direccion_municipio_nombre  │ (verificar)      │ Lookup Localidad     │ Validación      │
│ direccion_isla_id           │ (extra)          │ Guardar en BD        │ Información     │
│ direccion_isla_nombre       │ (extra)          │ Guardar en BD        │ adicional       │
│ telefono_1                  │ contacto         │ Limpiar formato      │ Ver NOTAS*      │
│ telefono_2                  │ (extra/ignorar)  │ Ignorar si "_U"      │ _U = null/na    │
│ pagina_web                  │ URL              │ Limpiar y validar    │ Agregar http:// │
│ area_id                     │ ámbito           │ MAPPING (enum)*      │ Ver VALORES     │
│ area_nombre                 │ (verificar)      │ Lookup tabla ámbito  │ Validación      │
│ subarea_id                  │ (extra/ignorar)  │ Ignorar si "_U"      │ No siempre existe │
│ subarea_nombre              │ (extra/ignorar)  │ Ignorar si "_U"      │ No siempre existe │
└─────────────────────────────┴──────────────────┴─────────────────────┴─────────────────┘
```

### Mappings Especiales para Canarias

#### **MAPPING 1: código_postal**

Problema: Canarias NO proporciona código postal directamente. Tiene `direccion_municipio_id` que es un código INE.

Solución:

```
direccion_municipio_id (35001) → Buscar en tabla Localidad → obtener código_postal
Si no existe → Usar tabla de mappings municipio_id → código_postal (external lookup)
```

#### **MAPPING 2: ámbito (area_id → ENUM)**

```
Canarias area_id  →  Global ámbito
─────────────────────────────────────
01 (Mayores)                    → MAYORES
02 (Menores)                    → INFANCIA_Y_JUVENTUD
03 (Discapacidad)               → DISCAPACIDAD
04 (Enfermedad mental)          → SALUD_MENTAL
05 (Exclusión social)           → INCLUSIÓN_SOCIAL
06 (Mujer)                      → MUJER
07 (Centros Ocupacionales)      → EMPLEO_E_INSERCIÓN_LABORAL
08 (Migración)                  → MIGRACIÓN
09 (Cultura)                    → CULTURA_Y_DESARROLLO_COMUNITARIO
10 (Salud)                      → SALUD_Y_ATENCIÓN_SOCIOSANITARIA
... (agregar todas las combinaciones según datos reales)
```

#### **MAPPING 3: Teléfono - Limpieza**

```
Entrada: "(34)928414484"
Proceso:
  1. Remover parentesis: "34928414484"
  2. Si empieza con "34": remover (es España)
  3. Resultado: "928414484" o "928414484" (mantener ambos formatos?)
  4. Si es "_U" → NULL (valor especial de Canarias para missing)

Salida: contacto = "928414484"
```

#### **MAPPING 4: URL - Limpieza**

```
Entrada: "wwwadepsi.org"
Proceso:
  1. Si no empieza con "http" → agregar "https://"
  2. Si falta "." después de www → insertar
  3. Validar formato URL

Salida: URL = "https://www.adepsi.org"
```

#### **MAPPING 5: Dirección - Concatenación**

```
Campos:
  direccion_tipo_via = "Calle"
  direccion_nombre_via = "Lomo La Plana"
  direccion_numero = "28"
  direccion_complemento = "_U"

Proceso:
  direccion = trim(direccion_tipo_via) + " " +
              trim(direccion_nombre_via) + " " +
              trim(direccion_numero)
  Si direccion_complemento != "_U":
    direccion += ", " + direccion_complemento

Resultado: dirección = "Calle Lomo La Plana 28"
```

#### **MAPPING 6: Latitud/Longitud - GEOCODING REQUERIDO**

```
⚠️ PROBLEMA: Canarias NO tiene latitud/longitud en datos originales

Solución:
  1. Usar dirección completa: "Calle Lomo La Plana 28, 35001, Las Palmas"
  2. Llamar API de geocoding (Google Maps, OpenStreetMap, etc.)
  3. Obtener latitud/longitud
  4. Guardar en BD

Herramientas sugeridas:
  - geopy (Python library)
  - Google Maps Geocoding API
  - OpenStreetMap Nominatim
  - Bing Maps

Manejo de errores:
  - Si geocoding falla → marcar registro como PENDIENTE_GEOCODING
  - Reintentar periódicamente
  - Permitir edición manual de coordenadas
```

---

## 2️⃣ MAPPING CATALUNYA (XML)

### Esquema Fuente - Campos Disponibles

```xml
<entitat>
    <n_mero_registre>306</n_mero_registre>
    <nom_de_l_entitat>180ºParaLaCooperaciónYElDesarrollo</nom_de_l_entitat>
    <naturalesa>Associació</naturalesa>
    <cif_entitat>G63749444</cif_entitat>
    <adre_a>PladelVinyet,9BlocDbaixos</adre_a>
    <codi_postal>08172</codi_postal>
    <municipi>SantCugatdelVallès</municipi>
    <tel_fon>932173600</tel_fon>
    <tel_fon_m_bil>620030453</tel_fon_m_bil>
    <correu_electr_nic>laia@1x1microcreditorg</correu_electr_nic>
    <web>http://www1x1microcreditorg</web>
</entitat>
```

### Tabla de Mappings: Catalunya → Esquema Global

```
┌──────────────────────────┬──────────────────┬─────────────────────┬─────────────────┐
│ Campo Fuente (Catalunya) │ Campo Global     │ Transformación      │ Notas           │
├──────────────────────────┼──────────────────┼─────────────────────┼─────────────────┤
│ n_mero_registre          │ cod_entidad      │ Directo (cast STR)  │ Identificador   │
│ nom_de_l_entitat         │ nombre           │ Directo (rename)    │ Nombre entidad  │
│ naturalesa               │ (extra/ignorar)  │ Guardar si útil     │ Tipo org        │
│ cif_entitat              │ (extra)          │ Guardar en BD       │ ID fiscal       │
│ adre_a                   │ dirección        │ Limpiar espacios    │ Dirección completa
│ codi_postal              │ código_postal    │ Directo (rename)    │ Código postal   │
│ municipi                 │ Localidad.nombre │ Lookup Localidad    │ Buscar municipio│
│ tel_fon                  │ contacto         │ Limpiar formato     │ Teléfono fijo   │
│ tel_fon_m_bil            │ contacto         │ Concatenar*         │ Teléfono móvil  │
│ correu_electr_nic        │ (extra)          │ Guardar en BD       │ Email contacto  │
│ web                      │ URL              │ Validar formato     │ Website         │
│ (NO TIENE)               │ latitud          │ GEOCODING REQUERIDO │ ⚠️ Falta        │
│ (NO TIENE)               │ longitud         │ GEOCODING REQUERIDO │ ⚠️ Falta        │
│ (NO TIENE)               │ ámbito           │ ??? (FALTA FIELD)   │ ⚠️ ¿Inferir?    │
└──────────────────────────┴──────────────────┴─────────────────────┴─────────────────┘
```

### Mappings Especiales para Catalunya

#### **MAPPING 1: Municipio → Código Postal**

```
Entrada: municipi = "SantCugatdelVallès"
Problema: Necesita código postal, pero solo tiene nombre de municipio

Solución:
  1. Buscar "SantCugatdelVallès" en tabla Localidad (por nombre)
  2. Si existe → obtener código_postal
  3. Si no existe → crear lookup table municipio_nombre → código_postal
  4. Si aún no encuentra → MARCAR COMO ERROR (municipio inválido)

Tabla de Localidad en BD:
  código | nombre               | provincia_id
  08172  | Sant Cugat del Vallès | 08 (Barcelona)
```

#### **MAPPING 2: Teléfono - Múltiples valores**

```
Campos:
  tel_fon = "932173600"
  tel_fon_m_bil = "620030453"

Problema: Dos campos de teléfono, but esquema global solo tiene "contacto"

Soluciones (elegir una):

Opción A: Concatenar
  contacto = "932173600 / 620030453"

Opción B: Prioridad (fijo primero)
  contacto = "932173600"
  (guardar móvil en campo extra)

Opción C: Crear campo teléfono_alternativo en BD
  contacto = "932173600"
  contacto_secundario = "620030453"

Recomendación: Opción B o C (conservar ambos)
```

#### **MAPPING 3: Limpiar espacios en dirección**

```
Entrada: "PladelVinyet,9BlocDbaixos"
Problema: Falta espacios

Proceso:
  1. Agregar espacio después de comas: "Pla del Vinyet, 9Bloc D baixos"
  2. Convertir a Case propio: "Pla del Vinyet, 9 Bloc D baixos"
  3. Validar formato

Salida: dirección = "Pla del Vinyet, 9 Bloc D baixos"
```

#### **MAPPING 4: Latitud/Longitud - GEOCODING REQUERIDO**

```
⚠️ PROBLEMA: Catalunya NO tiene latitud/longitud

Solución:
  1. Usar dirección: "Pla del Vinyet, 9 Bloc D baixos, 08172, Sant Cugat del Vallès"
  2. Llamar API de geocoding
  3. Obtener latitud/longitud (LL format)
  4. Convertir si necesario desde UTM a LL

Nota: Catalunya está en UTM Zona 31N, pero mapa usará LL (lat/lon)
```

#### **MAPPING 5: Ámbito - CAMPO FALTANTE**

```
⚠️ PROBLEMA CRÍTICO: Catalunya NO tiene campo "ámbito" (tipo de servicio)

Posibles soluciones:

Opción 1: Inferir de nombre de entidad
  Ej: "180º Para La Cooperación Y El Desarrollo" → MIGRACIÓN / INCLUSIÓN_SOCIAL
  Ej: "Acción Solidaria Igman" → INCLUSIÓN_SOCIAL
  (Requiere análisis manual o ML)

Opción 2: Crear tabla de mappings manual
  nom_de_l_entitat → ámbito (mapear manualmente cada una)

Opción 3: Dejar NULL en campo ámbito
  (Usuarios no pueden filtrar por tipo de servicio para Catalunya)

Opción 4: Pedir datos adicionales al gobierno de Catalunya
  (Mejor solución a largo plazo)

Recomendación: Opción 2 (crear mapping manual durante carga)
```

---

## 3️⃣ MAPPING VALENCIA (CSV)

### Esquema Fuente - Campos Disponibles

```csv
WKT,id,ni_centro,tipo_centro,nombre,max,entidad,domici,leyenda,cod_ine_mun,provincia,comarca,municipio,sector,clasificacion,pobtotal,email,telefono,f_resolu,x_25830,y_25830
"POINT (698055 4211247)","1","29",CENTROS SOCIALES,"CENTRO CIVICO-SOCIAL ""VIRGEN DEL PILAR""","0",AYUNTAMIENTO DE LOS MONTESINOS,"PZA.DE LA IGLESIA, 2",Entidad Local,"03903",Alacant/Alicante,el Baix Segura/La Vega Baja,Los Montesinos,POBLACIÓN EN GENERAL Y COLECTIVOS SOCIALMENTE DESFAVORECIDOS,POBLACIÓN EN GENERAL Y COLECTIVOS SOCIALMENTE DESFAVORECIDOS,"4912",zero@gva.es,"966721087",1995-09-12 00:00:00,"698055","4211247"
```

### Tabla de Mappings: Valencia → Esquema Global

```
┌──────────────────────────┬──────────────────┬─────────────────────┬─────────────────┐
│ Campo Fuente (Valencia)  │ Campo Global     │ Transformación      │ Notas           │
├──────────────────────────┼──────────────────┼─────────────────────┼─────────────────┤
│ id                       │ cod_entidad      │ Directo (cast STR)  │ Identificador   │
│ ni_centro                │ (extra)          │ Guardar en BD       │ Número interno  │
│ tipo_centro              │ ámbito           │ MAPPING (enum)*     │ Tipo de servicio│
│ nombre                   │ nombre           │ Directo (rename)    │ Nombre entidad  │
│ max                      │ (extra/ignorar)  │ Ignorar             │ No es relevante │
│ entidad                  │ (extra)          │ Guardar en BD       │ Tipo de org     │
│ domici                   │ dirección        │ Directo (rename)    │ Dirección       │
│ leyenda                  │ (extra)          │ Guardar en BD       │ Descripción     │
│ cod_ine_mun              │ código_postal    │ LOOKUP*             │ Convertir a CP  │
│ provincia                │ Provincia.nombre │ Lookup Provincia    │ Buscar provincia│
│ comarca                  │ (extra)          │ Guardar en BD       │ Información     │
│ municipio                │ Localidad.nombre │ Lookup Localidad    │ Buscar municipio│
│ sector                   │ (extra)          │ Guardar en BD       │ Sector social   │
│ clasificacion            │ (extra/descripción) │ Guardar en BD    │ Clasificación   │
│ pobtotal                 │ (extra)          │ Guardar en BD       │ Población zona  │
│ email                    │ (extra)          │ Guardar en BD       │ Email contacto  │
│ telefono                 │ contacto         │ Limpiar formato     │ Teléfono        │
│ f_resolu                 │ (extra)          │ Guardar en BD       │ Fecha resolución│
│ x_25830                  │ latitud          │ CONVERT UTM→LL*    │ Coordenada X    │
│ y_25830                  │ longitud         │ CONVERT UTM→LL*    │ Coordenada Y    │
│ WKT                      │ (alternativa)    │ Parse POINT(x y)    │ Formato WKT     │
└──────────────────────────┴──────────────────┴─────────────────────┴─────────────────┘
```

### Mappings Especiales para Valencia

#### **MAPPING 1: tipo_centro → ámbito (ENUM)**

```
Valencia tipo_centro  →  Global ámbito
───────────────────────────────────────
CENTROS SOCIALES                           → POBLACIÓN_EN_GENERAL/INCLUÍS ION_SOCIAL
HOGARES Y CLUBS PARA PERSONAS MAYORES     → MAYORES
RESIDENCIAS PARA PERSONAS MAYORES DEPENDIENTES → MAYORES
CENTRO ESPECÍFICO PARA ENFERMOS MENTALES  → SALUD_MENTAL
... (mapear todas las categorías según datos reales)

IMPORTANTE:
  - "POBLACIÓN EN GENERAL Y COLECTIVOS SOCIALMENTE DESFAVORECIDOS"
    → INCLUSIÓN_SOCIAL (o crear categoría nueva)
  - "PERSONAS MAYORES" → MAYORES
  - "PERSONAS CON ENFERMEDAD MENTAL" → SALUD_MENTAL
```

#### **MAPPING 2: cod_ine_mun → código_postal**

```
Entrada: cod_ine_mun = "03903"
Problema: Es código INE de municipio, no código postal

Solución:
  1. Buscar cod_ine_mun en tabla Localidad
  2. Si existe → obtener código_postal asociado
  3. Tabla de mappings: cod_ine_mun → código_postal

  Ejemplo:
  cod_ine_mun | municipio              | código_postal
  03903       | Los Montesinos         | 03550
  03120       | San Miguel de Salinas   | 03150
  03014       | Alacant/Alicante       | 03001-03015 (múltiples)

  Si municipio tiene múltiples códigos postales:
    - Usar el primero/principal
    - O buscar por dirección completa
```

#### **MAPPING 3: Conversión UTM → Lat/Lon**

```
DATO: Valencia proporciona coordenadas en formato UTM Zona 30 (ETRS89)
  x_25830 = 698055
  y_25830 = 4211247

Necesario: Convertir a Lat/Lon (formato estándar WGS84)

Biblioteca Python:
  pip install pyproj

Código:
  from pyproj import Transformer
  transformer = Transformer.from_crs("EPSG:25830", "EPSG:4326")
  lat, lon = transformer.transform(y_25830, x_25830)

  # Resultado (aproximado):
  # lat = 38.817, lon = -0.421

Esto es UNA VENTAJA de Valencia:
  ✅ YA tiene coordenadas (no necesita geocoding)
  ✅ Son precisas (del sistema de información del gobierno)
```

#### **MAPPING 4: Formato WKT (alternativa)**

```
Valencia también proporciona WKT:
  WKT = "POINT (698055 4211247)"

Opción alternativa (si es más fácil):
  1. Parsear WKT para obtener x, y
  2. Hacer conversión UTM → LL
  3. Guardar lat/lon

Ventaja: Información geométrica redundante (útil para validación)
```

#### **MAPPING 5: Teléfono - Limpieza**

```
Entrada: "966721087"
Proceso:
  1. Validar que sean solo dígitos
  2. Si está en formato internacional, normalizar
  3. Guardar

Salida: contacto = "966721087"
```

---

## 🔍 PROBLEMAS IDENTIFICADOS Y SOLUCIONES

### **Problema 1: Coordenadas Geográficas**

| Región    | Tiene Coords | Formato   | Solución                |
| --------- | ------------ | --------- | ----------------------- |
| Canarias  | ❌ NO        | -         | Geocoding de dirección  |
| Catalunya | ❌ NO        | -         | Geocoding de dirección  |
| Valencia  | ✅ SÍ        | UTM 25830 | Convertir UTM → Lat/Lon |

**Implementación:**

```python
# Para Canarias y Catalunya
from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="ngo_finder")
location = geolocator.geocode(direccion_completa)
latitud = location.latitude
longitud = location.longitude

# Para Valencia
from pyproj import Transformer
transformer = Transformer.from_crs("EPSG:25830", "EPSG:4326")
latitud, longitud = transformer.transform(y_25830, x_25830)
```

---

### **Problema 2: Campo Ámbito Faltante en Catalunya**

Catalunya NO tiene campo de tipo de servicio/ámbito.

**Solución propuesta:**

1. Crear tabla manual: nom_de_l_entitat → ámbito
2. Usar durante transformación
3. Marcar registros sin mapping → revisar manualmente

```python
# Mapping table manual
CATEGORIA_MAPPINGS = {
    "180º Para La Cooperación": "MIGRACIÓN",
    "1X1 Microcredit": "EMPLEO_E_INSERCIÓN_LABORAL",
    "Acción Solidaria": "INCLUSIÓN_SOCIAL",
    ...
}

# Durante transformación
ámbito = CATEGORIA_MAPPINGS.get(nom_de_l_entitat, "SIN_CATEGORÍA")
```

---

### **Problema 3: Formatos de Teléfono Inconsistentes**

- Canarias: "(34)928414484"
- Catalunya: "932173600"
- Valencia: "966721087"

**Solución:**

```python
def limpiar_telefono(tel):
    if not tel or tel == "_U":
        return None

    # Remover caracteres no numéricos
    tel = ''.join(c for c in tel if c.isdigit())

    # Si empieza con 34 (España), remover
    if tel.startswith('34'):
        tel = tel[2:]

    # Validar longitud (España: 9 dígitos)
    if len(tel) == 9:
        return tel

    return tel  # Devolver como está si no encaja
```

---

### **Problema 4: URLs Malformadas**

- Canarias: "wwwadepsi.org" (falta https://)
- Catalunya: "http://ca180gradosinfo/" (falta www, formato roto)
- Valencia: "http://...org" (variaciones)

**Solución:**

```python
def limpiar_url(url):
    if not url:
        return None

    url = url.strip()

    # Si no tiene protocolo, agregar
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Validar formato básico
    try:
        from urllib.parse import urlparse
        result = urlparse(url)
        if all([result.scheme, result.netloc]):
            return url
    except:
        pass

    return None  # URL inválida
```

---

### **Problema 5: Valores Null Inconsistentes**

- Canarias usa: "\_U" (Undefined)
- Catalunya: campos vacíos ""
- Valencia: ceros "0" o vacíos

**Solución:**

```python
def normalizar_nulo(valor):
    """Convierte todos los formatos de null a None"""
    if valor is None:
        return None
    if isinstance(valor, str):
        valor = valor.strip()
        if valor in ['', '_U', 'null', 'NULL', 'N/A', 'n/a', '0']:
            return None
    return valor if valor else None
```

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### Antes de Implementar Extractores

- [ ] Validar que todos los campos están documentados
- [ ] Verificar conversiones de tipos (string → float, etc.)
- [ ] Identificar valores null especiales (\_U, "", etc.)
- [ ] Crear lookup tables para foreign keys:
  - [ ] Provincia (id → nombre)
  - [ ] Localidad (código → nombre, provincia_id)
  - [ ] Ámbito mappings (source value → global enum)
  - [ ] Municipio → Código Postal mappings

### Durante Transformación

- [ ] Limpiar todos los campos (trim, lowercase/proper case)
- [ ] Validar tipos de datos
- [ ] Buscar claves foráneas
- [ ] Aplicar enum mappings
- [ ] Detectar errores (valores inválidos, faltantes)
- [ ] Geocoding para Canarias y Catalunya
- [ ] Conversión UTM → Lat/Lon para Valencia

### Después de Carga

- [ ] Verificar conteos de registros cargados
- [ ] Reportar registros reparados
- [ ] Reportar registros fallidos con motivos
- [ ] Validar FK constraints en BD
- [ ] Spot-check datos en mapa

---

## 📊 EJEMPLO DE TRANSFORMACIÓN COMPLETA

### Caso 1: Canarias

```
Entrada (JSON crudo):
{
  "nif": "G35068824",
  "denominacion": "Asociacion Adepsi",
  "direccion_tipo_via": "Calle",
  "direccion_nombre_via": "Lomo La Plana",
  "direccion_numero": "28",
  "direccion_provincia_id": "35",
  "direccion_provincia_nombre": "Las Palmas",
  "direccion_municipio_id": "35001",
  "area_id": "03",
  "area_nombre": "Discapacidad",
  "telefono_1": "(34)928414484",
  "pagina_web": "wwwadepsi.org"
}

Transformación:
  1. cod_entidad = nif = "G35068824"
  2. nombre = denominacion = "Asociacion Adepsi"
  3. dirección = "Calle Lomo La Plana 28"
  4. contacto = limpiar_telefono("(34)928414484") = "928414484"
  5. URL = limpiar_url("wwwadepsi.org") = "https://www.adepsi.org"
  6. área_id = "03" → lookup → ámbito = "DISCAPACIDAD"
  7. provincia_id = 35 (directo)
  8. código_postal = lookup(35001) en tabla Localidad = "35001"
  9. latitud, longitud = geocoding("Calle Lomo La Plana 28, 35001, Las Palmas")
     → (28.1234, -15.4321)

Salida (para BD):
{
  "cod_entidad": "G35068824",
  "nombre": "Asociacion Adepsi",
  "dirección": "Calle Lomo La Plana 28",
  "código_postal": "35001",
  "ámbito": "DISCAPACIDAD",
  "latitud": 28.1234,
  "longitud": -15.4321,
  "contacto": "928414484",
  "URL": "https://www.adepsi.org",
  "región_origen": "CAN"
}
```

### Caso 2: Valencia

```
Entrada (CSV crudo):
{
  "id": "1",
  "ni_centro": "29",
  "tipo_centro": "CENTROS SOCIALES",
  "nombre": "CENTRO CIVICO-SOCIAL 'VIRGEN DEL PILAR'",
  "domici": "PZA.DE LA IGLESIA, 2",
  "cod_ine_mun": "03903",
  "municipio": "Los Montesinos",
  "provincia": "Alacant/Alicante",
  "telefono": "966721087",
  "x_25830": "698055",
  "y_25830": "4211247"
}

Transformación:
  1. cod_entidad = "1"
  2. nombre = "Centro Civico-Social Virgen Del Pilar" (limpiar)
  3. dirección = "Pza. De La Iglesia, 2" (limpiar)
  4. contacto = "966721087" (directo)
  5. tipo_centro = "CENTROS SOCIALES" → lookup → ámbito = "INCLUSIÓN_SOCIAL"
  6. código_postal = lookup(03903) = "03550"
  7. latitud, longitud = convertir_utm_a_ll(698055, 4211247)
     → (38.1234, -0.5678)

Salida (para BD):
{
  "cod_entidad": "1",
  "nombre": "Centro Civico-Social Virgen Del Pilar",
  "dirección": "Pza. De La Iglesia, 2",
  "código_postal": "03550",
  "ámbito": "INCLUSIÓN_SOCIAL",
  "latitud": 38.1234,
  "longitud": -0.5678,
  "contacto": "966714087",
  "provincia_id": 3,
  "región_origen": "CV"
}
```

---

## 📝 DOCUMENTO DE ERRORES Y REPARACIONES

Durante la carga, documentar:

```
CANARIAS:
✓ 150 registros cargados correctamente
⚠ 5 registros reparados:
  - ID_001: Teléfono formatado (removidos paréntesis)
  - ID_002: URL corregida (agregado https://)
  - ID_003: Dirección normalizada (removidas tildes)
  - ID_004: Geocoding fallido → pendiente manual review
  - ID_005: Provincia inválida → asignado default
✗ 2 registros fallidos:
  - ID_XX: Municipio no existe en tabla Localidad
  - ID_YY: Geocoding no converge

CATALUNYA:
✓ 120 registros cargados correctamente
⚠ 8 registros reparados:
  - Ámbito inferido manualmente
  - Teléfonos normalizados
  - URLs reparadas
✗ 1 registro fallido:
  - Código postal inválido

VALENCIA:
✓ 200 registros cargados correctamente
⚠ 0 registros reparados (muy buena calidad)
✗ 0 registros fallidos
```

---

**Próximo paso:** Usar este documento de mappings durante la implementación de los extractores (semana 3-4).

**Actualización:** Este documento debe revisarse/ajustarse cuando se descarguen datos reales completos (actualmente solo tenemos primeros registros).
