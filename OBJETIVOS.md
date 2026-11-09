# PROYECTO BUSCADOR DE ONGD

## Integración e Interoperabilidad - Curso 2026-27

---

## 📋 DESCRIPCIÓN GENERAL DEL PROYECTO

Construir una **aplicación buscadora de ONGD (organizaciones no gubernamentales)** que integre datos de 3 regiones españolas diferentes usando formatos y esquemas distintos.

**Objetivo Principal:** Crear una interfaz de búsqueda unificada que haga que los datos de múltiples fuentes heterogéneas aparezcan como un único recurso.

---

## 🎯 OBJETIVOS PRINCIPALES

1. **Extraer** datos de 3 fuentes regionales diferentes (formatos distintos)
2. **Transformar** a un esquema global común usando mappings semánticos
3. **Cargar** en un almacén de datos centralizado
4. **Buscar** en la base de datos unificada (NO en archivos originales)
5. **Mostrar** resultados en mapa interactivo y formularios

---

## 🏗️ DESCRIPCIÓN DE LA ARQUITECTURA

```
FUENTES DE DATOS (Los Extractores Leen Esto Una Sola Vez)
├─ Canarias (JSON)
├─ Catalunya (XML)
└─ Comunitat Valenciana (CSV)
       ↓
[EXTRACTORES - Parsean y Devuelven Datos Crudos]
├─ Extractor_CAN  → {nombres de campo originales}
├─ Extractor_CAT  → {nombres de campo originales}
└─ Extractor_CV   → {nombres de campo originales}
       ↓
[TRANSFORMADOR - Aplica Mappings Semánticos]
├─ Mapea nombres de campos (nombreEntidad → nombre)
├─ Mapea valores enum (diferentes tipos → ámbito)
├─ Busca claves foráneas (provincia string → ID)
└─ Valida y maneja errores
       ↓
[ALMACÉN DE DATOS - PostgreSQL]
├─ Tabla Entidad (registros principales)
├─ Tabla Localidad (ciudades/códigos postales)
└─ Tabla Provincia (provincias)
       ↓
[DOS APIs]
├─ API de Carga (POST /load) → Extrae, Transforma, Inserta
└─ API de Búsqueda (GET /search) → Consulta BD, devuelve resultados
       ↓
[INTERFAZ DE USUARIO]
├─ Formulario de búsqueda (ciudad, código postal, provincia, tipo)
└─ Mapa interactivo (OpenLayers) → muestra resultados con lat/lon
```

---

## 📊 ESQUEMA GLOBAL DE LA BASE DE DATOS

### **Tabla Provincia**

```
┌────────────────────────────────┐
│ Provincia                      │
├────────────────────────────────┤
│ código (PK)      : INT         │
│ nombre           : VARCHAR(100)│
└────────────────────────────────┘
```

### **Tabla Localidad**

```
┌────────────────────────────────┐
│ Localidad                      │
├────────────────────────────────┤
│ código (PK)      : VARCHAR(5)  │
│ nombre           : VARCHAR(100)│
│ provincia_id (FK): INT         │
└────────────────────────────────┘
```

### **Tabla Entidad** (Principal)

```
┌────────────────────────────────┐
│ Entidad                        │
├────────────────────────────────┤
│ cod_entidad (PK) : VARCHAR(50) │
│ nombre           : VARCHAR(200)│
│ ámbito           : VARCHAR(50) │
│ dirección        : VARCHAR(300)│
│ código_postal(FK): VARCHAR(5)  │
│ latitud          : FLOAT       │
│ longitud         : FLOAT       │
│ descripción      : TEXT        │
│ contacto         : VARCHAR(100)│
│ URL              : VARCHAR(200)│
│ región_origen    : VARCHAR(3)  │ (CAN, CAT, CV)
└────────────────────────────────┘
```

### **Valores Enum para Ámbito**

```
MAYORES
DISCAPACIDAD
SALUD_MENTAL
INFANCIA_Y_JUVENTUD
MUJER
MIGRACIÓN
INCLUSIÓN_SOCIAL
EDUCACIÓN_Y_FORMACIÓN
EMPLEO_E_INSERCIÓN_LABORAL
SALUD_Y_ATENCIÓN_SOCIOSANITARIA
VOLUNTARIADO_Y_PARTICIPACIÓN_COMUNITARIA
CULTURA_Y_DESARROLLO_COMUNITARIO
```

