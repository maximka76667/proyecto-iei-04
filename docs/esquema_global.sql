-- Esquema relacional inferido a partir del mapping del equipo 4.
-- Nota: DDL oficial no incluido entre los archivos aportados.


CREATE TABLE IF NOT EXISTS provincias (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  clave TEXT NOT NULL UNIQUE,
  codigo TEXT,
  nombre TEXT
);
CREATE TABLE IF NOT EXISTS localidades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  clave TEXT NOT NULL UNIQUE,
  codigo TEXT,
  nombre TEXT,
  provincia_id INTEGER REFERENCES provincias(id)
);
CREATE TABLE IF NOT EXISTS entidades (
  id_entidad INTEGER PRIMARY KEY AUTOINCREMENT,
  fuente TEXT NOT NULL CHECK (fuente IN ('CAN','CAT','CV')),
  id_origen TEXT NOT NULL,
  nombre TEXT NOT NULL,
  ambito TEXT,
  direccion TEXT,
  codigo_postal TEXT,
  longitud REAL,
  latitud REAL,
  descripcion TEXT,
  contacto TEXT,
  url TEXT,
  localidad_id INTEGER REFERENCES localidades(id),
  provincia_id INTEGER REFERENCES provincias(id),
  search_blob TEXT NOT NULL,
  raw_json TEXT NOT NULL,
  fingerprint TEXT NOT NULL,
  actualizado_en TEXT NOT NULL,
  UNIQUE (fuente, id_origen),
  CHECK ((longitud IS NULL AND latitud IS NULL) OR
         (longitud BETWEEN -180 AND 180 AND latitud BETWEEN -90 AND 90))
);
CREATE INDEX IF NOT EXISTS idx_entidades_fuente ON entidades(fuente);
CREATE INDEX IF NOT EXISTS idx_entidades_ambito ON entidades(ambito);
CREATE INDEX IF NOT EXISTS idx_entidades_coord ON entidades(longitud, latitud);
CREATE INDEX IF NOT EXISTS idx_entidades_localidad ON entidades(localidad_id);
CREATE INDEX IF NOT EXISTS idx_entidades_provincia ON entidades(provincia_id);
CREATE TABLE IF NOT EXISTS cargas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fuente TEXT NOT NULL,
  fecha TEXT NOT NULL,
  estado TEXT NOT NULL DEFAULT 'completada',
  registros_leidos INTEGER NOT NULL DEFAULT 0,
  insertados INTEGER NOT NULL DEFAULT 0,
  actualizados INTEGER NOT NULL DEFAULT 0,
  sin_cambios INTEGER NOT NULL DEFAULT 0,
  descartados INTEGER NOT NULL DEFAULT 0,
  incidencias INTEGER NOT NULL DEFAULT 0,
  reparaciones INTEGER NOT NULL DEFAULT 0,
  mensaje TEXT
);
CREATE TABLE IF NOT EXISTS incidencias (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  carga_id INTEGER NOT NULL REFERENCES cargas(id),
  fuente TEXT NOT NULL,
  fila INTEGER NOT NULL,
  entidad_id TEXT,
  campo TEXT NOT NULL,
  codigo TEXT NOT NULL,
  gravedad TEXT NOT NULL,
  descripcion TEXT NOT NULL,
  original TEXT,
  reparado TEXT
);
CREATE INDEX IF NOT EXISTS idx_incidencias_carga ON incidencias(carga_id);
