"""Demo de la Entrega 1: wrapper -> extractor (HTTP) -> mapping -> almacén -> informe.

Uso:
  python demo_entrega-1.py                    # CV, CAT y CAN, base de datos nueva
  python demo_entrega-1.py --sources CV
  python demo_entrega-1.py --data-dir data/samples   # otra carpeta con cv.csv, cat.xml, can.json
  python demo_entrega-1.py --keep-db          # recarga sobre la BD existente (idempotencia)
  python demo_entrega-1.py --no-color         # sin colores (p. ej. al guardar en un fichero)

Arranca un wrapper HTTP por fuente, extrae los registros llamando a su API
(nunca lee el fichero directamente), aplica los mappings semánticos, carga en
el almacén e imprime el informe de registros cargados, reparados y rechazados.
Al terminar detiene los wrappers.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

import httpx

from iei import pipeline
from iei.database import connect

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "data" / "demo_entrega-1.sqlite3"
PORTS = pipeline.DEFAULT_PORTS
SOURCE_NAMES = {"CV": "Comunitat Valenciana (CSV)", "CAT": "Catalunya (XML)", "CAN": "Canarias (JSON)"}
# Códigos de incidencia que implican rechazar el registro entero.
REJECT_CODES = {"id_obligatorio", "nombre_obligatorio", "duplicado_lote", "fila_ilegible"}
EXAMPLES_PER_TYPE = 3


# ---------------------------------------------------------------- colores ---

class Style:
    enabled = False
    RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
    RED, GREEN, YELLOW, BLUE, CYAN = "\033[31m", "\033[32m", "\033[33m", "\033[34m", "\033[36m"


def setup_output(no_color: bool) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    Style.enabled = not no_color and not os.environ.get("NO_COLOR") and sys.stdout.isatty()
    if Style.enabled and os.name == "nt":
        os.system("")  # activa las secuencias de color ANSI en la consola de Windows


def paint(text, *styles: str) -> str:
    text = str(text)
    return "".join(styles) + text + Style.RESET if Style.enabled else text


def header(text: str) -> None:
    line = "━" * 64
    print("\n" + paint(line, Style.BLUE))
    print(paint("  " + text, Style.BOLD, Style.BLUE))
    print(paint(line, Style.BLUE))


def step(text: str) -> None:
    print("\n" + paint("▶ " + text, Style.BOLD))


def ok(text: str) -> None:
    print("  " + paint("✓", Style.GREEN) + " " + text)


def pct(part: int, total: int) -> str:
    return f"{100 * part / total:5.1f} %" if total else "    - "


# -------------------------------------------------------------- informe ---

def classify_records(conn: sqlite3.Connection, load_id: int, totals: dict) -> dict:
    """Qué le pasó a cada registro: limpio, reparado, con datos eliminados o rechazado.

    Cada registro cuenta una sola vez, en la categoría más grave que le afecte.
    """
    by_row: dict[int, set[str]] = {}
    for row in conn.execute("SELECT fila, codigo, gravedad FROM incidencias "
                            "WHERE carga_id=? AND codigo != 'fila_ilegible'", (load_id,)):
        kind = ("rechazado" if row["codigo"] in REJECT_CODES
                else "dato_invalido" if row["gravedad"] == "error"
                else "aviso" if row["gravedad"] == "advertencia"
                else "reparado")
        by_row.setdefault(row["fila"], set()).add(kind)
    counts = {"dato_invalido": 0, "aviso": 0, "reparado": 0}
    for kinds in by_row.values():
        if "rechazado" in kinds:
            continue
        for kind in ("dato_invalido", "aviso", "reparado"):
            if kind in kinds:
                counts[kind] += 1
                break
    loaded = totals["insertados"] + totals["actualizados"] + totals["sin_cambios"]
    counts["limpio"] = loaded - sum(counts.values())
    counts["cargados"] = loaded
    counts["rechazado"] = totals["descartados"]
    return counts


def print_record_summary(counts: dict, totals: dict) -> None:
    total = totals["leidos"]
    print(f"\n  {paint('¿Qué ha pasado con los registros?', Style.BOLD)}  ({total} leídos)\n")
    rows = [
        ("✓", Style.GREEN, "Cargados sin ningún problema", counts["limpio"]),
        ("✓", Style.CYAN, "Cargados tras repararlos automáticamente", counts["reparado"]),
        ("!", Style.YELLOW, "Cargados, con algún dato inválido eliminado", counts["dato_invalido"]),
        ("?", Style.YELLOW, "Cargados, con avisos para revisar", counts["aviso"]),
        ("✗", Style.RED, "Rechazados (no se han cargado)", counts["rechazado"]),
    ]
    for symbol, color, label, n in rows:
        style = (color,) if n else (Style.DIM,)
        print(f"    {paint(symbol, *style)}  {label:<46} {paint(f'{n:>5}', *style)}  "
              f"{paint(pct(n, total), Style.DIM)}")
    if totals["insertados"] or totals["actualizados"] or totals["sin_cambios"]:
        print(paint(f"\n    En el almacén: {totals['insertados']} nuevos, {totals['actualizados']} actualizados, "
                    f"{totals['sin_cambios']} sin cambios respecto a la carga anterior", Style.DIM))


def print_issue_details(conn: sqlite3.Connection, load_id: int) -> None:
    sections = [
        ("✗", Style.RED, "Registros rechazados",
         "codigo IN ({})".format(",".join("?" * len(REJECT_CODES))), tuple(REJECT_CODES)),
        ("!", Style.YELLOW, "Datos inválidos (el campo queda vacío, el registro sí se carga)",
         "gravedad='error' AND codigo NOT IN ({})".format(",".join("?" * len(REJECT_CODES))), tuple(REJECT_CODES)),
        ("✓", Style.CYAN, "Reparaciones automáticas", "gravedad='reparacion'", ()),
        ("?", Style.YELLOW, "Avisos (se carga el dato, pero conviene revisarlo)", "gravedad='advertencia'", ()),
    ]
    printed_any = False
    for symbol, color, title, condition, params in sections:
        types = conn.execute(
            f"SELECT codigo, descripcion, COUNT(*) AS n FROM incidencias "
            f"WHERE carga_id=? AND {condition} GROUP BY codigo ORDER BY n DESC",
            (load_id, *params)).fetchall()
        if not types:
            continue
        printed_any = True
        print(f"\n  {paint(symbol + ' ' + title, Style.BOLD, color)}")
        for t in types:
            print(f"    {paint(f'{t['n']:>5}', Style.BOLD)} ×{t['descripcion']}  {paint('[' + t['codigo'] + ']', Style.DIM)}")
            examples = conn.execute(
                "SELECT fila, entidad_id, campo, original, reparado FROM incidencias "
                "WHERE carga_id=? AND codigo=? ORDER BY fila LIMIT ?",
                (load_id, t["codigo"], EXAMPLES_PER_TYPE)).fetchall()
            for ex in examples:
                where = f"fila {ex['fila']}"
                if ex["entidad_id"]:
                    where += f", id {ex['entidad_id']}"
                value = ""
                if ex["original"] is not None:
                    value = f"«{ex['original']}»"
                if ex["reparado"] is not None:
                    value += " → " + paint(f"«{ex['reparado']}»", Style.GREEN)
                print(paint(f"          {where} · {ex['campo']}: ", Style.DIM) + value)
            if t["n"] > EXAMPLES_PER_TYPE:
                print(paint(f"          … y {t['n'] - EXAMPLES_PER_TYPE} más", Style.DIM))
    if not printed_any:
        ok("Ninguna incidencia.")


def print_sample(conn: sqlite3.Connection, source: str, n: int) -> None:
    rows = conn.execute(
        "SELECT e.id_entidad, e.id_origen, e.nombre, e.ambito, e.direccion, e.codigo_postal, "
        "e.latitud, e.longitud, e.descripcion, e.contacto, e.url, "
        "l.nombre AS localidad, p.nombre AS provincia "
        "FROM entidades e LEFT JOIN localidades l ON e.localidad_id=l.id "
        "LEFT JOIN provincias p ON l.provincia_id=p.id "
        "WHERE e.fuente=? ORDER BY e.id_entidad LIMIT ?", (source, n)).fetchall()
    if not rows:
        return
    print(f"\n  {paint(f'Ejemplo de cómo han quedado {len(rows)} registros en el almacén', Style.BOLD)}")
    for row in rows:
        print()
        for key in row.keys():
            value = row[key]
            shown = paint("(vacío)", Style.DIM) if value is None else value
            print(f"    {paint(f'{key:<14}', Style.DIM)} {shown}")


def print_final_table(results: list[tuple[str, dict]]) -> None:
    header("Resumen de todas las fuentes")
    head = f"  {'Fuente':<8}{'Leídos':>8}{'Cargados':>10}{'Reparados':>11}{'Con avisos':>12}{'Rechazados':>12}"
    print(paint(head, Style.BOLD))
    sums = [0, 0, 0, 0, 0]
    for source, c in results:
        values = [c["leidos"], c["cargados"], c["reparado"], c["dato_invalido"] + c["aviso"], c["rechazado"]]
        sums = [a + b for a, b in zip(sums, values)]
        print(f"  {source:<8}{values[0]:>8}{paint(f'{values[1]:>10}', Style.GREEN)}"
              f"{paint(f'{values[2]:>11}', Style.CYAN)}{paint(f'{values[3]:>12}', Style.YELLOW)}"
              f"{paint(f'{values[4]:>12}', Style.RED if values[4] else Style.DIM)}")
    if len(results) > 1:
        print(paint(f"  {'TOTAL':<8}{sums[0]:>8}{sums[1]:>10}{sums[2]:>11}{sums[3]:>12}{sums[4]:>12}", Style.BOLD))


# ----------------------------------------------------------------- main ---

def main() -> int:
    parser = argparse.ArgumentParser(description="Demo de la Entrega 1 (ETL hasta el almacén).")
    parser.add_argument("--sources", nargs="+", choices=list(PORTS), default=["CV", "CAT", "CAN"],
                        help="Fuentes a cargar (por defecto: CV CAT CAN)")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "sources",
                        help="Carpeta con cv.csv, cat.xml y can.json (por defecto data/sources)")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help=f"Base de datos (por defecto {DEFAULT_DB.name})")
    parser.add_argument("--keep-db", action="store_true",
                        help="No borrar la BD antes de cargar (para mostrar que recargar no duplica)")
    parser.add_argument("--sample", type=int, default=2, help="Registros de ejemplo a mostrar por fuente")
    parser.add_argument("--no-color", action="store_true", help="Desactivar colores")
    args = parser.parse_args()
    setup_output(args.no_color)
    sources = list(dict.fromkeys(args.sources))

    data_dir = args.data_dir.resolve()
    missing = pipeline.missing_files(data_dir, sources)
    if missing:
        print(paint(f"ERROR: faltan en {data_dir}: {', '.join(missing)}", Style.BOLD, Style.RED), file=sys.stderr)
        return 1

    header("Demo Entrega 1 · Extracción, transformación y carga")
    try:
        shown_dir = data_dir.relative_to(ROOT)
    except ValueError:
        shown_dir = data_dir
    print(f"  Datos:   {shown_dir}")
    if args.keep_db:
        print(f"  Almacén: {args.db.name} (se conserva lo cargado antes)")
    else:
        if args.db.exists():
            args.db.unlink()
        print(f"  Almacén: {args.db.name} (vacío, se crea de nuevo)")

    results: list[tuple[str, dict]] = []
    try:
        step("Arrancando los wrappers (un servicio HTTP por fuente)")
        with pipeline.wrappers(sources, data_dir, ports=PORTS) as running:
            for source in sources:
                ok(f"{source:<4} {running[source].url}  · {running[source].records} registros")

            for source in sources:
                header(f"{source} · {SOURCE_NAMES[source]}")
                step("Extracción por HTTP desde el wrapper, transformación (mappings) y carga en el almacén")
                result = pipeline.extract_and_load(source, running[source].url, args.db)
                ok(f"{result.received} registros recibidos del wrapper")
                if result.read_errors:
                    print("  " + paint("✗", Style.RED) + f" {result.read_errors} filas ilegibles en el fichero")

                totals = result.totals
                conn = connect(args.db)
                try:
                    counts = classify_records(conn, totals["carga_id"], totals)
                    counts["leidos"] = totals["leidos"]
                    print_record_summary(counts, totals)
                    print_issue_details(conn, totals["carga_id"])
                    if args.sample > 0:
                        print_sample(conn, source, args.sample)
                finally:
                    conn.close()
                results.append((source, counts))

        print_final_table(results)
    except (RuntimeError, httpx.HTTPError, ValueError, OSError) as exc:
        print("\n" + paint(f"ERROR: {exc}", Style.BOLD, Style.RED), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrumpido.")
        return 130
    print("\n" + paint("Wrappers detenidos. Fin de la demo.", Style.DIM) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