---

## 📡 FUENTES DE DATOS Y MAPPINGS

### **Fuente 1: CANARIAS (JSON)**

**URL de Datos:** https://bit.ly/3TehHk8

**Tareas:**

- [ ] Descargar e inspeccionar estructura JSON
- [ ] Documentar todos los nombres de campos y tipos
- [ ] Crear mapping: Canarias → esquema global
- [ ] Definir mappings de valores para enum ámbito

**Campos Esperados:** id, nombreEntidad, tipoServicio, direccion, codigoPostal, provincia, latitud, longitud, descripcion, telefono, ...

---

### **Fuente 2: CATALUNYA (XML)**

**URL de Datos:** https://bit.ly/4dPgAOL

**Tareas:**

- [ ] Descargar e inspeccionar estructura XML
- [ ] Documentar todos los nombres de campos y tipos
- [ ] Crear mapping: Catalunya → esquema global
- [ ] Definir mappings de valores para enum ámbito

**Campos Esperados:** oid, nom_entitat, tipus_activitat, adreca, codi_postal, provincia, latitud, longitud, descripció, telèfon, web, ...

---

### **Fuente 3: COMUNITAT VALENCIANA (CSV)**

**URL de Datos:** https://bit.ly/4dtoMnH

**Tareas:**

- [ ] Descargar e inspeccionar estructura CSV
- [ ] Documentar todos los nombres de campos y tipos
- [ ] Crear mapping: Valencia → esquema global
- [ ] Definir mappings de valores para enum ámbito

**Campos Esperados:** ID, Nombre, Tipo_Servicio, Dirección, CP, Provincia, Latitud, Longitud, Descripción, Teléfono, Website, ...

---

## 📋 DOCUMENTO DE MAPPINGS SEMÁNTICOS

Crear tablas de mapping detalladas que muestren:

| Campo Fuente | Campo Global | Transformación | Notas            |
| ------------ | ------------ | -------------- | ---------------- |
| Campo1       | objetivo1    | Cómo convertir | Casos especiales |
| Campo2       | objetivo2    | Cómo convertir | Casos especiales |

**Para cada una de las 3 fuentes:**

- Mapping Canarias
- Mapping Catalunya
- Mapping Valencia

**Incluir:**

- Renombramientos directos de campos
- Mappings de valores enum (tipoServicio → ámbito con conversiones de valores)
- Búsquedas de claves foráneas (provincia string → Provincia.id)
- Conversiones de tipos de datos (string → float para lat/lon)
- Manejo de campos faltantes
- Casos de error

---

## 💻 STACK TECNOLÓGICO (RECOMENDADO)

| Componente        | Tecnología                   | Razón                                                |
| ----------------- | ---------------------------- | ---------------------------------------------------- |
| **Backend**       | Python + FastAPI             | Amigable con ETL, manejo de datos                    |
| **Base de Datos** | PostgreSQL                   | Relacional, bueno para esquemas, soporte geoespacial |
| **ETL**           | Pandas, sqlalchemy, requests | Transformación de datos                              |
| **Frontend**      | React + TypeScript           | UI moderna, basada en componentes                    |
| **Mapas**         | OpenLayers                   | Visualización de mapas interactivos                  |
| **Docs API**      | Swagger/OpenAPI              | Auto-generado desde FastAPI                          |

---

## 🔧 CRONOGRAMA DETALLADO POR FASE

### **FASE 1: ENUNCIADO Y PLANIFICACIÓN**

#### Semana 1: 28/09 - 30/09

- **28/09 (Lunes):** Enunciado del proyecto. Discusión sobre objetivos y alcance
- **30/09 (Miércoles):** Enunciado del proyecto. Discusión sobre objetivos y alcance

**Tareas a completar:**

- [ ] Leer y comprender el enunciado completo
- [ ] Identificar requisitos principales
- [ ] Formar equipos (5 personas)
- [ ] Planificar reuniones y división de tareas

