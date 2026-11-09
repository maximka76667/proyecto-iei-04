"""Fuentes originales accesibles mediante servicios wrapper HTTP independientes.

Se seleccionan los archivos por su CONTENIDO, no por los nombres de carpeta del ZIP.
"""
from __future__ import annotations

import csv
import json
import os
from functools import lru_cache
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FILENAMES = {"CV": "cv.csv", "CAT": "cat.xml", "CAN": "can.json"}


def source_path(source: str) -> Path:
    if source not in FILENAMES:
        raise ValueError(f"Fuente desconocida: {source}")
    return Path(os.getenv("IEI_SOURCE_DIR", str(ROOT / "data" / "sources"))) / FILENAMES[source]


@lru_cache(maxsize=16)
def _load_cached(source: str, path: str, mtime_ns: int, size: int) -> tuple[dict, ...]:
    file = Path(path)
    if source == "CV":
        with file.open("r", encoding="utf-8-sig", newline="") as stream:
            return tuple(dict(item) for item in csv.DictReader(stream))
    if source == "CAN":
        with file.open("r", encoding="utf-8-sig") as stream:
            content = json.load(stream)
        if not isinstance(content, list):
            raise ValueError("CAN: se esperaba una lista JSON de entidades")
        if not all(isinstance(row, dict) for row in content):
            raise ValueError("CAN: hay entidades JSON que no son objetos")
        return tuple(content)
    if source == "CAT":
        root = ET.parse(file).getroot()
        if root.tag != "registre_ongd":
            raise ValueError(f"CAT: elemento raíz inesperado: {root.tag}")
        return tuple({node.tag: node.text for node in child} for child in root if child.tag == "entitat")
    raise ValueError(source)


def load_source(source: str) -> tuple[dict, ...]:
    file = source_path(source)
    st = file.stat()
    return _load_cached(source, str(file.resolve()), st.st_mtime_ns, st.st_size)
