"""Comprueba cada caso de data/samples/casos.json con el mismo pipeline que la demo.

Arranca los wrappers reales (en puertos libres), extrae por HTTP, transforma y
carga una vez por sesión; luego cada caso consulta el resultado.

Los casos con "pendiente" son comportamiento acordado aún no implementado: se
esperan fallidos (xfail estricto). Cuando se implementen, el test avisa
(XPASS) para quitar la marca "pendiente" de casos.json.
"""
import json
import sqlite3
from pathlib import Path

import pytest

from iei import pipeline

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"
MANIFEST = json.loads((SAMPLES / "casos.json").read_text(encoding="utf-8"))["fuentes"]
NOT_NULL = "*"


@pytest.fixture(scope="module")
def loaded(tmp_path_factory):
    db = tmp_path_factory.mktemp("samples") / "samples.sqlite3"
    results = pipeline.run(SAMPLES, list(MANIFEST), db)
    return db, {source: r.totals for source, r in results.items()}


def _codes(db, load_id, fila):
    with sqlite3.connect(db) as conn:
        return {r[0] for r in conn.execute(
            "SELECT codigo FROM incidencias WHERE carga_id=? AND fila=? AND codigo != 'fila_ilegible'",
            (load_id, fila))}


def _entity(db, fuente, id_origen):
    if not id_origen:
        return None
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM entidades WHERE fuente=? AND id_origen=?", (fuente, id_origen)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _params():
    for source, info in MANIFEST.items():
        for case in info["casos"]:
            marks = [pytest.mark.xfail(strict=True, reason=case["pendiente"])] if case.get("pendiente") else []
            yield pytest.param(source, case, id=f"{source}-{case['fila']}-{case['caso']}", marks=marks)


@pytest.mark.parametrize("source,case", list(_params()))
def test_case(loaded, source, case):
    db, totals = loaded
    codes = _codes(db, totals[source]["carga_id"], case["fila"])
    missing = set(case.get("esperado", [])) - codes
    assert not missing, f"faltan incidencias {sorted(missing)}; registradas: {sorted(codes)}"

    entity = _entity(db, source, case["id"])
    expected_loaded = case.get("cargado", True)
    if expected_loaded is not None:
        assert (entity is not None) == expected_loaded, \
            "no está en el almacén" if expected_loaded else "no debía cargarse"
    for field, expected in case.get("campos", {}).items():
        assert entity is not None, "la entidad no está en el almacén"
        if expected == NOT_NULL:
            assert entity[field] is not None, f"{field} vacío"
        else:
            assert entity[field] == expected, f"{field}: {entity[field]!r} != {expected!r}"


@pytest.mark.parametrize("source", list(MANIFEST))
def test_read_errors(loaded, source):
    db, totals = loaded
    with sqlite3.connect(db) as conn:
        lines = {r[0] for r in conn.execute(
            "SELECT fila FROM incidencias WHERE carga_id=? AND codigo='fila_ilegible'",
            (totals[source]["carga_id"],))}
    assert lines == {e["linea"] for e in MANIFEST[source]["errores_lectura"]}