---

### **FASE 2: ESQUEMAS Y MAPPINGS SEMÁNTICOS**

#### Semana 2-3: 05/10 - 14/10

**05/10 (Lunes):** Elaboración esquemas fuentes y mappings
**07/10 (Miércoles):** Elaboración esquemas fuentes y mappings

**Tareas a completar:**

- [ ] Descargar los 3 archivos de datos (CAN, CAT, CV)
- [ ] Analizar estructura JSON de Canarias
- [ ] Analizar estructura XML de Catalunya
- [ ] Analizar estructura CSV de Valencia
- [ ] Documentar todos los campos de cada fuente
- [ ] Crear tablas de mappings semánticos (3 documentos)
- [ ] Diseñar esquema PostgreSQL global
- [ ] Documentar conversiones de enums (ámbito)

**12/10:** SIN CLASE DE PRÁCTICAS

**14/10 (Miércoles):** Revisión mappings

- [ ] Presentar mappings para revisión

**19/10 (Lunes):** Revisión mappings

- [ ] Incorporar feedback de la revisión

---

### **FASE 3: IMPLEMENTACIÓN DE EXTRACTORES (Parte 1 de 3)**

#### Semana 4: 19/10 - 26/10

**19/10 (Lunes):** Revisión mappings (completar si falta)

**26/10 (Lunes):** Implementación extractores 1

- [ ] Implementar Extractor_CAN (JSON)
- [ ] Implementar validaciones básicas
- [ ] Probar con datos reales

**Tareas a completar:**

- [ ] Extractor_CAN debe parsear JSON y devolver dicts
- [ ] Documentar formato de salida
- [ ] Realizar pruebas unitarias

---

### **FASE 4: IMPLEMENTACIÓN DE EXTRACTORES (Parte 2 de 3)**

#### Semana 5: 28/10 - 09/11

**28/10 (Miércoles):** Implementación extractores 2

- [ ] Implementar Extractor_CAT (XML)
- [ ] Implementar validaciones básicas
- [ ] Probar con datos reales

**02/11:** SIN CLASE DE PRÁCTICAS

**04/11:** SIN CLASE DE PRÁCTICAS

**09/11 (Lunes):** Implementación extractores 2 (continuación)

- [ ] Finalizar Extractor_CAT
- [ ] Integrar con transformador provisional
- [ ] Pruebas end-to-end parciales

**Tareas a completar:**

- [ ] Extractor_CAT debe parsear XML y devolver dicts
- [ ] Documentar formato de salida
- [ ] Realizar pruebas unitarias

---

### **FASE 5: IMPLEMENTACIÓN DE EXTRACTORES (Parte 3 de 3)**

#### Semana 6: 11/11 - 23/11

**11/11 (Miércoles):** Implementación extractores 3

- [ ] Implementar Extractor_CV (CSV)
- [ ] Implementar validaciones básicas
- [ ] Probar con datos reales

**16/11 (Lunes):** Implementación extractores 3 (continuación)

- [ ] Finalizar Extractor_CV
- [ ] Todos los 3 extractores funcionando
- [ ] Pipeline ETL funcional

**Tareas a completar:**

- [ ] Extractor_CV debe parsear CSV y devolver dicts
- [ ] Documentar formato de salida
- [ ] Realizar pruebas unitarias
- [ ] Implementar Transformador (aplica mappings)
- [ ] Implementar manejo de errores
- [ ] Pruebas end-to-end del pipeline ETL completo

---

### **ENTREGABLE 1: CÓDIGO + DEMO**

#### 18/11 (Miércoles) / 23/11 (Lunes)

**ÚLTIMA FECHA PARA ENTREGAR: 23/11**

**Qué debe funcionar:**

- ✅ Extractor_CAN: extrae JSON y devuelve datos crudos
- ✅ Extractor_CAT: extrae XML y devuelve datos crudos
- ✅ Extractor_CV: extrae CSV y devuelve datos crudos
- ✅ Transformador: aplica mappings semánticos a datos de cualquier fuente
- ✅ Cargador: inserta datos transformados en PostgreSQL
- ✅ Manejo de errores: detecta, reporta y repara errores
- ✅ Base de datos: esquema PostgreSQL implementado

