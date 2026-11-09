"""Almacén global relacional con trazabilidad del proceso ETL (SQLite)."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .mapping import map_row, search_text

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = """
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
  id_entidad TEXT PRIMARY KEY,
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
"""


def database_path() -> Path:
    return Path(os.getenv("IEI_DB_PATH", str(ROOT / "data" / "integrador.sqlite3")))


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    db_path = Path(path) if path is not None else database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.executescript(SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _upsert_geo(conn, table: str, key: str, code, name, province_id=None):
    row = conn.execute(f"SELECT id FROM {table} WHERE clave = ?", (key,)).fetchone()
    if row:
        conn.execute(f"UPDATE {table} SET codigo = ?, nombre = ?" + (", provincia_id = ?" if table == "localidades" else "") + " WHERE id = ?",
                     ((code, name, province_id, row["id"]) if table == "localidades" else (code, name, row["id"])))
        return row["id"]
    fields = "clave,codigo,nombre,provincia_id" if table == "localidades" else "clave,codigo,nombre"
    placeholders = "?,?,?,?" if table == "localidades" else "?,?,?"
    values = (key, code, name, province_id) if table == "localidades" else (key, code, name)
    return conn.execute(f"INSERT INTO {table} ({fields}) VALUES ({placeholders})", values).lastrowid


def process_source(source: str, rows: list[dict] | tuple[dict, ...], db_path=None) -> dict:
    """Carga una fuente con UPSERT idempotente, errores por fila y resumen persistido.

    Sólo se descartan registros sin id/nombre o IDs repetidos dentro de la misma
    fuente de importación. Otros errores se reparan o se dejan en NULL.
    """
    if source not in {"CV", "CAT", "CAN"}:
        raise ValueError("Fuente no válida")
    conn = connect(db_path)
    totals = dict(fuente=source, leidos=len(rows), insertados=0, actualizados=0,
                  sin_cambios=0, descartados=0, incidencias=0, reparaciones=0)
    try:
        with conn:
            load_id = conn.execute("INSERT INTO cargas (fuente, fecha, registros_leidos) VALUES (?, ?, ?)",
                                   (source, _now(), len(rows))).lastrowid
            seen_ids = set()
            for row_num, raw in enumerate(rows, start=1):
                if not isinstance(raw, dict):
                    raw = {}
                mapped = map_row(source, raw)
                ent_id = mapped.entity.get("id_entidad")
                if ent_id and ent_id in seen_ids:
                    mapped.accepted = False
                    mapped.note("id_entidad", "duplicado_lote", "error", "ID de origen duplicado en el mismo lote", ent_id)
                if ent_id:
                    seen_ids.add(ent_id)
                for issue in mapped.issues:
                    conn.execute("""INSERT INTO incidencias
                       (carga_id,fuente,fila,entidad_id,campo,codigo,gravedad,descripcion,original,reparado)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                       (load_id, source, row_num, ent_id, issue.field, issue.code,
                        issue.severity, issue.message, issue.original, issue.repaired))
                    totals["incidencias"] += 1
                    if issue.severity == "reparacion":
                        totals["reparaciones"] += 1
                if not mapped.accepted:
                    totals["descartados"] += 1
                    continue

                province = mapped.province
                prov_id = None
                if province["codigo"] or province["nombre"]:
                    prov_key = "code:" + province["codigo"] if province["codigo"] else "name:" + source + ":" + search_text(province["nombre"])
                    prov_id = _upsert_geo(conn, "provincias", prov_key, province["codigo"], province["nombre"])
                locality = mapped.locality
                loc_id = None
                if locality["codigo"] or locality["nombre"]:
                    loc_key = "code:" + locality["codigo"] if locality["codigo"] else "name:" + source + ":" + str(prov_id) + ":" + search_text(locality["nombre"])
                    loc_id = _upsert_geo(conn, "localidades", loc_key, locality["codigo"], locality["nombre"], prov_id)

                ent = mapped.entity
                haystack = " ".join(search_text(v) for v in
                                    (ent["nombre"], ent["direccion"], ent["descripcion"],
                                     ent["ambito"], locality["nombre"], province["nombre"]) if v)
                raw_json = json.dumps(raw, ensure_ascii=False, sort_keys=True)
                normalized_json = json.dumps([ent, loc_id, prov_id], ensure_ascii=False, sort_keys=True)
                fingerprint = hashlib.sha256(normalized_json.encode("utf-8")).hexdigest()
                previous = conn.execute("SELECT fingerprint FROM entidades WHERE id_entidad=?", (ent_id,)).fetchone()
                if previous and previous["fingerprint"] == fingerprint:
                    totals["sin_cambios"] += 1
                    continue
                columns = ["id_entidad", "fuente", "id_origen", "nombre", "ambito", "direccion", "codigo_postal",
                           "longitud", "latitud", "descripcion", "contacto", "url", "localidad_id", "provincia_id",
                           "search_blob", "raw_json", "fingerprint", "actualizado_en"]
                args = [ent["id_entidad"], ent["fuente"], ent["id_origen"], ent["nombre"],
                        ent["ambito"], ent["direccion"], ent["codigo_postal"], ent["longitud"], ent["latitud"],
                        ent["descripcion"], ent["contacto"], ent["url"], loc_id, prov_id, haystack,
                        raw_json, fingerprint, _now()]
                updates = ", ".join(f"{field}=excluded.{field}" for field in columns[1:])
                conn.execute(f"INSERT INTO entidades ({', '.join(columns)}) VALUES ({','.join('?' * len(columns))}) "
                             f"ON CONFLICT(id_entidad) DO UPDATE SET {updates}", args)
                if previous:
                    totals["actualizados"] += 1
                else:
                    totals["insertados"] += 1
            conn.execute("""UPDATE cargas SET insertados=?, actualizados=?, sin_cambios=?,
                         descartados=?, incidencias=?, reparaciones=? WHERE id=?""",
                         (totals["insertados"], totals["actualizados"], totals["sin_cambios"],
                          totals["descartados"], totals["incidencias"], totals["reparaciones"], load_id))
            totals["carga_id"] = load_id
    finally:
        conn.close()
    return totals


def escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def make_where(q=None, municipio=None, provincia=None, ambito=None, fuente=None, bbox=None):
    clauses, args = [], []
    if q:
        clauses.append("e.search_blob LIKE ? ESCAPE '\\'")
        args.append("%" + escape_like(search_text(q)) + "%")
    if municipio:
        clauses.append("LOWER(COALESCE(l.nombre,'')) LIKE ? ESCAPE '\\'")
        args.append("%" + escape_like(municipio.strip().lower()) + "%")
    if provincia:
        clauses.append("LOWER(COALESCE(p.nombre,'')) LIKE ? ESCAPE '\\'")
        args.append("%" + escape_like(provincia.strip().lower()) + "%")
    if ambito:
        clauses.append("e.ambito = ?")
        args.append(ambito)
    if fuente:
        clauses.append("e.fuente = ?")
        args.append(fuente)
    if bbox:
        west, south, east, north = bbox
        clauses.append("e.longitud IS NOT NULL AND e.latitud BETWEEN ? AND ?")
        args.extend([south, north])
        if west <= east:
            clauses.append("e.longitud BETWEEN ? AND ?")
            args.extend([west, east])
        else:  # Bounding box que atraviesa el antimeridiano
            clauses.append("(e.longitud >= ? OR e.longitud <= ?)")
            args.extend([west, east])
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", args


ENTITY_SELECT = """SELECT e.id_entidad, e.fuente, e.id_origen, e.nombre, e.ambito,
 e.direccion, e.codigo_postal, e.longitud, e.latitud, e.descripcion, e.contacto,
 e.url, l.codigo AS localidad_codigo, l.nombre AS localidad, p.codigo AS provincia_codigo,
 p.nombre AS provincia
 FROM entidades e LEFT JOIN localidades l ON e.localidad_id = l.id
 LEFT JOIN provincias p ON e.provincia_id = p.id"""


def search_entities(db_path=None, *, q=None, municipio=None, provincia=None,
                    ambito=None, fuente=None, bbox=None, limit=30, offset=0):
    conn = connect(db_path)
    try:
        where, args = make_where(q, municipio, provincia, ambito, fuente, bbox)
        total = conn.execute("SELECT COUNT(*) AS n FROM entidades e LEFT JOIN localidades l ON e.localidad_id = l.id LEFT JOIN provincias p ON e.provincia_id = p.id" + where, args).fetchone()["n"]
        rows = conn.execute(ENTITY_SELECT + where + " ORDER BY e.nombre COLLATE NOCASE, e.id_entidad LIMIT ? OFFSET ?",
                            [*args, limit, offset]).fetchall()
        return {"total": total, "limit": limit, "offset": offset, "items": [dict(row) for row in rows]}
    finally:
        conn.close()


def get_entity(identifier: str, db_path=None):
    conn = connect(db_path)
    try:
        row = conn.execute(ENTITY_SELECT + " WHERE e.id_entidad = ?", (identifier,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def statistics(db_path=None):
    conn = connect(db_path)
    try:
        total = conn.execute("SELECT COUNT(*) AS n FROM entidades").fetchone()["n"]
        geo = conn.execute("SELECT COUNT(*) AS n FROM entidades WHERE longitud IS NOT NULL AND latitud IS NOT NULL").fetchone()["n"]
        by_source = {row["fuente"]: row["n"] for row in conn.execute("SELECT fuente,COUNT(*) AS n FROM entidades GROUP BY fuente")}
        return {"total": total, "geolocalizadas": geo, "sin_coordenadas": total - geo,
                "fuentes": {source: by_source.get(source, 0) for source in ("CV", "CAT", "CAN")}}
    finally:
        conn.close()


def filters_metadata(db_path=None):
    conn = connect(db_path)
    try:
        provinces = [row[0] for row in conn.execute("SELECT DISTINCT nombre FROM provincias WHERE nombre IS NOT NULL ORDER BY nombre COLLATE NOCASE")]
        ambit = [row[0] for row in conn.execute("SELECT DISTINCT ambito FROM entidades WHERE ambito IS NOT NULL ORDER BY ambito")]
        return {"provincias": provinces, "ambitos": ambit, "fuentes": ["CV", "CAT", "CAN"]}
    finally:
        conn.close()


def loads_history(db_path=None, limit=20):
    conn = connect(db_path)
    try:
        return [dict(row) for row in conn.execute("SELECT * FROM cargas ORDER BY id DESC LIMIT ?", (limit,))]
    finally:
        conn.close()


def load_issues(load_id: int, db_path=None, limit=100, offset=0):
    conn = connect(db_path)
    try:
        exists = conn.execute("SELECT id FROM cargas WHERE id=?", (load_id,)).fetchone()
        if not exists:
            return None
        count = conn.execute("SELECT COUNT(*) FROM incidencias WHERE carga_id=?", (load_id,)).fetchone()[0]
        rows = conn.execute("SELECT * FROM incidencias WHERE carga_id=? ORDER BY id LIMIT ? OFFSET ?", (load_id,limit,offset)).fetchall()
        return {"carga_id": load_id, "total": count, "limit": limit, "offset": offset, "items": [dict(row) for row in rows]}
    finally:
        conn.close()
