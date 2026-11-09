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


def _read_cv(file: Path) -> tuple[tuple[dict, ...], tuple[dict, ...]]:
    """Lee el CSV sin descartar filas en silencio.

    Las filas con un número de columnas distinto al de la cabecera no se
    devuelven como registros: se informan como errores de lectura con su línea.
    """
    with file.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        try:
            header = [name.strip() for name in next(reader)]
        except StopIteration:
            raise ValueError("CV: fichero vacío, sin cabecera") from None
        records, errors = [], []
        while True:
            try:
                row = next(reader)
            except StopIteration:
                break
            except csv.Error as exc:
                errors.append({"line": reader.line_num, "reason": f"CSV ilegible: {exc}", "raw": None})
                continue
            if not any(cell.strip() for cell in row):
                continue  # línea en blanco
            if len(row) != len(header):
                errors.append({"line": reader.line_num,
                               "reason": f"Se esperaban {len(header)} columnas y hay {len(row)}",
                               "raw": ",".join(row)})
                continue
            records.append(dict(zip(header, row)))
    return tuple(records), tuple(errors)


@lru_cache(maxsize=16)
def _load_cached(source: str, path: str, mtime_ns: int, size: int) -> tuple[tuple[dict, ...], tuple[dict, ...]]:
    """Devuelve (registros, errores_de_lectura)."""
    file = Path(path)
    if source == "CV":
        return _read_cv(file)
    if source == "CAN":
        with file.open("r", encoding="utf-8-sig") as stream:
            content = json.load(stream)
        if not isinstance(content, list):
            raise ValueError("CAN: se esperaba una lista JSON de entidades")
        if not all(isinstance(row, dict) for row in content):
            raise ValueError("CAN: hay entidades JSON que no son objetos")
        return tuple(content), ()
    if source == "CAT":
        root = ET.parse(file).getroot()
        if root.tag != "registre_ongd":
            raise ValueError(f"CAT: elemento raíz inesperado: {root.tag}")
        return tuple({node.tag: node.text for node in child} for child in root if child.tag == "entitat"), ()
    raise ValueError(source)


def _load(source: str):
    file = source_path(source)
    st = file.stat()
    return _load_cached(source, str(file.resolve()), st.st_mtime_ns, st.st_size)


def load_source(source: str) -> tuple[dict, ...]:
    """Registros leídos correctamente, con los nombres de campo originales."""
    return _load(source)[0]


def load_read_errors(source: str) -> tuple[dict, ...]:
    """Filas que no se pudieron leer: línea del fichero, motivo y contenido."""
    return _load(source)[1]
