"""API de búsqueda, carga ETL, mapa y transformación de coordenadas.

Documentación Swagger: /docs | Especificación: /openapi.json
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .database import (connect, process_source, search_entities, get_entity, statistics,
                       filters_metadata, loads_history, load_issues)
from .mapping import convert_utm

ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title="IEI – Integrador de entidades del Tercer Sector", version="2.0.0",
              description="Buscador y carga ETL sobre CV (CSV), CAT (XML) y CAN (JSON). "
                          "Los wrappers exponen los datos por HTTP; los extractores aplican mappings semánticos, validan y registran incidencias.")
app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")

DEFAULT_WRAPPERS = {"CAN": "http://127.0.0.1:8101", "CAT": "http://127.0.0.1:8102", "CV": "http://127.0.0.1:8103"}


class LoadRequest(BaseModel):
    sources: list[Literal["CV", "CAT", "CAN"]] = Field(default_factory=lambda: ["CV", "CAT", "CAN"], min_length=1)


class ConvertRequest(BaseModel):
    x_25830: float
    y_25830: float


def wrapper_url(source: str) -> str:
    return os.environ.get("IEI_WRAPPER_" + source + "_URL", DEFAULT_WRAPPERS[source]).rstrip("/")


def extract_http(source: str) -> list[dict]:
    """Extractor HTTP paginado. No consulta directamente el fichero original."""
    result = []
    with httpx.Client(timeout=30.0, follow_redirects=False) as client:
        page = 1
        total = None
        while True:
            response = client.get(wrapper_url(source) + "/records", params={"page": page, "page_size": 500})
            response.raise_for_status()
            data = response.json()
            if data.get("source") != source or not isinstance(data.get("records"), list):
                raise ValueError("El wrapper respondió con fuente o formato inesperado")
            if total is None:
                total = data.get("total")
                if not isinstance(total, int) or total < 0 or total > 1_000_000:
                    raise ValueError("El wrapper devolvió un total no válido")
            rows = data["records"]
            if not rows and len(result) < total:
                raise ValueError("El wrapper terminó antes de devolver todos los registros")
            result.extend(rows)
            if len(result) >= total:
                if len(result) != total:
                    raise ValueError("El wrapper devolvió más registros que el total declarado")
                break
            page += 1
    return result


def parse_bbox(value: str | None):
    if value is None or value.strip() == "":
        return None
    try:
        values = tuple(float(v.strip()) for v in value.split(","))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="bbox debe ser oeste,sur,este,norte") from exc
    if len(values) != 4:
        raise HTTPException(status_code=422, detail="bbox debe tener cuatro coordenadas")
    west, south, east, north = values
    import math
    if not all(map(math.isfinite, values)) or not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= 90 and -90 <= north <= 90) or south > north:
        raise HTTPException(status_code=422, detail="bbox tiene límites inválidos")
    return values


@app.get("/", include_in_schema=False)
def landing():
    return FileResponse(ROOT / "frontend" / "index.html")


@app.get("/api/health", tags=["Sistema"], summary="Estado del integrador")
def health():
    with connect() as conn:
        pass
    return {"status": "ok", "service": "integrador", "version": "2.0.0"}


@app.get("/api/sources", tags=["Sistema"], summary="Wrappers configurados")
def sources():
    return [{"source": source, "url": wrapper_url(source)} for source in ("CV", "CAT", "CAN")]


@app.post("/api/load", tags=["Carga"], summary="Ejecutar la carga ETL de una o varias fuentes")
def load(req: LoadRequest):
    results = []
    for source in dict.fromkeys(req.sources):
        try:
            raw_rows = extract_http(source)
            result = process_source(source, raw_rows)
            results.append({"source": source, "status": "ok", **result})
        except (httpx.HTTPError, ValueError, OSError, RuntimeError) as exc:
            results.append({"source": source, "status": "error", "message": str(exc)})
    return {"status": "ok" if all(r["status"] == "ok" for r in results) else "partial_error", "results": results}


@app.get("/api/entities", tags=["Búsqueda"], summary="Buscar entidades con filtros y paginación")
def entities(q: str | None = Query(None, max_length=200),
             municipio: str | None = Query(None, max_length=150),
             provincia: str | None = Query(None, max_length=150),
             ambito: str | None = Query(None, max_length=100),
             fuente: Literal["CV", "CAT", "CAN"] | None = None,
             bbox: str | None = None,
             limit: int = Query(30, ge=1, le=200), offset: int = Query(0, ge=0)):
    return search_entities(q=q, municipio=municipio, provincia=provincia,
                           ambito=ambito, fuente=fuente, bbox=parse_bbox(bbox),
                           limit=limit, offset=offset)


@app.get("/api/entities/{entity_id}", tags=["Búsqueda"], summary="Detalles de una entidad")
def entity(entity_id: str):
    result = get_entity(entity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Entidad no encontrada")
    return result


@app.get("/api/map", tags=["Mapa"], summary="Entidades geolocalizadas en formato GeoJSON")
def map_geojson(bbox: str | None = None, q: str | None = Query(None, max_length=200),
                municipio: str | None = Query(None, max_length=150),
                provincia: str | None = Query(None, max_length=150),
                ambito: str | None = Query(None, max_length=100),
                fuente: Literal["CV", "CAT", "CAN"] | None = None):
    result = search_entities(q=q, municipio=municipio, provincia=provincia,
                             ambito=ambito, fuente=fuente, bbox=parse_bbox(bbox),
                             limit=10000)
    features = []
    for item in result["items"]:
        if item["longitud"] is None or item["latitud"] is None:
            continue
        features.append({"type": "Feature", "id": item["id_entidad"],
                         "geometry": {"type": "Point", "coordinates": [item["longitud"], item["latitud"]]},
                         "properties": {key: item[key] for key in
                                        ("id_entidad", "nombre", "fuente", "ambito", "direccion", "localidad", "provincia")}})
    return {"type": "FeatureCollection", "features": features, "total_con_coordenadas": len(features)}


@app.get("/api/stats", tags=["Sistema"], summary="Estadísticas del almacén")
def stats():
    return statistics()


@app.get("/api/metadata", tags=["Búsqueda"], summary="Opciones disponibles de filtros")
def metadata():
    return filters_metadata()


@app.get("/api/loads", tags=["Carga"], summary="Historial de ejecuciones")
def loads(limit: int = Query(20, ge=1, le=100)):
    return {"items": loads_history(limit=limit)}


@app.get("/api/loads/{load_id}/issues", tags=["Carga"], summary="Incidencias y reparaciones de una carga")
def issues(load_id: int, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    data = load_issues(load_id, limit=limit, offset=offset)
    if data is None:
        raise HTTPException(status_code=404, detail="Carga no encontrada")
    return data


@app.get("/api/loads/{load_id}/issues.csv", tags=["Carga"], summary="Descargar todas las incidencias y reparaciones en CSV")
def issues_csv(load_id: int):
    import csv
    import io
    first = load_issues(load_id, limit=500)
    if first is None:
        raise HTTPException(status_code=404, detail="Carga no encontrada")
    rows = first["items"]
    offset = len(rows)
    while offset < first["total"]:
        next_rows = load_issues(load_id, limit=500, offset=offset)["items"]
        if not next_rows:
            break
        rows.extend(next_rows)
        offset += len(next_rows)
    stream = io.StringIO()
    writer = csv.writer(stream)
    keys = ("fuente", "fila", "entidad_id", "campo", "codigo", "gravedad", "descripcion", "original", "reparado")
    writer.writerow(keys)
    for row in rows:
        # Evitar evaluación de fórmulas al abrir en una hoja de cálculo.
        values = []
        for key in keys:
            value = row[key]
            if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
                value = "'" + value
            values.append(value)
        writer.writerow(values)
    return Response("\ufeff" + stream.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="incidencias_carga_{load_id}.csv"'})


@app.post("/api/coordinates/convert", tags=["Geografía"], summary="Transformar UTM ETRS89/30N a longitud y latitud WGS84")
def coordinates(req: ConvertRequest):
    try:
        longitude, latitude = convert_utm(req.x_25830, req.y_25830)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"source_crs": "EPSG:25830", "target_crs": "EPSG:4326", "longitud": longitude, "latitud": latitude}
