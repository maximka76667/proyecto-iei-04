"""Arranque en un paso: levanta los wrappers y el integrador, y carga datasets.

Uso: python run_demo.py
Omitir carga inicial: python run_demo.py --no-load
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent


def read_json(url, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"} if data else {})
    with urlopen(request, timeout=50) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-load", action="store_true", help="No realizar carga inicial")
    parser.add_argument("--port", type=int, default=8000, help="Puerto de aplicación (por defecto 8000)")
    args = parser.parse_args()
    processes = []
    def stop_signal(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop_signal)
    services = [("CAN", 8101), ("CAT", 8102), ("CV", 8103), ("API", args.port)]
    try:
        for name, port in services:
            env = os.environ.copy()
            if name != "API":
                env["IEI_WRAPPER_SOURCE"] = name
                module = "iei.wrapper:app"
            else:
                module = "iei.api:app"
            command = [sys.executable, "-m", "uvicorn", module, "--host", "127.0.0.1", "--port", str(port)]
            proc = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            processes.append(proc)
        for name, port in services:
            for attempt in range(100):
                if any(p.poll() is not None for p in processes):
                    raise RuntimeError("Un servidor terminó inesperadamente; comprueba puertos ocupados")
                try:
                    health = read_json(f"http://127.0.0.1:{port}/" + ("api/health" if name == "API" else "health"))
                    if health["status"] == "ok":
                        break
                except (URLError, TimeoutError, ValueError, ConnectionError):
                    time.sleep(0.15)
            else:
                raise RuntimeError(f"No arranca el servicio {name} ({port})")
        url = f"http://127.0.0.1:{args.port}"
        if not args.no_load:
            print("Cargando datos de CV, CAT y CAN vía HTTP (idempotente)...", flush=True)
            report = read_json(url + "/api/load", {"sources": ["CV", "CAT", "CAN"]})
            for item in report["results"]:
                if item["status"] == "ok":
                    print(f"  {item['source']}: +{item['insertados']} altas, "
                          f"{item['sin_cambios']} sin cambios, {item['incidencias']} incidencias")
                else:
                    print(f"  {item['source']}: ERROR {item['message']}")
        print(f"\nBuscador: {url}\nDocumentación API: {url}/docs\nCtrl+C para detener.\n", flush=True)
        while all(p.poll() is None for p in processes):
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
