import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Any

from .osint_connectors import (
    generic_public_queries,
    google_search_url,
    manual_source_task,
    mercado_publico_supplier_by_rut,
    phone_public_queries,
    plate_public_queries,
    public_web_evidence,
    rut_public_queries,
)


@dataclass(frozen=True)
class TransformDefinition:
    id: str
    name: str
    description: str
    input_types: list[str]
    output_types: list[str]
    execution_mode: str
    risk_level: str
    requires_human: bool
    source_policy: str


TRANSFORMS: list[TransformDefinition] = [
    TransformDefinition("cl.rut.normalize", "Normalizar y validar RUT", "Valida dígito verificador, genera formato canónico y metadatos de consistencia.", ["rut"], ["Identifier"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.rut.variants", "Variantes de búsqueda RUT", "Genera RUT con/sin puntos, sin guion, cuerpo numérico y tokens útiles para correlación pasiva.", ["rut"], ["IdentifierVariant"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.rut.dorks", "Búsqueda pública verificable de RUT", "Ejecuta búsqueda pública pasiva y persiste sólo resultados reales con URL, título, extracto y fecha; los sitios restringidos quedan como HITL.", ["rut"], ["WebEvidence", "Evidence", "SourceStatus"], "automatic", "low", False, "public_passive_verified"),
    TransformDefinition("cl.rut.public_records.human", "RUT en fuentes públicas autorizadas HITL", "Prepara verificación manual en fuentes chilenas que pueden requerir autorización, CAPTCHA o revisión de términos.", ["rut"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.rut.business_links.human", "Vínculos societarios por RUT HITL", "Crea tareas para contrastar participación societaria, publicaciones y documentos públicos asociados al RUT.", ["rut"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.email.analyze", "Analizar email .cl", "Normaliza email, extrae dominio, TLD, usuario y señales básicas de organización chilena.", ["email"], ["Email", "Domain"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.email.dorks", "Búsqueda pública verificable de email", "Consulta resultados públicos indexados para el email y persiste evidencia real citada, no dorks como hallazgos.", ["email"], ["WebEvidence", "Evidence", "SourceStatus"], "automatic", "low", False, "public_passive_verified"),
    TransformDefinition("cl.phone.normalize", "Normalizar teléfono chileno", "Normaliza a E.164, clasifica móvil/fijo/geográfico y prepara enriquecimiento autorizado.", ["phone"], ["Phone", "HumanTask"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.phone.variants", "Variantes de búsqueda teléfono", "Genera representaciones con +56, 56, espacios, guiones y formato local para correlación manual.", ["phone"], ["IdentifierVariant"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.phone.dorks", "Búsqueda pública verificable de teléfono", "Consulta resultados públicos indexados para el teléfono y persiste evidencia real citada; portabilidad y mensajería quedan HITL.", ["phone"], ["WebEvidence", "Evidence", "SourceStatus"], "automatic", "low", False, "public_passive_verified"),
    TransformDefinition("cl.phone.messaging.human", "Verificación mensajería HITL", "Prepara verificación manual no intrusiva de disponibilidad en canales de contacto permitidos.", ["phone"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.phone.carrier.human", "Carrier/portabilidad autorizada HITL", "Genera tarea para consultar operador o portabilidad solo mediante fuentes autorizadas.", ["phone"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.plate.normalize", "Normalizar patente chilena", "Valida formatos frecuentes de patente chilena: moderna, antigua, moto y casos por revisar.", ["plate"], ["Vehicle"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.plate.variants", "Variantes de búsqueda patente", "Genera patente sin separadores, con guion, espacios y patrones útiles para búsqueda documental.", ["plate"], ["IdentifierVariant"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.plate.dorks", "Búsqueda pública verificable de patente", "Consulta resultados públicos indexados para la patente y persiste evidencia real citada; servicios vehiculares restringidos quedan HITL.", ["plate"], ["WebEvidence", "Evidence", "SourceStatus"], "automatic", "low", False, "public_passive_verified"),
    TransformDefinition("cl.plate.vehicle_records.human", "Registros vehiculares HITL", "Prepara consulta manual autorizada de registros, multas o antecedentes vehiculares aplicables.", ["plate"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.domain.analyze", "Analizar dominio", "Normaliza dominio, detecta TLD .cl, subdominio probable y artefactos web básicos.", ["domain"], ["Domain", "WebArtifact"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.domain.dorks", "Búsqueda pública verificable de dominio", "Consulta resultados públicos indexados del dominio y persiste evidencia real citada, separada de inferencias locales.", ["domain"], ["WebEvidence", "Evidence", "SourceStatus"], "automatic", "low", False, "public_passive_verified"),
    TransformDefinition("cl.name.variants", "Variantes de nombre", "Genera variantes locales de nombre; no crea hallazgos OSINT sin evidencia externa.", ["name"], ["IdentifierVariant"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.company.variants", "Variantes de empresa", "Normaliza razón social y sufijos frecuentes; no crea hallazgos OSINT sin evidencia externa.", ["company"], ["IdentifierVariant"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.company.public_records.human", "Empresa en fuentes públicas HITL", "Prepara búsquedas autorizadas en Diario Oficial, Mercado Público y Registro de Empresas.", ["company"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.dork.generate", "Búsqueda pública verificable genérica", "Ejecuta consultas públicas pasivas y crea únicamente evidencias reales verificables o estados de fuente, nunca dorks como hallazgos.", ["rut", "email", "phone", "plate", "name", "company", "domain"], ["WebEvidence", "Evidence", "SourceStatus"], "automatic", "low", False, "public_passive_verified"),
    TransformDefinition("cl.source.diario_oficial.human", "Diario Oficial HITL", "Prepara búsqueda manual autorizada en Diario Oficial.", ["rut", "name", "company"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.source.registro_empresas.human", "Registro empresas HITL", "Prepara consulta manual autorizada de empresa/RUT.", ["rut", "company"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.rut.diario_oficial.human", "RUT → Diario Oficial HITL", "Abre una consulta focalizada para publicaciones del Diario Oficial asociadas al RUT; no crea hallazgos sin captura humana.", ["rut"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.rut.poder_judicial.human", "RUT → Poder Judicial HITL", "Prepara búsqueda manual autorizada en canales del Poder Judicial o consulta pública permitida; requiere operador y base legítima.", ["rut"], ["HumanTask"], "human_in_the_loop", "high", True, "manual_authorized"),
    TransformDefinition("cl.phone.caller_id.human", "Teléfono → directorios/caller ID HITL", "Genera tareas para revisar fuentes de caller ID o directorios sólo con autorización, sin llamadas ni mensajes automáticos.", ["phone"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.phone.denuncias_sernac_subtel.human", "Teléfono → SERNAC/Subtel HITL", "Prepara búsquedas manuales en reclamos, fiscalización o documentos públicos asociados a un teléfono, cuando sea legalmente procedente.", ["phone"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.plate.registro_civil.human", "Patente → Registro Civil HITL", "Prepara consulta manual de certificado/anotaciones vehiculares mediante canal autorizado; no automatiza trámites ni pagos.", ["plate"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.plate.sernac.human", "Patente → SERNAC/recalls HITL", "Prepara revisión manual de menciones públicas, recalls, reclamos o alertas asociadas a patente/modelo cuando la fuente lo permita.", ["plate"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.email.breach_check.human", "Email → brechas públicas HITL/API", "Prepara verificación de brechas sólo mediante API autorizada o consulta manual legítima; no consulta servicios con credenciales inexistentes.", ["email"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.name.linkedin.human", "Nombre → LinkedIn/dorks HITL", "Prepara búsquedas manuales en LinkedIn u otras fuentes profesionales respetando login, términos y finalidad del caso.", ["name"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("ai.extract_entities", "Extraer entidades con IA", "Extrae entidades y relaciones desde texto usando prompts configurables.", ["text"], ["Entity", "Relationship"], "automatic", "medium", False, "ai_inference"),
]


def transform_catalog() -> list[dict[str, Any]]:
    return [asdict(t) for t in TRANSFORMS]


def make_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}:{digest}"


def clean_rut(value: str) -> str:
    return re.sub(r"[^0-9kK]", "", value).upper()


def validate_rut(value: str) -> dict[str, Any]:
    cleaned = clean_rut(value)
    if len(cleaned) < 2:
        return {"valid": False, "normalized": value, "reason": "RUT demasiado corto"}
    body, dv = cleaned[:-1], cleaned[-1]
    factor, total = 2, 0
    for digit in reversed(body):
        if not digit.isdigit():
            return {"valid": False, "normalized": value, "reason": "Cuerpo contiene caracteres inválidos"}
        total += int(digit) * factor
        factor = 2 if factor == 7 else factor + 1
    remainder = 11 - (total % 11)
    expected = "0" if remainder == 11 else "K" if remainder == 10 else str(remainder)
    normalized = f"{int(body):,}".replace(",", ".") + f"-{dv}"
    return {
        "valid": dv == expected,
        "normalized": normalized,
        "expected_dv": expected,
        "body": body,
        "dv": dv,
        "compact": f"{body}{dv}",
        "without_points": f"{body}-{dv}",
        "risk_note": "Validación matemática local; no confirma identidad ni titularidad.",
    }


def normalize_email(value: str) -> dict[str, Any]:
    email = value.strip().lower()
    valid = bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))
    local_part, domain = (email.split("@", 1) + [""])[:2] if "@" in email else (email, "")
    return {
        "valid": valid,
        "email": email,
        "local_part": local_part,
        "domain": domain,
        "tld": domain.split(".")[-1] if "." in domain else "",
        "is_cl": domain.endswith(".cl"),
        "risk_note": "Análisis sintáctico local; verificar titularidad solo con evidencia autorizada.",
    }


def normalize_phone(value: str) -> dict[str, Any]:
    digits = re.sub(r"\D", "", value)
    if digits.startswith("0056"):
        digits = digits[2:]
    if digits.startswith("56"):
        national = digits[2:]
        e164 = f"+{digits}"
    elif digits.startswith("9") and len(digits) == 9:
        national = digits
        e164 = f"+56{digits}"
    elif len(digits) == 8:
        national = f"2{digits}"
        e164 = f"+562{digits}"
    elif len(digits) == 9 and digits.startswith("2"):
        national = digits
        e164 = f"+56{digits}"
    else:
        national = digits[-9:] if len(digits) >= 9 else digits
        e164 = f"+{digits}" if digits else value
    category = "mobile" if national.startswith("9") and len(national) == 9 else "landline_rm" if national.startswith("2") and len(national) == 9 else "landline_or_special" if len(national) in (8, 9) else "unknown"
    return {
        "normalized": e164,
        "national": national,
        "country": "CL" if e164.startswith("+56") else "unknown",
        "category": category,
        "carrier": "requires_authorized_lookup",
        "valid_shape": e164.startswith("+56") and len(re.sub(r"\D", "", e164)) == 11,
        "risk_note": "No se ejecuta llamada ni mensajería; enriquecimiento requiere autorización.",
    }


def normalize_plate(value: str) -> dict[str, Any]:
    plate = re.sub(r"[^A-Za-z0-9]", "", value).upper()
    modern = bool(re.match(r"^[BCDFGHJKLMNPQRSTVWXYZ]{4}\d{2}$", plate))
    old = bool(re.match(r"^[A-Z]{2}\d{4}$", plate))
    motorcycle = bool(re.match(r"^[A-Z]{2}\d{3}$", plate))
    diplomatic_or_special = bool(re.match(r"^[A-Z]{2,4}\d{1,4}$", plate)) and not (modern or old or motorcycle)
    return {
        "normalized": plate,
        "valid_shape": modern or old or motorcycle or diplomatic_or_special,
        "format": "modern" if modern else "old" if old else "motorcycle" if motorcycle else "special_or_unknown" if diplomatic_or_special else "unknown",
        "with_hyphen": f"{plate[:2]}-{plate[2:4]}-{plate[4:]}" if len(plate) == 6 else plate,
        "risk_note": "Formato local; no confirma propietario ni vigencia del vehículo.",
    }


def normalize_domain(value: str) -> dict[str, Any]:
    domain = value.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
    labels = [label for label in domain.split(".") if label]
    return {
        "domain": domain,
        "valid": bool(re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", domain)),
        "tld": labels[-1] if labels else "",
        "is_cl": domain.endswith(".cl"),
        "registrable_hint": ".".join(labels[-2:]) if len(labels) >= 2 else domain,
        "subdomain_hint": ".".join(labels[:-2]) if len(labels) > 2 else "",
    }


def rut_variants(value: str) -> list[dict[str, Any]]:
    data = validate_rut(value)
    body, dv = data.get("body", ""), data.get("dv", "")
    candidates = [data.get("normalized", value), data.get("without_points", ""), data.get("compact", ""), body, f"{body} {dv}".strip()]
    return _variants_to_entities("IdentifierVariant", "rut", candidates, {"valid": data.get("valid"), "expected_dv": data.get("expected_dv")})


def phone_variants(value: str) -> list[dict[str, Any]]:
    data = normalize_phone(value)
    national = data.get("national", "")
    candidates = [data["normalized"], data["normalized"].replace("+", ""), national, f"+56 {national[:1]} {national[1:5]} {national[5:]}" if len(national) == 9 else "", f"{national[:1]} {national[1:5]} {national[5:]}" if len(national) == 9 else ""]
    return _variants_to_entities("IdentifierVariant", "phone", candidates, {"category": data.get("category"), "country": data.get("country")})


def plate_variants(value: str) -> list[dict[str, Any]]:
    data = normalize_plate(value)
    plate = data["normalized"]
    candidates = [plate, data.get("with_hyphen", ""), f"{plate[:2]} {plate[2:4]} {plate[4:]}" if len(plate) == 6 else "", f"{plate[:4]}-{plate[4:]}" if len(plate) == 6 else ""]
    return _variants_to_entities("IdentifierVariant", "plate", candidates, {"format": data.get("format"), "valid_shape": data.get("valid_shape")})


def name_variants(value: str) -> list[dict[str, Any]]:
    clean = " ".join(value.strip().split())
    parts = clean.split()
    candidates = [clean, clean.upper(), clean.lower()]
    if len(parts) >= 2:
        candidates.extend([f"{parts[0]} {parts[-1]}", f"{parts[-1]}, {parts[0]}", " ".join([p[0] for p in parts if p]) + " " + parts[-1]])
    return _variants_to_entities("IdentifierVariant", "name", candidates, {"parts": parts, "evidence_kind": "local_algorithm"})


def company_variants(value: str) -> list[dict[str, Any]]:
    clean = " ".join(value.strip().split())
    simplified = re.sub(r"\b(spa|s\.a\.?|sa|ltda\.?|limitada|eirl)\b", "", clean, flags=re.I).strip(" ,.-")
    candidates = [clean, clean.upper(), simplified, f"{simplified} chile" if simplified else ""]
    return _variants_to_entities("IdentifierVariant", "company", candidates, {"simplified": simplified, "evidence_kind": "local_algorithm"})


def _variants_to_entities(entity_type: str, variant_type: str, candidates: list[str], extra: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    seen: set[str] = set()
    entities: list[dict[str, Any]] = []
    for candidate in candidates:
        normalized = str(candidate or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        entities.append({
            "type": entity_type,
            "label": normalized,
            "value": normalized,
            "confidence": 0.74,
            "properties": {"variant_type": variant_type, "evidence_kind": (extra or {}).get("evidence_kind", "local_algorithm"), **(extra or {})},
        })
    return entities


def generate_dorks(input_type: str, value: str) -> list[dict[str, str]]:
    safe_value = value.replace('"', "").strip()
    templates = [
        ("Documentos públicos Chile", f'site:.cl "{safe_value}" filetype:pdf'),
        ("Diario Oficial", f'site:diariooficial.interior.gob.cl "{safe_value}"'),
        ("Mercado Público", f'site:mercadopublico.cl "{safe_value}"'),
        ("Repositorios universitarios", f'(site:repositorio.uchile.cl OR site:repositorio.uc.cl OR site:repositorio.usach.cl) "{safe_value}" filetype:pdf'),
    ]
    if input_type == "rut":
        compact = clean_rut(safe_value)
        templates.extend([
            ("RUT exacto sin puntos", f'"{compact}" site:.cl'),
            ("RUT en actas o resoluciones", f'"{safe_value}" (acta OR resolución OR contrato OR licitación) filetype:pdf'),
        ])
    elif input_type == "email":
        domain = safe_value.split("@")[-1]
        templates.extend([
            ("Email exacto", f'"{safe_value}"'),
            ("Dominio asociado", f'site:{domain} OR "@{domain}"'),
        ])
    elif input_type == "phone":
        phone = normalize_phone(safe_value)["normalized"]
        templates.extend([
            ("Teléfono exacto", f'"{phone}" OR "{phone.replace("+56", "")}"'),
            ("Teléfono en documentos", f'"{phone}" filetype:pdf site:.cl'),
        ])
    elif input_type == "plate":
        plate = normalize_plate(safe_value)["normalized"]
        templates.extend([
            ("Patente exacta", f'"{plate}" site:.cl'),
            ("Patente en avisos o documentos", f'"{plate}" (vehículo OR patente OR multa OR remate)'),
        ])
    elif input_type == "domain":
        domain = normalize_domain(safe_value)["domain"]
        templates.extend([
            ("PDFs del dominio", f'site:{domain} filetype:pdf'),
            ("Emails publicados", f'site:{domain} "@{domain}"'),
            ("Menciones externas", f'"{domain}" -site:{domain}'),
        ])
    return [{"source": name, "query": query, "execution": "manual_or_configured_search_api", "input_type": input_type} for name, query in templates]


def _dork_entities(items: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [{"type": "DorkQuery", "label": item["source"], "value": item["query"], "confidence": 0.72, "properties": item} for item in items]


def human_task(source: str, value: str, purpose: str | None = None, url: str | None = None, reason: str | None = None) -> dict[str, Any]:
    query = f"{source} {value}".strip()
    return manual_source_task(
        source,
        value,
        purpose or "Verificación manual autorizada de una fuente pública o restringida.",
        url or google_search_url(query),
        reason=reason,
    )


def _rut_public_evidence(value: str) -> dict[str, Any]:
    data = validate_rut(value)
    official = mercado_publico_supplier_by_rut(value)
    public = public_web_evidence("rut", value, rut_public_queries(value, data.get("compact", ""), data.get("normalized", value)), max_results_per_query=2)
    result = {
        "entities": [*official.get("entities", []), *public.get("entities", [])],
        "evidence": [*official.get("evidence", []), *public.get("evidence", [])],
        "source_statuses": [*official.get("source_statuses", []), *public.get("source_statuses", [])],
        "human_tasks": [],
    }
    result["human_tasks"].extend([
        human_task("SII situación tributaria de terceros", value, "Consultar información tributaria pública sólo si el operador supera manualmente los controles y tiene base legítima; guardar extracto y URL exacta.", "https://www2.sii.cl/stc/noauthz", "SII aplica controles anti-automatización y condiciones de uso; el sistema no evade CAPTCHA ni automatiza sesiones."),
        human_task("Rutificador autorizado", value, "Revisar una fuente de rutificación sólo si sus términos y la finalidad del caso lo permiten; guardar evidencia explícita, no inferencias.", google_search_url(f"rutificador {value}"), "No se automatiza scraping de rutificadores no oficiales o con términos restrictivos."),
    ])
    return result


def _phone_public_evidence(value: str) -> dict[str, Any]:
    data = normalize_phone(value)
    result = public_web_evidence("phone", value, phone_public_queries(value, data.get("normalized", value), data.get("national", "")), max_results_per_query=2)
    if not result.get("evidence"):
        result.setdefault("human_tasks", []).extend([
            human_task("Búsqueda web autorizada de teléfono", data.get("normalized", value), "Buscar el número en fuentes públicas permitidas y guardar sólo evidencia textual verificable.", google_search_url(data.get("normalized", value))),
            human_task("Portabilidad/Subtel u operador autorizado", data.get("normalized", value), "Verificar carrier o portabilidad sólo mediante fuente autorizada o consentimiento aplicable.", google_search_url(f"Subtel portabilidad {data.get('national', value)}"), "No existe conector público confiable de lookup telefónico individual sin restricciones; requiere operador."),
        ])
    return result


def _plate_public_evidence(value: str) -> dict[str, Any]:
    data = normalize_plate(value)
    result = public_web_evidence("plate", value, plate_public_queries(value, data.get("normalized", value)))
    if not result.get("entities"):
        result.setdefault("human_tasks", []).append(human_task("Volante o Maleta / informe vehicular autorizado", data.get("normalized", value), "Consultar antecedentes vehiculares sólo desde fuente autorizada y registrar evidencia textual verificable.", google_search_url(f"Volante o Maleta patente {data.get('normalized', value)}")))
    return result


def _generic_public_evidence(input_type: str, value: str) -> dict[str, Any]:
    result = public_web_evidence(input_type, value, generic_public_queries(input_type, value), max_results_per_query=2)
    if not result.get("evidence"):
        result.setdefault("human_tasks", []).append(human_task("Búsqueda web pública autorizada", value, "Continuar manualmente porque el buscador público automatizado no entregó resultados verificables.", google_search_url(value), "No se crea evidencia automática sin URL y extracto verificable."))
    return result


def execute_transform(transform_id: str, input_type: str, value: str) -> dict[str, Any]:
    if transform_id == "cl.rut.normalize":
        data = validate_rut(value)
        return {"entities": [{"type": "Identifier", "label": data["normalized"], "value": data.get("compact", value), "properties": {**data, "evidence_kind": "local_algorithm"}, "confidence": 0.95 if data.get("valid") else 0.45}]}
    if transform_id == "cl.rut.variants":
        return {"entities": rut_variants(value)}
    if transform_id == "cl.rut.dorks":
        return _rut_public_evidence(value)
    if transform_id == "cl.rut.public_records.human":
        return {"human_tasks": [human_task("Diario Oficial", value, "Buscar publicaciones públicas asociadas al RUT.", google_search_url(f"site:diariooficial.interior.gob.cl {value}")), human_task("Mercado Público", value, "Contrastar apariciones en contratos, compras o licitaciones públicas.", google_search_url(f"site:mercadopublico.cl {value}")), human_task("SII situación tributaria de terceros", value, "Consultar información tributaria pública sólo si existe base legítima y el operador completa manualmente los controles.", "https://www2.sii.cl/stc/noauthz", "SII aplica controles anti-automatización; no se automatiza ni evade CAPTCHA.")]}
    if transform_id == "cl.rut.business_links.human":
        return {"human_tasks": [human_task("Registro de Empresas y Sociedades", value, "Revisar participación societaria o representación legal con autorización.", google_search_url(f"Registro de Empresas y Sociedades {value}")), human_task("SII u organismo tributario autorizado", value, "Validar información tributaria sólo con permisos correspondientes.", "https://www2.sii.cl/stc/noauthz", "Consulta protegida; requiere operador humano autorizado.")]}
    if transform_id == "cl.email.analyze":
        data = normalize_email(value)
        entities = [{"type": "Email", "label": data["email"], "value": data["email"], "properties": {**data, "evidence_kind": "local_algorithm"}, "confidence": 0.9 if data.get("valid") else 0.35}]
        if data.get("domain"):
            entities.append({"type": "Domain", "label": data["domain"], "value": data["domain"], "properties": {"tld": data["tld"], "is_cl": data["is_cl"], "evidence_kind": "local_algorithm"}, "confidence": 0.82})
        return {"entities": entities, "relationships": [{"source_label": data["email"], "target_label": data.get("domain", ""), "type": "HAS_DOMAIN"}] if data.get("domain") else []}
    if transform_id == "cl.email.dorks":
        return _generic_public_evidence("email", value)
    if transform_id == "cl.phone.normalize":
        data = normalize_phone(value)
        normalized = data["normalized"]
        return {"entities": [{"type": "Phone", "label": normalized, "value": normalized, "properties": {**data, "evidence_kind": "local_algorithm"}, "confidence": 0.86 if data.get("valid_shape") else 0.42}], "human_tasks": [human_task("Enriquecimiento telefónico autorizado", normalized, "Enriquecimiento autorizado de teléfono, sin llamadas ni mensajes automáticos.", google_search_url(f"{normalized} teléfono Chile"))]}
    if transform_id == "cl.phone.variants":
        return {"entities": phone_variants(value)}
    if transform_id == "cl.phone.dorks":
        return _phone_public_evidence(value)
    if transform_id == "cl.phone.messaging.human":
        return {"human_tasks": [human_task("WhatsApp / verificación manual no intrusiva", normalize_phone(value)["normalized"], "Confirmar disponibilidad sólo si existe base legal o autorización; no automatizar contacto.", "https://web.whatsapp.com/", "Requiere operador humano; el sistema no envía mensajes ni llamadas automáticas.")]}
    if transform_id == "cl.phone.carrier.human":
        normalized = normalize_phone(value)["normalized"]
        return {"human_tasks": [human_task("Carrier/portabilidad autorizada", normalized, "Consultar operador o portabilidad mediante canal legítimo y autorizado.", google_search_url(f"portabilidad Chile {normalized}"))]}
    if transform_id == "cl.plate.normalize":
        data = normalize_plate(value)
        return {"entities": [{"type": "Vehicle", "label": data["normalized"], "value": data["normalized"], "properties": {**data, "evidence_kind": "local_algorithm"}, "confidence": 0.86 if data.get("valid_shape") else 0.38}]}
    if transform_id == "cl.plate.variants":
        return {"entities": plate_variants(value)}
    if transform_id == "cl.plate.dorks":
        return _plate_public_evidence(value)
    if transform_id == "cl.plate.vehicle_records.human":
        normalized = normalize_plate(value)["normalized"]
        return {"human_tasks": [human_task("Registro Civil o canal vehicular autorizado", normalized, "Consultar antecedentes vehiculares sólo con permisos aplicables.", google_search_url(f"certificado anotaciones vigentes patente {normalized}")), human_task("Volante o Maleta / informe vehicular autorizado", normalized, "Consultar informe vehicular sólo si el operador cuenta con autorización y acepta términos aplicables.", google_search_url(f"Volante o Maleta patente {normalized}")), human_task("Municipalidades/multas públicas", normalized, "Revisar fuentes municipales abiertas si sus términos lo permiten.", google_search_url(f"multas patente {normalized} municipalidad Chile"))]}
    if transform_id == "cl.domain.analyze":
        data = normalize_domain(value)
        return {"entities": [{"type": "Domain", "label": data["domain"], "value": data["domain"], "properties": {**data, "evidence_kind": "local_algorithm"}, "confidence": 0.86 if data.get("valid") else 0.4}, {"type": "WebArtifact", "label": f"https://{data['domain']}", "value": f"https://{data['domain']}", "properties": {"artifact_type": "url_candidate", "evidence_kind": "local_algorithm", **data}, "confidence": 0.62}]}
    if transform_id == "cl.domain.dorks":
        return _generic_public_evidence("domain", value)
    if transform_id == "cl.name.variants":
        return {"entities": name_variants(value)}
    if transform_id == "cl.company.variants":
        return {"entities": company_variants(value)}
    if transform_id == "cl.company.public_records.human":
        return {"human_tasks": [human_task("Diario Oficial", value, "Buscar constituciones, modificaciones o publicaciones societarias.", google_search_url(f"site:diariooficial.interior.gob.cl {value}")), human_task("Mercado Público", value, "Revisar proveedor, adjudicaciones o contratos públicos.", google_search_url(f"site:mercadopublico.cl {value}")), human_task("Registro de Empresas y Sociedades", value, "Contrastar razón social y representantes si existe autorización.", google_search_url(f"Registro de Empresas y Sociedades {value}"))]}
    if transform_id == "cl.dork.generate":
        return _generic_public_evidence(input_type, value)
    if transform_id == "cl.source.diario_oficial.human":
        return {"human_tasks": [human_task("Diario Oficial", value)]}
    if transform_id == "cl.source.registro_empresas.human":
        return {"human_tasks": [human_task("Registro de Empresas y Sociedades", value)]}
    if transform_id == "cl.rut.diario_oficial.human":
        data = validate_rut(value)
        normalized = data.get("normalized", value)
        return {"human_tasks": [
            human_task("Diario Oficial - publicaciones por RUT", normalized, "Buscar publicaciones, avisos, resoluciones o documentos indexados asociados al RUT; guardar sólo URL, fecha y extracto verificable.", google_search_url(f"site:diariooficial.interior.gob.cl {normalized}"), "El Diario Oficial puede no exponer API estable para esta consulta; se mantiene como revisión humana."),
            human_task("Diario Oficial - variantes RUT", data.get("compact", value), "Revisar variantes sin puntos/guion para evitar falsos negativos, manteniendo trazabilidad de consulta.", google_search_url(f"site:diariooficial.interior.gob.cl {data.get('compact', value)}")),
        ]}
    if transform_id == "cl.rut.poder_judicial.human":
        data = validate_rut(value)
        normalized = data.get("normalized", value)
        return {"human_tasks": [
            human_task("Poder Judicial / Oficina Judicial Virtual", normalized, "Consultar sólo si existe base legítima y autorización aplicable; registrar rol, tribunal, fecha y extracto público si la fuente lo permite.", "https://oficinajudicialvirtual.pjud.cl/", "Fuente sensible con interacción, sesión/CAPTCHA y restricciones; no se automatiza."),
            human_task("Poder Judicial indexado", normalized, "Buscar menciones públicas indexadas sin evadir controles ni autenticación.", google_search_url(f"site:pjud.cl {normalized}")),
        ]}
    if transform_id == "cl.phone.caller_id.human":
        data = normalize_phone(value)
        normalized = data.get("normalized", value)
        return {"human_tasks": [
            human_task("Caller ID/directorios autorizados", normalized, "Revisar manualmente servicios de identificación o directorios sólo si sus términos y la finalidad del caso lo permiten; no llamar ni enviar mensajes.", google_search_url(f"{normalized} caller ID Chile"), "Estos servicios suelen tener términos restrictivos, login o datos personales; se requiere operador."),
            human_task("Búsqueda exacta de teléfono", normalized, "Buscar apariciones públicas exactas del teléfono y guardar URL/extracto verificable si existe.", google_search_url(f'"{normalized}" OR "{data.get("national", value)}" Chile')),
        ]}
    if transform_id == "cl.phone.denuncias_sernac_subtel.human":
        data = normalize_phone(value)
        normalized = data.get("normalized", value)
        national = data.get("national", value)
        return {"human_tasks": [
            human_task("SERNAC documentos/reclamos indexados", normalized, "Buscar menciones públicas del teléfono en documentos, reclamos o alertas indexadas; no inferir titularidad sin evidencia.", google_search_url(f"site:sernac.cl ({normalized} OR {national})")),
            human_task("Subtel documentos indexados", normalized, "Revisar documentos públicos de Subtel o portabilidad sólo por canales permitidos.", google_search_url(f"site:subtel.gob.cl ({normalized} OR {national})")),
        ]}
    if transform_id == "cl.plate.registro_civil.human":
        normalized = normalize_plate(value)["normalized"]
        return {"human_tasks": [
            human_task("Registro Civil - certificado/anotaciones vehiculares", normalized, "Consultar certificados o anotaciones vehiculares sólo mediante canal autorizado, con operador y permisos aplicables; guardar extracto del certificado si procede.", google_search_url(f"Registro Civil certificado anotaciones vigentes patente {normalized}"), "No se automatizan trámites, pagos, sesiones ni CAPTCHA."),
        ]}
    if transform_id == "cl.plate.sernac.human":
        normalized = normalize_plate(value)["normalized"]
        return {"human_tasks": [
            human_task("SERNAC / alertas o recalls vehiculares", normalized, "Revisar menciones públicas asociadas a la patente, modelo o recall si aparece en documentos; guardar sólo evidencia verificable.", google_search_url(f"site:sernac.cl {normalized} vehículo OR recall OR alerta")),
            human_task("Documentos públicos de patente", normalized, "Buscar documentos públicos o remates asociados a patente sin usar scraping restrictivo.", google_search_url(f'"{normalized}" (patente OR vehículo OR remate OR multa) Chile')),
        ]}
    if transform_id == "cl.email.breach_check.human":
        email = normalize_email(value).get("email", value)
        return {"human_tasks": [
            human_task("HaveIBeenPwned API/autorizada", email, "Consultar brechas sólo con API key autorizada o consentimiento aplicable; registrar fuente, fecha, breach y extracto permitido.", "https://haveibeenpwned.com/", "La API pública moderna requiere condiciones y/o credenciales; no se simula resultado."),
            human_task("Búsqueda pública exacta de email", email, "Buscar apariciones públicas exactas del correo en fuentes indexadas y guardar evidencia real si existe.", google_search_url(f'"{email}"')),
        ]}
    if transform_id == "cl.name.linkedin.human":
        clean = " ".join(value.strip().split())
        return {"human_tasks": [
            human_task("LinkedIn búsqueda manual", clean, "Buscar perfiles profesionales sólo desde sesión/operador autorizado y citar datos públicos observables; no automatizar login ni scraping.", google_search_url(f"site:linkedin.com/in {clean} Chile"), "LinkedIn bloquea automatización y requiere respetar términos; se conserva como HITL."),
            human_task("Nombre en documentos públicos Chile", clean, "Buscar menciones del nombre en documentos públicos chilenos y capturar URL/extracto verificable.", google_search_url(f'"{clean}" filetype:pdf Chile')),
        ]}
    raise ValueError(f"Transform no soportado: {transform_id}")
