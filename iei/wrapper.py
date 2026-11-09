"""Servicio HTTP de lectura de fuentes heterogéneas.

Ejecutar uno por fuente: IEI_WRAPPER_SOURCE=CAN uvicorn iei.wrapper:app --port 8101
"""
from __future__ import annotations

import os
from fastapi import FastAPI, HTTPException, Query
from .sources import FILENAMES, load_source

app = FastAPI(title="IEI – Wrapper de fuente", version="2.0", description="Expone registros originales sin transformación semántica.")


def current_source() -> str:
    value = os.getenv("IEI_WRAPPER_SOURCE", "CV").strip().upper()
    if value not in FILENAMES:
        raise HTTPException(status_code=500, detail="IEI_WRAPPER_SOURCE inválida")
    return value


@app.get("/health", tags=["Sistema"])
def health():
    source = current_source()
    try:
        count = len(load_source(source))
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ok", "source": source, "records": count}


@app.get("/schema", tags=["Fuente"])
def schema():
    source = current_source()
    try:
        records = load_source(source)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"source": source, "count": len(records), "fields": list(records[0]) if records else []}


@app.get("/records", tags=["Fuente"])
def records(page: int = Query(1, ge=1), page_size: int = Query(250, ge=1, le=500)):
    source = current_source()
    try:
        rows = load_source(source)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    start = (page - 1) * page_size
    return {"source": source, "page": page, "page_size": page_size, "total": len(rows),
            "records": rows[start:start + page_size]}
