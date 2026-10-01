#!/usr/bin/env python3
"""Clase 10 · Ej. 9 (OBLIGATORIO): descargador paralelo con un pool de threads HECHO A MANO.

    python3 descargador.py                        # URLs de ejemplo (necesita internet)
    python3 descargador.py --workers 8 url1 url2 ...
    python3 descargador.py --demo-local           # sin internet: levanta un servidor local lento

Estructura (lo mismo que hay dentro de ThreadPoolExecutor):
    main ──put(url)──► [Queue de tareas] ──get()──► worker 1..N ──► resultados (lista + Lock)
                       + N centinelas None para que cada worker sepa que tiene que terminar
"""
import argparse
import http.server
import queue
import statistics
import threading
import time
import urllib.error
import urllib.request

URLS_EJEMPLO = [
    "https://www.python.org", "https://docs.python.org", "https://pypi.org",
    "https://www.google.com", "https://github.com", "https://www.um.edu.ar",
    "https://httpbin.org/delay/1", "https://dominio-que-no-existe.invalid",
]


def descargar(url, timeout):
    inicio = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:   # I/O: acá el GIL se LIBERA
            datos = r.read()
        return {"url": url, "ok": True, "bytes": len(datos), "tiempo": time.perf_counter() - inicio}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        motivo = getattr(e, "reason", e)
        return {"url": url, "ok": False, "error": str(motivo), "tiempo": time.perf_counter() - inicio}


def worker(tareas, resultados, lock, timeout):
    while True:
        url = tareas.get()
        try:
            if url is None:                  # centinela → terminar
                return
            r = descargar(url, timeout)
            with lock:                       # list.append es seguro en CPython, pero el lock
                resultados.append(r)         # deja explícito que la lista es COMPARTIDA
            estado = f"{r['bytes']:>8,} B" if r["ok"] else f"ERROR {r['error'][:40]}"
            print(f"[{threading.current_thread().name}] {r['tiempo']:5.2f}s {estado}  {url}")
        finally:
            tareas.task_done()               # para que tareas.join() sepa cuándo termina todo


def descargar_todo(urls, n_workers, timeout):
    tareas, resultados, lock = queue.Queue(), [], threading.Lock()
    hilos = [threading.Thread(target=worker, args=(tareas, resultados, lock, timeout), name=f"w{i}")
             for i in range(n_workers)]          # POOL FIJO: N hilos, no uno por URL
    for h in hilos:
        h.start()
    for u in urls:
        tareas.put(u)
    for _ in hilos:
        tareas.put(None)                          # un centinela por worker
    for h in hilos:
        h.join()
    return resultados


def servidor_local_lento():
    """Servidor HTTP en un thread: cada respuesta tarda 0.5 s (simula red lenta)."""
    class Lento(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            time.sleep(0.5)
            cuerpo = b"x" * 10_000
            self.send_response(404 if "roto" in self.path else 200)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def log_message(self, *args):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Lento)   # puerto 0 = elegí uno libre
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    return [f"{base}/archivo{i}" for i in range(10)] + [f"{base}/roto"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--timeout", type=float, default=10)
    ap.add_argument("--demo-local", action="store_true")
    a = ap.parse_args()
    urls = servidor_local_lento() if a.demo_local else (a.urls or URLS_EJEMPLO)

    print(f"=== {len(urls)} URLs con 1 worker (secuencial) ===")
    t0 = time.perf_counter()
    descargar_todo(urls, 1, a.timeout)
    t_seq = time.perf_counter() - t0

    print(f"\n=== {len(urls)} URLs con {a.workers} workers ===")
    t0 = time.perf_counter()
    res = descargar_todo(urls, a.workers, a.timeout)
    t_par = time.perf_counter() - t0

    ok = [r for r in res if r["ok"]]
    tiempos = [r["tiempo"] for r in res]
    print("\n=== Estadísticas ===")
    print(f"Exitosas: {len(ok)}/{len(res)}   Bytes: {sum(r['bytes'] for r in ok):,}")
    for r in res:
        if not r["ok"]:
            print(f"  ✗ {r['url']}: {r['error']}")
    print(f"Tiempo por URL: min {min(tiempos):.2f}s · prom {statistics.mean(tiempos):.2f}s · max {max(tiempos):.2f}s")
    print(f"Total: secuencial {t_seq:.2f}s vs {a.workers} workers {t_par:.2f}s → speedup {t_seq / t_par:.1f}x")


if __name__ == "__main__":
    main()