**Qué entregar:**

- [ ] Código fuente completo (en Git/GitHub)
- [ ] Scripts SQL para crear tablas
- [ ] Demo ejecutable mostrando:
  - Extracción de datos de las 3 fuentes
  - Transformación correcta
  - Carga en base de datos
  - Reporte de errores y reparaciones
- [ ] Documentación de:
  - Mappings semánticos (3 documentos)
  - Esquema de base de datos
  - Instrucciones de ejecución

---

### **FASE 6: API DE CARGA + FORMULARIO**

#### Semana 7-8: 25/11 - 02/12

**25/11 (Lunes):** Implementación API de carga + formulario

- [ ] Crear endpoint POST /load
- [ ] Implementar selección de regiones (CAN, CAT, CV)
- [ ] Crear UI para seleccionar regiones
- [ ] Mostrar progreso y resultados de carga

**30/11 (Lunes):** Implementación API de carga + formulario (continuación)

- [ ] API de carga completamente funcional
- [ ] Formulario de carga en UI
- [ ] Manejo de errores robusto
- [ ] Reporte detallado de carga

**Tareas a completar:**

- [ ] FastAPI endpoint para POST /load
- [ ] Selector de regiones en formulario
- [ ] Reporte de progreso (registros cargados, reparados, fallidos)
- [ ] Base de datos se limpia/actualiza en cada carga

---

### **FASE 7: API DE BÚSQUEDA + FORMULARIO + MASHUP DE MAPAS**

#### Semana 9-10: 02/12 - 21/12

**02/12 (Lunes):** Implementación API de consulta + formulario + mashup

- [ ] Crear endpoint GET /search
- [ ] Implementar filtros (ciudad, código postal, provincia, tipo)
- [ ] Crear formulario de búsqueda en UI
- [ ] Integrar mapa OpenLayers
- [ ] Mostrar resultados en mapa con lat/lon

**07/12 (Miércoles):** Implementación API de consulta + formulario + mashup (continuación)

**09/12 (Lunes):** Implementación API de consulta + formulario + mashup (continuación)

**14/12 (Miércoles):** Implementación API de consulta + formulario + mashup (continuación)

**16/12 (Lunes):** Implementación API de consulta + formulario + mashup (continuación)

**21/12 (Lunes):** Implementación API de consulta + formulario + mashup (finalización)

- [ ] API de búsqueda completamente funcional
- [ ] Todos los filtros funcionando
- [ ] Mapa interactivo mostrando resultados
- [ ] UI pulida y responsive

**Tareas a completar:**

- [ ] FastAPI endpoint para GET /search
- [ ] Filtros por: ciudad, código postal, provincia, tipo de servicio
- [ ] Formulario de búsqueda con validaciones
- [ ] Integración OpenLayers
- [ ] Marcadores en mapa con información de entidades
- [ ] Pop-ups informativos al hacer clic en marcador
- [ ] API documentation con Swagger

**23/12:** SIN CLASE DE PRÁCTICAS

---

### **ENTREGABLE 2: APLICACIÓN FINALIZADA**

#### 07/01 (Entrega Final)

**ÚLTIMA FECHA PARA ENTREGAR: 07/01/2027**

**Qué debe funcionar:**

- ✅ FASE 1-5: Todos los extractores + transformador + carga en BD
- ✅ FASE 6: API de carga + formulario de carga
- ✅ FASE 7: API de búsqueda + formulario de búsqueda + mapa interactivo
- ✅ Manejo robusto de errores en todas las fases
- ✅ Documentación completa (APIs, esquemas, mappings)
- ✅ UI profesional y usable

**Qué entregar:**

- [ ] Código fuente completo
- [ ] Base de datos PostgreSQL lista para usar
- [ ] Aplicación ejecutable (backend + frontend)
- [ ] Documentación:
  - README con instrucciones de instalación
  - API documentation (Swagger/OpenAPI)
  - Mappings semánticos (detallado)
  - Esquema de base de datos (diagrama ERD)
  - Guía de usuario (cómo usar la aplicación)
