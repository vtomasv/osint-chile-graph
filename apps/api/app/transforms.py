import hashlib
import re
from dataclasses import dataclass, asdict
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
    TransformDefinition("cl.rut.normalize", "Normalizar RUT", "Valida dígito verificador y devuelve RUT canónico.", ["rut"], ["Identifier"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.email.analyze", "Analizar email .cl", "Extrae dominio, TLD y genera entidad dominio.", ["email"], ["Email", "Domain"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.phone.normalize", "Normalizar teléfono chileno", "Normaliza a formato E.164 y prepara enriquecimiento manual.", ["phone"], ["Phone", "HumanTask"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.plate.normalize", "Normalizar patente chilena", "Valida formatos frecuentes de patente chilena.", ["plate"], ["Vehicle"], "automatic", "low", False, "local_algorithm"),
    TransformDefinition("cl.dork.generate", "Generar dorks seguros", "Crea consultas para fuentes públicas y documentos abiertos.", ["rut", "email", "name", "company", "domain"], ["DorkQuery"], "automatic", "low", False, "public_passive"),
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
    return {"valid": dv == expected, "normalized": normalized, "expected_dv": expected}


def normalize_email(value: str) -> dict[str, Any]:
    email = value.strip().lower()
    valid = bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))
    domain = email.split("@")[-1] if valid else ""
    return {"valid": valid, "email": email, "domain": domain, "is_cl": domain.endswith(".cl")}


def normalize_phone(value: str) -> dict[str, Any]:
    digits = re.sub(r"\D", "", value)
    if digits.startswith("56"):
        e164 = f"+{digits}"
    elif digits.startswith("9") and len(digits) == 9:
        e164 = f"+56{digits}"
    elif len(digits) == 8:
        e164 = f"+562{digits}"
    else:
        e164 = f"+{digits}" if digits else value
    return {"normalized": e164, "country": "CL" if e164.startswith("+56") else "unknown", "carrier": "requires_authorized_lookup", "valid_shape": e164.startswith("+56") and len(re.sub(r"\D", "", e164)) in (11, 12)}


def normalize_plate(value: str) -> dict[str, Any]:
    plate = re.sub(r"[^A-Za-z0-9]", "", value).upper()
    modern = bool(re.match(r"^[BCDFGHJKLMNPQRSTVWXYZ]{4}\d{2}$", plate))
    old = bool(re.match(r"^[A-Z]{2}\d{4}$", plate))
    motorcycle = bool(re.match(r"^[A-Z]{2}\d{3}$", plate))
    return {"normalized": plate, "valid_shape": modern or old or motorcycle, "format": "modern" if modern else "old" if old else "motorcycle" if motorcycle else "unknown"}


def generate_dorks(input_type: str, value: str) -> list[dict[str, str]]:
    safe_value = value.replace('"', "").strip()
    templates = [
        ("Diario Oficial", f'site:diariooficial.interior.gob.cl "{safe_value}"'),
        ("Mercado Público", f'site:mercadopublico.cl "{safe_value}"'),
        ("Repositorios universitarios", f'(site:repositorio.uchile.cl OR site:repositorio.uc.cl OR site:repositorio.usach.cl) "{safe_value}" filetype:pdf'),
        ("Documentos públicos Chile", f'site:.cl "{safe_value}" filetype:pdf'),
    ]
    if input_type == "email":
        domain = safe_value.split("@")[-1]
        templates.append(("Dominio asociado", f'site:{domain} OR "{safe_value}"'))
    return [{"source": name, "query": query, "execution": "manual_or_configured_search_api"} for name, query in templates]


def human_task(source: str, value: str) -> dict[str, Any]:
    return {
        "type": "HumanTask",
        "source": source,
        "value": value,
        "status": "pending_manual_review",
        "reason": "La fuente puede requerir login, CAPTCHA, autorización o validación manual.",
        "instructions": "Abrir la fuente en navegador, revisar términos aplicables, ejecutar la consulta si existe autorización y registrar evidencia verificable.",
    }


def execute_transform(transform_id: str, input_type: str, value: str) -> dict[str, Any]:
    if transform_id == "cl.rut.normalize":
        return {"entities": [{"type": "Identifier", "label": validate_rut(value)["normalized"], "value": value, "properties": validate_rut(value)}]}
    if transform_id == "cl.email.analyze":
        data = normalize_email(value)
        entities = [{"type": "Email", "label": data["email"], "value": data["email"], "properties": data}]
        if data.get("domain"):
            entities.append({"type": "Domain", "label": data["domain"], "value": data["domain"], "properties": {"tld": data["domain"].split(".")[-1]}})
        return {"entities": entities, "relationships": [{"source_label": data["email"], "target_label": data.get("domain", ""), "type": "HAS_DOMAIN"}] if data.get("domain") else []}
    if transform_id == "cl.phone.normalize":
        data = normalize_phone(value)
        return {"entities": [{"type": "Phone", "label": data["normalized"], "value": data["normalized"], "properties": data}], "human_tasks": [human_task("authorized_phone_enrichment", data["normalized"])]}
    if transform_id == "cl.plate.normalize":
        data = normalize_plate(value)
        return {"entities": [{"type": "Vehicle", "label": data["normalized"], "value": data["normalized"], "properties": data}]}
    if transform_id == "cl.dork.generate":
        return {"entities": [{"type": "DorkQuery", "label": item["source"], "value": item["query"], "properties": item} for item in generate_dorks(input_type, value)]}
    if transform_id == "cl.source.diario_oficial.human":
        return {"human_tasks": [human_task("Diario Oficial", value)]}
    if transform_id == "cl.source.registro_empresas.human":
        return {"human_tasks": [human_task("Registro de Empresas y Sociedades", value)]}
    raise ValueError(f"Transform no soportado: {transform_id}")
