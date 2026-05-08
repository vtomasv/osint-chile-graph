import json
import requests

BASE = "https://api.mercadopublico.cl/servicios/v1/Publico/Empresas/BuscarProveedor"
TICKETS = [
    "F8537A18-6766-4DEF-9E59-426B4FEE2844",
]
RUTS = ["76960560-4", "22091655-3", "60805000-0"]
for ticket in TICKETS:
    print("TICKET", ticket)
    for rut in RUTS:
        try:
            resp = requests.get(BASE, params={"rutempresaproveedor": rut, "ticket": ticket}, timeout=20)
            print("RUT", rut, "status", resp.status_code, "type", resp.headers.get("content-type"), "len", len(resp.text))
            print(resp.text[:1200])
        except Exception as exc:
            print("ERROR", rut, type(exc).__name__, exc)