- [ ] Video/demo mostrando:
  - Cargar datos de las 3 regiones
  - Búsqueda por diferentes criterios
  - Resultados en mapa
  - Manejo de errores

---

## ⚠️ REQUISITOS DE MANEJO DE ERRORES

El proyecto incluirá conjuntos de datos de prueba con errores intencionales. Tu sistema debe:

### **Detectar e Informar:**

- [ ] Errores de formato (fechas malformadas, códigos postales no numéricos)
- [ ] Valores null/faltantes
- [ ] Datos fuera de rango (códigos postales inválidos)
- [ ] Datos inconsistentes (código postal no coincide con provincia)
- [ ] Duplicados

### **Manejar y Reparar (si es posible):**

- [ ] Reportar qué registros fallaron
- [ ] Reparar cuando sea posible (eliminar espacios, estandarizar formatos)
- [ ] Reportar conteos de registros fallidos Y reparados

### **Formato de Salida:**

```
Carga completada:
✓ Se cargaron 350 registros
⚠ Se repararon 5 registros (problemas auto-corregidos)
✗ Fallaron 2 registros (no se pudieron reparar)

Detalles de registros fallidos:
- Registro ID_001: Código postal inválido "XXXXX"
- Registro ID_002: Falta el campo requerido "nombre"
```

---

## 🎓 CONCEPTOS CLAVE (Objetivos de Aprendizaje)

- **Integración de Datos:** Combinar datos de múltiples fuentes heterogéneas
- **Pipeline ETL:** Proceso Extract, Transform, Load
- **Mappings Semánticos:** Documentar cómo esquemas diferentes se relacionan
- **Arquitectura SOA:** Exponer funcionalidad mediante APIs
- **Calidad de Datos:** Validar, limpiar, reportar errores
- **Interoperabilidad:** Hacer que formatos diversos funcionen juntos

---

## 👥 ESTRUCTURA DEL EQUIPO

- **Tamaño de grupo:** 5 personas
- **Reuniones:** Semanales durante prácticas + tutorías por Teams
- **Soporte:** Enfoque en aspectos de ingeniería de datos, no programación básica
- **Lenguaje/Herramientas:** Tu elección

---

## 📚 MATERIALES PROPORCIONADOS

- [ ] Técnicas de extracción de datos (Selenium para datos semi-estructurados)
- [ ] Documentación y ejemplos de OpenLayers
- [ ] Diagrama de esquema global
- [ ] Acceso a herramienta Altova (para trabajo con XML/mappings)
- [ ] Fuentes de datos en Poliformat

**Ubicación Poliformat:**  
`Recursos/Proyecto-prácticas/Fuentes de datos/{Comunitat Valenciana | Catalunya | Canarias}`

---

## ✅ CRITERIOS DE ÉXITO

Tu aplicación es exitosa cuando:

1. ✅ Pueda extraer datos de las 3 fuentes en formatos diferentes
2. ✅ Los datos se transforman correctamente al esquema común
3. ✅ Todos los datos se cargan en base de datos PostgreSQL
4. ✅ API de búsqueda consulta base de datos (NO archivos) y devuelve resultados
5. ✅ Los resultados se muestran en mapa interactivo con lat/lon correcto
6. ✅ Los errores se detectan, reportan y (cuando es posible) reparan
7. ✅ Todas las APIs están documentadas con Swagger
8. ✅ El usuario puede buscar por ciudad, código postal, provincia, tipo de servicio
9. ✅ El usuario puede cargar datos de cualquiera/todas las regiones
10. ✅ El sistema maneja datos faltantes/inválidos correctamente

---

## 🚀 PRÓXIMOS PASOS INMEDIATOS (28/09 - 05/10)

1. **Descargar los 3 archivos de datos** desde Poliformat
2. **Analizar su estructura** (JSON, XML, CSV)
3. **Documentar los campos** en cada uno
4. **Crear documento de mappings semánticos**
5. **Diseñar esquema PostgreSQL** basado en esquema global
6. **Elegir stack tecnológico** (recomendado: Python + FastAPI + PostgreSQL)
7. **Prepararse para implementar extractores el 26/10**

---

**¡Mucho éxito! 🎯**
