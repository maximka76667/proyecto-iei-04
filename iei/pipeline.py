"""Pipeline de la Entrega 1: wrappers HTTP -> extractor -> mapping -> almacén.

Lo usan la demo (demo_entrega-1.py) y los tests (tests/test_samples.py), de
modo que los tests comprueban exactamente lo que ejecuta la demo.

    with wrappers(["CV"], data_dir) as running:
        result = extract_and_load("CV", running["CV"].url, db)

o, en una sola llamada:

    results = run(data_dir, ["CV", "CAT", "CAN"], db)
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import httpx

from .database import process_source
from .extractor import extract_http, extract_read_errors_http
from .sources import FILENAMES

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORTS = {"CAN": 8101, "CAT": 8102, "CV": 8103}


@dataclass
class RunningWrapper:
    source: str
    url: str
    records: int  # registros que el wrapper dice tener (/health)


@dataclass
class LoadResult:
    source: str
    received: int      # registros recibidos del wrapper
    read_errors: int   # filas ilegibles informadas por el wrapper
    totals: dict       # resumen de process_source (incluye carga_id)


def missing_files(data_dir: Path, sources: list[str]) -> list[str]:
    return [FILENAMES[s] for s in sources if not (Path(data_dir) / FILENAMES[s]).is_file()]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start(source: str, port: int, data_dir: Path) -> subprocess.Popen:
    env = os.environ.copy()
    env["IEI_WRAPPER_SOURCE"] = source
    env["IEI_SOURCE_DIR"] = str(data_dir)
    command = [sys.executable, "-m", "uvicorn", "iei.wrapper:app",
               "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"]
    return subprocess.Popen(command, cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)


def _wait_healthy(source: str, url: str, proc: subprocess.Popen, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            err = proc.stderr.read() if proc.stderr else ""
            raise RuntimeError(f"El wrapper {source} terminó al arrancar ({url}; ¿puerto ocupado?)\n{err}")
        try:
            response = httpx.get(url + "/health", timeout=2.0)
            if response.status_code == 200:
                return response.json()
            if response.status_code >= 500:
                raise RuntimeError(f"El wrapper {source} no puede leer su fuente: {response.text}")
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"El wrapper {source} no respondió en {timeout:.0f} s")


def _stop(processes) -> None:
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
    for proc in processes:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@contextmanager
def wrappers(sources: list[str], data_dir: Path, ports: dict[str, int] | None = None,
             timeout: float = 20.0) -> Iterator[dict[str, RunningWrapper]]:
    """Arranca un wrapper HTTP por fuente sobre `data_dir` y los detiene al salir.

    Sin `ports`, usa puertos libres elegidos por el sistema (útil en tests).
    """
    data_dir = Path(data_dir).resolve()
    missing = missing_files(data_dir, sources)
    if missing:
        raise FileNotFoundError(f"Faltan en {data_dir}: {', '.join(missing)}")
    ports = ports or {s: free_port() for s in sources}
    processes: dict[str, subprocess.Popen] = {}
    try:
        for source in sources:
            processes[source] = _start(source, ports[source], data_dir)
        running = {}
        for source in sources:
            url = f"http://127.0.0.1:{ports[source]}"
            health = _wait_healthy(source, url, processes[source], timeout)
            running[source] = RunningWrapper(source, url, health.get("records", 0))
        yield running
    finally:
        _stop(processes.values())


def extract_and_load(source: str, wrapper_url: str, db_path: Path) -> LoadResult:
    """Extrae del wrapper por HTTP, aplica los mappings y carga en el almacén."""
    rows = extract_http(source, wrapper_url)
    read_errors = extract_read_errors_http(source, wrapper_url)
    totals = process_source(source, rows, db_path, read_errors=read_errors)
    return LoadResult(source, len(rows), len(read_errors), totals)


def run(data_dir: Path, sources: list[str], db_path: Path,
        ports: dict[str, int] | None = None) -> dict[str, LoadResult]:
    """Pipeline completo en una llamada: arranca wrappers, carga cada fuente y los detiene."""
    with wrappers(sources, data_dir, ports) as running:
        return {s: extract_and_load(s, running[s].url, db_path) for s in sources}
