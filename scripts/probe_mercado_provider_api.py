import json
import requests

BASE = "https://servicios-prd.mercadopublico.cl"
HEADERS = {
    "User-Agent": "Mozilla/5.0 OSINTChileGraph/0.1 (+passive public-source probe)",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://proveedor.mercadopublico.cl",
    "Referer": "https://proveedor.mercadopublico.cl/busqueda",
}

cases = [
    ("rut_sin_dv", f"{BASE}/v1/proveedor/rut", {"rut": "76960560"}),
    ("rut_con_dv", f"{BASE}/v1/proveedor/rut", {"rut": "76960560-4"}),
    ("nombre", f"{BASE}/v1/proveedor/nombre", {"nombre": "BANCO"}),
    ("ultimo_folio", f"{BASE}/v1/habilidad-proveedor/ultimo-folio", {}),
]

for name, url, params in cases:
    print("\nCASE", name)
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=20)
        print("url", response.url)
        print("status", response.status_code, "type", response.headers.get("content-type"), "len", len(response.text))
        print(response.text[:1200])
    except Exception as exc:
        print("error", type(exc).__name__, exc)
