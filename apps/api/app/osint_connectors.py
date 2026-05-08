from __future__ import annotations

import html
import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests


USER_AGENT = "OSINT-Chile-Graph/0.3 (+responsible-public-osint; passive evidence collection)"
SEARCH_ENDPOINT = "https://html.duckduckgo.com/html/"
MERCADO_PUBLICO_SUPPLIER_ENDPOINT = "https://api.mercadopublico.cl/servicios/v1/Publico/Empresas/BuscarProveedor"
MERCADO_PUBLICO_PUBLIC_TICKET = "F8537A18-6766-4DEF-9E59-426B4FEE2844"
REQUEST_TIMEOUT = float(os.getenv("OSINT_CONNECTOR_TIMEOUT_SECONDS", "2.5"))
PUBLIC_WEB_SEARCH_ENABLED = os.getenv("OSINT_ENABLE_PUBLIC_WEB_SEARCH", "false").strip().lower() in {"1", "true", "yes", "on"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_search_url(query: str) -> str:
    return f"{SEARCH_ENDPOINT}?q={quote_plus(query)}"


def google_search_url(query: str) -> str:
    return "https://www.google.com/search?q=" + quote_plus(query)


def format_chilean_rut(value: str) -> str:
    cleaned = re.sub(r"[^0-9kK]", "", value).upper()
    if len(cleaned) < 2:
        return value.strip()
    body, dv = cleaned[:-1], cleaned[-1]
    try:
        dotted = f"{int(body):,}".replace(",", ".")
    except ValueError:
        dotted = body
    return f"{dotted}-{dv}"


def connector_status(source: str, status: str, query: str, message: str, url: str = "") -> dict[str, Any]:
    return {
        "source": source,
        "status": status,
        "query": query,
        "url": url or build_search_url(query),
        "message": message,
        "checked_at": utc_now_iso(),
    }


def _strip_tags(value: str) -> str:
    value = re.sub(r"<script[\s\S]*?</script>", " ", value, flags=re.I)
    value = re.sub(r"<style[\s\S]*?</style>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def _decode_ddg_url(url: str) -> str:
    clean = html.unescape(url)
    if clean.startswith("//"):
        clean = "https:" + clean
    parsed = urlparse(clean)
    params = parse_qs(parsed.query)
    if "uddg" in params and params["uddg"]:
        return unquote(params["uddg"][0])
    return clean


def _extract_results(document: str, max_results: int) -> list[dict[str, str]]:
    blocks = re.findall(r'<div[^>]+class="[^"]*result[^"]*"[\s\S]*?</div>\s*</div>', document, flags=re.I)
    if not blocks:
        blocks = re.findall(r'<a[^>]+class="[^"]*result__a[^"]*"[\s\S]*?</a>[\s\S]{0,900}', document, flags=re.I)

    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for block in blocks:
        anchor = re.search(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>([\s\S]*?)</a>', block, flags=re.I)
        if not anchor:
            continue
        url = _decode_ddg_url(anchor.group(1))
        title = _strip_tags(anchor.group(2))
        snippet_match = re.search(r'<a[^>]+class="[^"]*result__snippet[^"]*"[\s\S]*?</a>|<div[^>]+class="[^"]*result__snippet[^"]*"[\s\S]*?</div>', block, flags=re.I)
        snippet = _strip_tags(snippet_match.group(0)) if snippet_match else ""
        if not url or not title or url in seen:
            continue
        seen.add(url)
        results.append({"title": title, "url": url, "snippet": snippet})
        if len(results) >= max_results:
            break
    return results


def public_search(query: str, *, source: str, max_results: int = 4) -> dict[str, Any]:
    url = build_search_url(query)
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True, headers={"User-Agent": USER_AGENT})
        if response.status_code >= 400 or response.status_code == 202:
            return {
                "results": [],
                "status": connector_status(source, "blocked_or_unavailable", query, f"La fuente de búsqueda respondió HTTP {response.status_code}; no se registra como evidencia y debe continuarse por HITL o API configurada.", url),
            }
        challenge_markers = ("anomaly", "captcha", "vqd", "duckduckgo.com/duckduckgo-help-pages/results/syntax")
        if any(marker in response.text.lower() for marker in challenge_markers) and "result__a" not in response.text:
            return {
                "results": [],
                "status": connector_status(source, "blocked_or_unavailable", query, "La fuente de búsqueda devolvió una página de control o sin resultados HTML analizables; no se registra como evidencia.", url),
            }
        results = _extract_results(response.text, max_results)
        status = "verified_evidence" if results else "no_results"
        message = f"Se encontraron {len(results)} resultado(s) públicos indexados." if results else "La búsqueda pública respondió, pero no entregó resultados verificables. No se crea evidencia ni entidad útil."
        return {"results": results, "status": connector_status(source, status, query, message, url)}
    except requests.RequestException as exc:
        return {
            "results": [],
            "status": connector_status(source, "blocked_or_unavailable", query, f"No se pudo consultar la búsqueda pública: {exc.__class__.__name__}: {exc}", url),
        }


def evidence_from_search_result(*, connector: str, query: str, result: dict[str, str], rank: int, input_type: str, input_value: str) -> dict[str, Any]:
    title = result.get("title", "Resultado público")
    url = result.get("url", "")
    snippet = result.get("snippet", "")
    extract = f"Resultado público verificado por búsqueda pasiva: {title}."
    if snippet:
        extract += f" Extracto: {snippet}"
    return {
        "source_name": connector,
        "source_url": url,
        "extract": extract,
        "confidence": 0.72 if snippet else 0.62,
        "properties": {
            "evidence_kind": "verified_evidence",
            "connector": connector,
            "query": query,
            "rank": rank,
            "title": title,
            "snippet": snippet,
            "input_type": input_type,
            "input_value": input_value,
            "checked_at": utc_now_iso(),
        },
    }


def web_evidence_entity(evidence: dict[str, Any]) -> dict[str, Any]:
    props = evidence.get("properties", {})
    return {
        "type": "WebEvidence",
        "label": props.get("title") or evidence.get("source_url") or evidence.get("source_name"),
        "value": evidence.get("source_url") or props.get("title") or evidence.get("source_name"),
        "confidence": evidence.get("confidence", 0.7),
        "properties": {
            "evidence_kind": "verified_evidence",
            "source_name": evidence.get("source_name"),
            "source_url": evidence.get("source_url"),
            "extract": evidence.get("extract"),
            **props,
        },
    }


def mercado_publico_supplier_by_rut(value: str) -> dict[str, Any]:
    rut = format_chilean_rut(value)
    params = {"rutempresaproveedor": rut, "ticket": MERCADO_PUBLICO_PUBLIC_TICKET}
    api_url = f"{MERCADO_PUBLICO_SUPPLIER_ENDPOINT}?rutempresaproveedor={quote_plus(rut)}&ticket={quote_plus(MERCADO_PUBLICO_PUBLIC_TICKET)}"
    source = "Mercado Público API BuscarProveedor"
    try:
        response = requests.get(MERCADO_PUBLICO_SUPPLIER_ENDPOINT, params=params, timeout=REQUEST_TIMEOUT, allow_redirects=True, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text[:1000]}
        companies = payload.get("listaEmpresas") if isinstance(payload, dict) else []
        if response.status_code == 200 and companies:
            evidence = []
            entities = []
            names = []
            for index, item in enumerate(companies, start=1):
                name = str(item.get("NombreEmpresa") or "Proveedor Mercado Público").strip()
                code = str(item.get("CodigoEmpresa") or "").strip()
                names.append(name)
                ev = {
                    "source_name": source,
                    "source_url": "https://www.mercadopublico.cl/Home/BusquedaProveedor",
                    "extract": f"La API oficial de Mercado Público devolvió el proveedor {name} para el RUT {rut}. CódigoEmpresa={code or 'sin código expuesto'}.",
                    "confidence": 0.86,
                    "properties": {
                        "evidence_kind": "verified_evidence",
                        "connector": "mercado_publico_supplier_api",
                        "api_url": api_url,
                        "rut_query": rut,
                        "company_name": name,
                        "company_code": code,
                        "rank": index,
                        "raw_item": item,
                        "checked_at": utc_now_iso(),
                    },
                }
                evidence.append(ev)
                entities.append({
                    "type": "Company",
                    "label": name,
                    "value": code or name,
                    "confidence": 0.86,
                    "properties": {
                        "evidence_kind": "verified_evidence",
                        "source_name": source,
                        "source_url": "https://www.mercadopublico.cl/Home/BusquedaProveedor",
                        "rut_query": rut,
                        "company_code": code,
                        "extract": ev["extract"],
                    },
                })
                entities.append(web_evidence_entity(ev))
            return {
                "entities": entities,
                "evidence": evidence,
                "source_statuses": [connector_status(source, "verified_evidence", rut, f"Mercado Público devolvió {len(companies)} proveedor(es): {', '.join(names[:3])}.", "https://www.mercadopublico.cl/Home/BusquedaProveedor")],
            }
        message = payload.get("Mensaje") if isinstance(payload, dict) else response.text[:300]
        normalized_status = "no_results" if response.status_code in {200, 404, 500} and "No hay resultados" in str(message) else "blocked_or_unavailable"
        return {
            "entities": [],
            "evidence": [],
            "source_statuses": [connector_status(source, normalized_status, rut, f"Mercado Público respondió HTTP {response.status_code}: {message or 'sin resultados parseables'}.", "https://www.mercadopublico.cl/Home/BusquedaProveedor")],
        }
    except requests.RequestException as exc:
        return {
            "entities": [],
            "evidence": [],
            "source_statuses": [connector_status(source, "blocked_or_unavailable", rut, f"No se pudo consultar Mercado Público: {exc.__class__.__name__}: {exc}", "https://www.mercadopublico.cl/Home/BusquedaProveedor")],
        }


def public_web_evidence(input_type: str, value: str, queries: list[tuple[str, str]], max_results_per_query: int = 3) -> dict[str, Any]:
    evidence: list[dict[str, Any]] = []
    entities: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []

    if not PUBLIC_WEB_SEARCH_ENABLED:
        for connector, query in queries:
            statuses.append(connector_status(
                connector,
                "operator_required",
                query,
                "Búsqueda web automática desactivada: no hay API de búsqueda configurada para producir evidencia verificable de forma estable. Se crea continuidad HITL; no se registra el dork como hallazgo.",
                google_search_url(query),
            ))
        return {"entities": entities, "evidence": evidence, "source_statuses": statuses}

    for connector, query in queries:
        response = public_search(query, source=connector, max_results=max_results_per_query)
        statuses.append(response["status"])
        for rank, result in enumerate(response["results"], start=1):
            item = evidence_from_search_result(connector=connector, query=query, result=result, rank=rank, input_type=input_type, input_value=value)
            evidence.append(item)
            entities.append(web_evidence_entity(item))

    return {"entities": entities, "evidence": evidence, "source_statuses": statuses}


def source_status_evidence(status: dict[str, Any], input_type: str, input_value: str) -> dict[str, Any]:
    return {
        "source_name": f"source_status:{status.get('source', 'unknown')}",
        "source_url": status.get("url", ""),
        "extract": status.get("message", "Estado de fuente registrado."),
        "confidence": 0.25 if status.get("status") in {"blocked_or_unavailable", "operator_required"} else 0.45,
        "properties": {
            "evidence_kind": "source_status",
            "status": status.get("status"),
            "query": status.get("query"),
            "input_type": input_type,
            "input_value": input_value,
            "checked_at": status.get("checked_at") or utc_now_iso(),
        },
    }


def manual_source_task(source: str, value: str, purpose: str, url: str, *, reason: str | None = None) -> dict[str, Any]:
    return {
        "type": "HumanTask",
        "source": source,
        "value": value,
        "status": "pending_manual_review",
        "purpose": purpose,
        "reason": reason or "La fuente requiere interacción humana, CAPTCHA, sesión, aceptación de términos, pago, autorización específica o revisión legal antes de consultar.",
        "source_url": url,
        "search_url": url,
        "execution_policy": "operator_required",
        "instructions": "Abrir la fuente desde el navegador integrado, revisar términos aplicables, ejecutar la consulta sólo si existe autorización y guardar evidencia con URL, fecha, extracto textual, confianza y entidades observadas.",
        "expected_evidence": ["URL o nombre de fuente", "fecha/hora de consulta", "extracto textual", "entidades observadas", "captura o referencia documental si procede"],
    }


def rut_public_queries(value: str, compact: str, normalized: str) -> list[tuple[str, str]]:
    tokens = [token for token in dict.fromkeys([normalized, compact, value]) if token]
    exact = " OR ".join(f'"{token}"' for token in tokens)
    return [
        ("Public Web Search", f"({exact}) Chile"),
        ("Diario Oficial indexado", f"site:diariooficial.interior.gob.cl ({exact})"),
        ("Mercado Público indexado", f"site:mercadopublico.cl ({exact})"),
        ("Documentos públicos Chile", f"({exact}) filetype:pdf Chile"),
    ]


def phone_public_queries(value: str, normalized: str, national: str) -> list[tuple[str, str]]:
    local = normalized.replace("+56", "").strip()
    exact = " OR ".join(f'"{token}"' for token in dict.fromkeys([normalized, national, local, value]) if token)
    return [
        ("Public Web Search", f"({exact}) Chile"),
        ("Documentos públicos Chile", f"({exact}) filetype:pdf Chile"),
        ("Sitios chilenos indexados", f"site:.cl ({exact})"),
    ]


def plate_public_queries(value: str, normalized: str) -> list[tuple[str, str]]:
    hyphen = f"{normalized[:2]}-{normalized[2:4]}-{normalized[4:]}" if len(normalized) == 6 else normalized
    spaced = f"{normalized[:2]} {normalized[2:4]} {normalized[4:]}" if len(normalized) == 6 else normalized
    exact = " OR ".join(f'"{token}"' for token in dict.fromkeys([normalized, hyphen, spaced, value]) if token)
    return [
        ("Public Web Search", f"({exact}) Chile vehículo patente"),
        ("Documentos públicos Chile", f"({exact}) filetype:pdf Chile"),
        ("Avisos y publicaciones indexadas", f"({exact}) (vehículo OR patente OR remate OR multa) Chile"),
    ]


def generic_public_queries(input_type: str, value: str) -> list[tuple[str, str]]:
    exact = f'"{value}"'
    return [
        ("Public Web Search", f"{exact} Chile"),
        ("Documentos públicos Chile", f"{exact} filetype:pdf Chile"),
        ("Sitios chilenos indexados", f"site:.cl {exact}"),
    ]
