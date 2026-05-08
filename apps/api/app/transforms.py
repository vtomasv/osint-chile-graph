import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Any


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
    TransformDefinition("cl.rut.dorks", "Dorks especializados para RUT", "Crea consultas pasivas para documentos públicos, Diario Oficial, Mercado Público y PDFs indexados.", ["rut"], ["DorkQuery"], "automatic", "low", False, "public_passive"),
    TransformDefinition("cl.rut.public_records.human", "RUT en fuentes públicas autorizadas HITL", "Prepara verificación manual en fuentes chilenas que pueden requerir autorización, CAPTCHA o revisión de términos.", ["rut"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.rut.business_links.human", "Vínculos societarios por RUT HITL", "Crea tareas para contrastar participación societaria, publicaciones y documentos públicos asociados al RUT.", ["rut"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.email.analyze", "Analizar email .cl", "Normaliza email, extrae dominio, TLD, usuario y señales básicas de organización chilena.", ["email"], ["Email", "Domain"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.email.dorks", "Dorks para email", "Genera consultas pasivas para email exacto, dominio asociado, documentos y repositorios públicos.", ["email"], ["DorkQuery"], "automatic", "low", False, "public_passive"),
    TransformDefinition("cl.phone.normalize", "Normalizar teléfono chileno", "Normaliza a E.164, clasifica móvil/fijo/geográfico y prepara enriquecimiento autorizado.", ["phone"], ["Phone", "HumanTask"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.phone.variants", "Variantes de búsqueda teléfono", "Genera representaciones con +56, 56, espacios, guiones y formato local para correlación manual.", ["phone"], ["IdentifierVariant"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.phone.dorks", "Dorks para teléfono", "Crea consultas pasivas para teléfono exacto en documentos públicos y sitios chilenos.", ["phone"], ["DorkQuery"], "automatic", "low", False, "public_passive"),
    TransformDefinition("cl.phone.messaging.human", "Verificación mensajería HITL", "Prepara verificación manual no intrusiva de disponibilidad en canales de contacto permitidos.", ["phone"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.phone.carrier.human", "Carrier/portabilidad autorizada HITL", "Genera tarea para consultar operador o portabilidad solo mediante fuentes autorizadas.", ["phone"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.plate.normalize", "Normalizar patente chilena", "Valida formatos frecuentes de patente chilena: moderna, antigua, moto y casos por revisar.", ["plate"], ["Vehicle"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.plate.variants", "Variantes de búsqueda patente", "Genera patente sin separadores, con guion, espacios y patrones útiles para búsqueda documental.", ["plate"], ["IdentifierVariant"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.plate.dorks", "Dorks para patente", "Crea consultas pasivas para patente en documentos, publicaciones, avisos y fuentes abiertas permitidas.", ["plate"], ["DorkQuery"], "automatic", "low", False, "public_passive"),
    TransformDefinition("cl.plate.vehicle_records.human", "Registros vehiculares HITL", "Prepara consulta manual autorizada de registros, multas o antecedentes vehiculares aplicables.", ["plate"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.domain.analyze", "Analizar dominio", "Normaliza dominio, detecta TLD .cl, subdominio probable y artefactos web básicos.", ["domain"], ["Domain", "WebArtifact"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.domain.dorks", "Dorks para dominio", "Genera búsquedas pasivas para PDFs, correos publicados, rutas sensibles indexadas y menciones del dominio.", ["domain"], ["DorkQuery"], "automatic", "low", False, "public_passive"),
    TransformDefinition("cl.name.variants", "Variantes de nombre", "Genera variantes de búsqueda de persona, iniciales y combinaciones para revisión de fuentes públicas.", ["name"], ["IdentifierVariant", "DorkQuery"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.company.variants", "Variantes de empresa", "Normaliza razón social, remueve sufijos frecuentes y genera consultas pasivas para documentos públicos.", ["company"], ["IdentifierVariant", "DorkQuery"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.company.public_records.human", "Empresa en fuentes públicas HITL", "Prepara búsquedas autorizadas en Diario Oficial, Mercado Público y Registro de Empresas.", ["company"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.dork.generate", "Generar dorks seguros", "Crea consultas genéricas para fuentes públicas y documentos abiertos según el tipo de semilla.", ["rut", "email", "phone", "plate", "name", "company", "domain"], ["DorkQuery"], "automatic", "low", False, "public_passive"),
    TransformDefinition("cl.source.diario_oficial.human", "Diario Oficial HITL", "Prepara búsqueda manual autorizada en Diario Oficial.", ["rut", "name", "company"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
    TransformDefinition("cl.source.registro_empresas.human", "Registro empresas HITL", "Prepara consulta manual autorizada de empresa/RUT.", ["rut", "company"], ["HumanTask"], "human_in_the_loop", "medium", True, "manual_authorized"),
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
    return _variants_to_entities("IdentifierVariant", "name", candidates, {"parts": parts}) + _dork_entities(generate_dorks("name", clean))


def company_variants(value: str) -> list[dict[str, Any]]:
    clean = " ".join(value.strip().split())
    simplified = re.sub(r"\b(spa|s\.a\.?|sa|ltda\.?|limitada|eirl)\b", "", clean, flags=re.I).strip(" ,.-")
    candidates = [clean, clean.upper(), simplified, f"{simplified} chile" if simplified else ""]
    return _variants_to_entities("IdentifierVariant", "company", candidates, {"simplified": simplified}) + _dork_entities(generate_dorks("company", clean))


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
            "properties": {"variant_type": variant_type, **(extra or {})},
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


def human_task(source: str, value: str, purpose: str | None = None) -> dict[str, Any]:
    return {
        "type": "HumanTask",
        "source": source,
        "value": value,
        "status": "pending_manual_review",
        "purpose": purpose or "Verificación manual autorizada de una fuente pública o restringida.",
        "reason": "La fuente puede requerir login, CAPTCHA, autorización, pago, términos específicos o validación manual.",
        "instructions": "Abrir la fuente en navegador, revisar términos aplicables, ejecutar la consulta solo si existe autorización y registrar evidencia verificable con fecha, URL y extracto.",
        "expected_evidence": ["URL o nombre de fuente", "fecha/hora de consulta", "extracto textual", "captura o referencia documental si procede"],
    }


def execute_transform(transform_id: str, input_type: str, value: str) -> dict[str, Any]:
    if transform_id == "cl.rut.normalize":
        data = validate_rut(value)
        return {"entities": [{"type": "Identifier", "label": data["normalized"], "value": data.get("compact", value), "properties": data, "confidence": 0.95 if data.get("valid") else 0.45}]}
    if transform_id == "cl.rut.variants":
        return {"entities": rut_variants(value)}
    if transform_id == "cl.rut.dorks":
        return {"entities": _dork_entities(generate_dorks("rut", value))}
    if transform_id == "cl.rut.public_records.human":
        return {"human_tasks": [human_task("Diario Oficial", value, "Buscar publicaciones públicas asociadas al RUT."), human_task("Mercado Público", value, "Contrastar apariciones en contratos, compras o licitaciones públicas."), human_task("Documentos públicos indexados", value, "Validar menciones en PDFs o resoluciones abiertas.")]}
    if transform_id == "cl.rut.business_links.human":
        return {"human_tasks": [human_task("Registro de Empresas y Sociedades", value, "Revisar participación societaria o representación legal con autorización."), human_task("SII u organismo tributario autorizado", value, "Validar información tributaria solo con permisos correspondientes.")]}
    if transform_id == "cl.email.analyze":
        data = normalize_email(value)
        entities = [{"type": "Email", "label": data["email"], "value": data["email"], "properties": data, "confidence": 0.9 if data.get("valid") else 0.35}]
        if data.get("domain"):
            entities.append({"type": "Domain", "label": data["domain"], "value": data["domain"], "properties": {"tld": data["tld"], "is_cl": data["is_cl"]}, "confidence": 0.82})
        return {"entities": entities, "relationships": [{"source_label": data["email"], "target_label": data.get("domain", ""), "type": "HAS_DOMAIN"}] if data.get("domain") else []}
    if transform_id == "cl.email.dorks":
        return {"entities": _dork_entities(generate_dorks("email", value))}
    if transform_id == "cl.phone.normalize":
        data = normalize_phone(value)
        return {"entities": [{"type": "Phone", "label": data["normalized"], "value": data["normalized"], "properties": data, "confidence": 0.86 if data.get("valid_shape") else 0.42}], "human_tasks": [human_task("authorized_phone_enrichment", data["normalized"], "Enriquecimiento autorizado de teléfono, sin llamadas ni mensajes automáticos.")]}
    if transform_id == "cl.phone.variants":
        return {"entities": phone_variants(value)}
    if transform_id == "cl.phone.dorks":
        return {"entities": _dork_entities(generate_dorks("phone", value))}
    if transform_id == "cl.phone.messaging.human":
        return {"human_tasks": [human_task("WhatsApp/manual contact verification", normalize_phone(value)["normalized"], "Confirmar disponibilidad solo si existe base legal o autorización; no automatizar contacto.")]}
    if transform_id == "cl.phone.carrier.human":
        return {"human_tasks": [human_task("Carrier/portabilidad autorizada", normalize_phone(value)["normalized"], "Consultar operador o portabilidad mediante canal legítimo y autorizado.")]}
    if transform_id == "cl.plate.normalize":
        data = normalize_plate(value)
        return {"entities": [{"type": "Vehicle", "label": data["normalized"], "value": data["normalized"], "properties": data, "confidence": 0.86 if data.get("valid_shape") else 0.38}]}
    if transform_id == "cl.plate.variants":
        return {"entities": plate_variants(value)}
    if transform_id == "cl.plate.dorks":
        return {"entities": _dork_entities(generate_dorks("plate", value))}
    if transform_id == "cl.plate.vehicle_records.human":
        return {"human_tasks": [human_task("Registro Civil o canal vehicular autorizado", normalize_plate(value)["normalized"], "Consultar antecedentes vehiculares solo con permisos aplicables."), human_task("Municipalidades/multas públicas", normalize_plate(value)["normalized"], "Revisar fuentes municipales abiertas si sus términos lo permiten.")]}
    if transform_id == "cl.domain.analyze":
        data = normalize_domain(value)
        return {"entities": [{"type": "Domain", "label": data["domain"], "value": data["domain"], "properties": data, "confidence": 0.86 if data.get("valid") else 0.4}, {"type": "WebArtifact", "label": f"https://{data['domain']}", "value": f"https://{data['domain']}", "properties": {"artifact_type": "url_candidate", **data}, "confidence": 0.62}]}
    if transform_id == "cl.domain.dorks":
        return {"entities": _dork_entities(generate_dorks("domain", value))}
    if transform_id == "cl.name.variants":
        return {"entities": name_variants(value)}
    if transform_id == "cl.company.variants":
        return {"entities": company_variants(value)}
    if transform_id == "cl.company.public_records.human":
        return {"human_tasks": [human_task("Diario Oficial", value, "Buscar constituciones, modificaciones o publicaciones societarias."), human_task("Mercado Público", value, "Revisar proveedor, adjudicaciones o contratos públicos."), human_task("Registro de Empresas y Sociedades", value, "Contrastar razón social y representantes si existe autorización.")]}
    if transform_id == "cl.dork.generate":
        return {"entities": _dork_entities(generate_dorks(input_type, value))}
    if transform_id == "cl.source.diario_oficial.human":
        return {"human_tasks": [human_task("Diario Oficial", value)]}
    if transform_id == "cl.source.registro_empresas.human":
        return {"human_tasks": [human_task("Registro de Empresas y Sociedades", value)]}
    raise ValueError(f"Transform no soportado: {transform_id}")
