#!/usr/bin/env python3
"""Corre las pruebas del ejercicio 3 contra api.py SIN levantar servidor (TestClient de FastAPI)."""
from fastapi.testclient import TestClient

import api

c = TestClient(api.app)


def ver(nombre, r):
    cuerpo = r.json() if r.content else ""
    if isinstance(cuerpo, dict) and "detail" in cuerpo and isinstance(cuerpo["detail"], list):
        d = cuerpo["detail"][0]
        cuerpo = f"{d['type']} en {d['loc']}: {d['msg']}"
    print(f"{nombre:<46} → {r.status_code}  {cuerpo}   (X-Tiempo {r.headers.get('x-tiempo')})")


print("── Parte B: los 4 errores ──")
ver("GET /tareas/abc", c.get("/tareas/abc"))
ver('POST {"tipo":"volar"}', c.post("/tareas", json={"tipo": "volar"}))
ver('POST {"tipo":"esperar","prioridad":99}', c.post("/tareas", json={"tipo": "esperar", "prioridad": 99}))
ver("GET /tareas/999", c.get("/tareas/999"))

print("\n── Parte C ──")
r = c.post("/tareas", json={"tipo": "descargar", "prioridad": 3})
ver("POST válido", r)
print(f"{'':46}   Location: {r.headers.get('location')}")
ver("PATCH /tareas/1 {estado: ejecutando}", c.patch("/tareas/1", json={"estado": "ejecutando"}))
ver("PATCH /tareas/1 {estado: volando}", c.patch("/tareas/1", json={"estado": "volando"}))
ver("PATCH /tareas/1 {}", c.patch("/tareas/1", json={}))
for _ in range(10):
    c.post("/tareas", json={"tipo": "esperar"})
r = c.post("/tareas", json={"tipo": "esperar"})
ver("POST con 10 pendientes", r)
print(f"{'':46}   Retry-After: {r.headers.get('retry-after')}")
ver("GET /estadisticas", c.get("/estadisticas"))
ver("DELETE /tareas/1", c.delete("/tareas/1"))
