import requests

urls = [
    "https://www2.sii.cl/stc/noauthz",
    "https://zeus.sii.cl/cvc/stc/stc.html",
    "https://zeus.sii.cl/cvc_cgi/stc/getstc?RUT=60803000&DV=K",
    "https://zeus.sii.cl/cvc_cgi/stc/getstc?RUT=60803000&PRG=STC&OPC=CON&ACEPTAR=Efectuar+Consulta",
    "https://www.diariooficial.interior.gob.cl/",
    "https://www.diariooficial.interior.gob.cl/sociedades-web/",
]

headers = {"User-Agent": "Mozilla/5.0 OSINT-Chile-Graph evidence connector; operator-controlled research"}
for url in urls:
    print("\nURL", url)
    try:
        response = requests.get(url, timeout=20, headers=headers)
        print("status", response.status_code, "final", response.url, "len", len(response.text), "ct", response.headers.get("content-type"))
        print(response.text[:700].replace("\n", " ")[:700])
    except Exception as exc:
        print("ERR", type(exc).__name__, exc)
