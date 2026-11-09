"""Extractores: obtienen los registros de cada fuente a través de su wrapper HTTP.

No leen nunca el fichero original; solo hablan con la API del wrapper.
"""
from __future__ import annotations

import os

import httpx

DEFAULT_WRAPPERS = {"CAN": "http://127.0.0.1:8101", "CAT": "http://127.0.0.1:8102", "CV": "http://127.0.0.1:8103"}


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


def extract_read_errors_http(source: str) -> list[dict]:
    """Filas que el wrapper no pudo leer (p. ej. número de columnas incorrecto)."""
    with httpx.Client(timeout=30.0, follow_redirects=False) as client:
        response = client.get(wrapper_url(source) + "/read-errors")
        response.raise_for_status()
        data = response.json()
    if data.get("source") != source or not isinstance(data.get("errors"), list):
        raise ValueError("El wrapper respondió con fuente o formato inesperado")
    return data["errors"]
