from pathlib import Path

path = Path('apps/api/app/transforms.py')
text = path.read_text()
text = text.replace('from typing import Any\n', 'from typing import Any\n\nfrom .osint_connectors import (\n    generic_public_queries,\n    google_search_url,\n    manual_source_task,\n    phone_public_queries,\n    plate_public_queries,\n    public_web_evidence,\n    rut_public_queries,\n)\n')
replacements = {
    'TransformDefinition("cl.rut.dorks", "Dorks especializados para RUT", "Crea consultas pasivas para documentos públicos, Diario Oficial, Mercado Público y PDFs indexados.", ["rut"], ["DorkQuery"], "automatic", "low", False, "public_passive")': 'TransformDefinition("cl.rut.dorks", "Búsqueda pública verificable de RUT", "Ejecuta búsqueda pública pasiva y persiste sólo resultados reales con URL, título, extracto y fecha; los sitios restringidos quedan como HITL.", ["rut"], ["WebEvidence", "Evidence", "SourceStatus"], "automatic", "low", False, "public_passive_verified")',
    'TransformDefinition("cl.email.dorks", "Dorks para email", "Genera consultas pasivas para email exacto, dominio asociado, documentos y repositorios públicos.", ["email"], ["DorkQuery"], "automatic", "low", False, "public_passive")': 'TransformDefinition("cl.email.dorks", "Búsqueda pública verificable de email", "Consulta resultados públicos indexados para el email y persiste evidencia real citada, no dorks como hallazgos.", ["email"], ["WebEvidence", "Evidence", "SourceStatus"], "automatic", "low", False, "public_passive_verified")',
    'TransformDefinition("cl.phone.dorks", "Dorks para teléfono", "Crea consultas pasivas para teléfono exacto en documentos públicos y sitios chilenos.", ["phone"], ["DorkQuery"], "automatic", "low", False, "public_passive")': 'TransformDefinition("cl.phone.dorks", "Búsqueda pública verificable de teléfono", "Consulta resultados públicos indexados para el teléfono y persiste evidencia real citada; portabilidad y mensajería quedan HITL.", ["phone"], ["WebEvidence", "Evidence", "SourceStatus"], "automatic", "low", False, "public_passive_verified")',
    'TransformDefinition("cl.plate.dorks", "Dorks para patente", "Crea consultas pasivas para patente en documentos, publicaciones, avisos y fuentes abiertas permitidas.", ["plate"], ["DorkQuery"], "automatic", "low", False, "public_passive")': 'TransformDefinition("cl.plate.dorks", "Búsqueda pública verificable de patente", "Consulta resultados públicos indexados para la patente y persiste evidencia real citada; servicios vehiculares restringidos quedan HITL.", ["plate"], ["WebEvidence", "Evidence", "SourceStatus"], "automatic", "low", False, "public_passive_verified")',
    'TransformDefinition("cl.domain.dorks", "Dorks para dominio", "Genera búsquedas pasivas para PDFs, correos publicados, rutas sensibles indexadas y menciones del dominio.", ["domain"], ["DorkQuery"], "automatic", "low", False, "public_passive")': 'TransformDefinition("cl.domain.dorks", "Búsqueda pública verificable de dominio", "Consulta resultados públicos indexados del dominio y persiste evidencia real citada, separada de inferencias locales.", ["domain"], ["WebEvidence", "Evidence", "SourceStatus"], "automatic", "low", False, "public_passive_verified")',
    'TransformDefinition("cl.name.variants", "Variantes de nombre", "Genera variantes de búsqueda de persona, iniciales y combinaciones para revisión de fuentes públicas.", ["name"], ["IdentifierVariant", "DorkQuery"], "automatic", "low", False, "local_algorithm")': 'TransformDefinition("cl.name.variants", "Variantes de nombre", "Genera variantes locales de nombre; no crea hallazgos OSINT sin evidencia externa.", ["name"], ["IdentifierVariant"], "automatic", "low", False, "local_algorithm")',
    'TransformDefinition("cl.company.variants", "Variantes de empresa", "Normaliza razón social, remueve sufijos frecuentes y genera consultas pasivas para documentos públicos.", ["company"], ["IdentifierVariant", "DorkQuery"], "automatic", "low", False, "local_algorithm")': 'TransformDefinition("cl.company.variants", "Variantes de empresa", "Normaliza razón social y sufijos frecuentes; no crea hallazgos OSINT sin evidencia externa.", ["company"], ["IdentifierVariant"], "automatic", "low", False, "local_algorithm")',
    'TransformDefinition("cl.dork.generate", "Generar dorks seguros", "Crea consultas genéricas para fuentes públicas y documentos abiertos según el tipo de semilla.", ["rut", "email", "phone", "plate", "name", "company", "domain"], ["DorkQuery"], "automatic", "low", False, "public_passive")': 'TransformDefinition("cl.dork.generate", "Búsqueda pública verificable genérica", "Ejecuta consultas públicas pasivas y crea únicamente evidencias reales verificables o estados de fuente, nunca dorks como hallazgos.", ["rut", "email", "phone", "plate", "name", "company", "domain"], ["WebEvidence", "Evidence", "SourceStatus"], "automatic", "low", False, "public_passive_verified")',
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f'No encontré catálogo esperado: {old[:80]}')
    text = text.replace(old, new)
text = text.replace('    return _variants_to_entities("IdentifierVariant", "name", candidates, {"parts": parts}) + _dork_entities(generate_dorks("name", clean))', '    return _variants_to_entities("IdentifierVariant", "name", candidates, {"parts": parts, "evidence_kind": "local_algorithm"})')
text = text.replace('    return _variants_to_entities("IdentifierVariant", "company", candidates, {"simplified": simplified}) + _dork_entities(generate_dorks("company", clean))', '    return _variants_to_entities("IdentifierVariant", "company", candidates, {"simplified": simplified, "evidence_kind": "local_algorithm"})')
text = text.replace('            "confidence": 0.74,\n            "properties": {"variant_type": variant_type, **(extra or {})},', '            "confidence": 0.74,\n            "properties": {"variant_type": variant_type, "evidence_kind": (extra or {}).get("evidence_kind", "local_algorithm"), **(extra or {})},')
old_human = '''def human_task(source: str, value: str, purpose: str | None = None) -> dict[str, Any]:
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
'''
new_human = '''def human_task(source: str, value: str, purpose: str | None = None, url: str | None = None, reason: str | None = None) -> dict[str, Any]:
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
    result = public_web_evidence("rut", value, rut_public_queries(value, data.get("compact", ""), data.get("normalized", value)))
    if not result.get("entities"):
        result.setdefault("human_tasks", []).extend([
            human_task("SII situación tributaria de terceros", value, "Consultar información tributaria pública sólo si el operador supera manualmente los controles y tiene base legítima.", "https://www2.sii.cl/stc/noauthz", "La consulta pública de terceros utiliza controles anti-automatización; el sistema no evade CAPTCHA ni automatiza sesiones."),
            human_task("Rutificador autorizado", value, "Revisar una fuente de rutificación sólo si sus términos y la finalidad del caso lo permiten.", google_search_url(f"rutificador {value}")),
        ])
    return result


def _phone_public_evidence(value: str) -> dict[str, Any]:
    data = normalize_phone(value)
    return public_web_evidence("phone", value, phone_public_queries(value, data.get("normalized", value), data.get("national", "")))


def _plate_public_evidence(value: str) -> dict[str, Any]:
    data = normalize_plate(value)
    result = public_web_evidence("plate", value, plate_public_queries(value, data.get("normalized", value)))
    if not result.get("entities"):
        result.setdefault("human_tasks", []).append(human_task("Volante o Maleta / informe vehicular autorizado", data.get("normalized", value), "Consultar antecedentes vehiculares sólo desde fuente autorizada y registrar evidencia textual verificable.", google_search_url(f"Volante o Maleta patente {data.get('normalized', value)}")))
    return result


def _generic_public_evidence(input_type: str, value: str) -> dict[str, Any]:
    return public_web_evidence(input_type, value, generic_public_queries(input_type, value))
'''
if old_human not in text:
    raise SystemExit('No encontré human_task original')
text = text.replace(old_human, new_human)
exec_replacements = {
    '        return {"entities": [{"type": "Identifier", "label": data["normalized"], "value": data.get("compact", value), "properties": data, "confidence": 0.95 if data.get("valid") else 0.45}]}': '        return {"entities": [{"type": "Identifier", "label": data["normalized"], "value": data.get("compact", value), "properties": {**data, "evidence_kind": "local_algorithm"}, "confidence": 0.95 if data.get("valid") else 0.45}]}',
    '        return {"entities": _dork_entities(generate_dorks("rut", value))}': '        return _rut_public_evidence(value)',
    '        return {"human_tasks": [human_task("Diario Oficial", value, "Buscar publicaciones públicas asociadas al RUT."), human_task("Mercado Público", value, "Contrastar apariciones en contratos, compras o licitaciones públicas."), human_task("Documentos públicos indexados", value, "Validar menciones en PDFs o resoluciones abiertas.")]}': '        return {"human_tasks": [human_task("Diario Oficial", value, "Buscar publicaciones públicas asociadas al RUT.", google_search_url(f"site:diariooficial.interior.gob.cl {value}")), human_task("Mercado Público", value, "Contrastar apariciones en contratos, compras o licitaciones públicas.", google_search_url(f"site:mercadopublico.cl {value}")), human_task("SII situación tributaria de terceros", value, "Consultar información tributaria pública sólo si existe base legítima y el operador completa manualmente los controles.", "https://www2.sii.cl/stc/noauthz", "SII aplica controles anti-automatización; no se automatiza ni evade CAPTCHA.")]}',
    '        return {"human_tasks": [human_task("Registro de Empresas y Sociedades", value, "Revisar participación societaria o representación legal con autorización."), human_task("SII u organismo tributario autorizado", value, "Validar información tributaria solo con permisos correspondientes.")]}': '        return {"human_tasks": [human_task("Registro de Empresas y Sociedades", value, "Revisar participación societaria o representación legal con autorización.", google_search_url(f"Registro de Empresas y Sociedades {value}")), human_task("SII u organismo tributario autorizado", value, "Validar información tributaria sólo con permisos correspondientes.", "https://www2.sii.cl/stc/noauthz", "Consulta protegida; requiere operador humano autorizado.")]}',
    '        entities = [{"type": "Email", "label": data["email"], "value": data["email"], "properties": data, "confidence": 0.9 if data.get("valid") else 0.35}]': '        entities = [{"type": "Email", "label": data["email"], "value": data["email"], "properties": {**data, "evidence_kind": "local_algorithm"}, "confidence": 0.9 if data.get("valid") else 0.35}]',
    '            entities.append({"type": "Domain", "label": data["domain"], "value": data["domain"], "properties": {"tld": data["tld"], "is_cl": data["is_cl"]}, "confidence": 0.82})': '            entities.append({"type": "Domain", "label": data["domain"], "value": data["domain"], "properties": {"tld": data["tld"], "is_cl": data["is_cl"], "evidence_kind": "local_algorithm"}, "confidence": 0.82})',
    '        return {"entities": _dork_entities(generate_dorks("email", value))}': '        return _generic_public_evidence("email", value)',
    '        return {"entities": [{"type": "Phone", "label": data["normalized"], "value": data["normalized"], "properties": data, "confidence": 0.86 if data.get("valid_shape") else 0.42}], "human_tasks": [human_task("authorized_phone_enrichment", data["normalized"], "Enriquecimiento autorizado de teléfono, sin llamadas ni mensajes automáticos.")]}': '        return {"entities": [{"type": "Phone", "label": data["normalized"], "value": data["normalized"], "properties": {**data, "evidence_kind": "local_algorithm"}, "confidence": 0.86 if data.get("valid_shape") else 0.42}], "human_tasks": [human_task("Enriquecimiento telefónico autorizado", data["normalized"], "Enriquecimiento autorizado de teléfono, sin llamadas ni mensajes automáticos.", google_search_url(f"{data[\"normalized\"]} teléfono Chile"))]}',
    '        return {"entities": _dork_entities(generate_dorks("phone", value))}': '        return _phone_public_evidence(value)',
    '        return {"human_tasks": [human_task("WhatsApp/manual contact verification", normalize_phone(value)["normalized"], "Confirmar disponibilidad solo si existe base legal o autorización; no automatizar contacto.")]}': '        return {"human_tasks": [human_task("WhatsApp / verificación manual no intrusiva", normalize_phone(value)["normalized"], "Confirmar disponibilidad sólo si existe base legal o autorización; no automatizar contacto.", "https://web.whatsapp.com/", "Requiere operador humano; el sistema no envía mensajes ni llamadas automáticas.")]}',
    '        return {"human_tasks": [human_task("Carrier/portabilidad autorizada", normalize_phone(value)["normalized"], "Consultar operador o portabilidad mediante canal legítimo y autorizado.")]}': '        return {"human_tasks": [human_task("Carrier/portabilidad autorizada", normalize_phone(value)["normalized"], "Consultar operador o portabilidad mediante canal legítimo y autorizado.", google_search_url(f"portabilidad Chile {normalize_phone(value)[\"normalized\"]}"))]}',
    '        return {"entities": [{"type": "Vehicle", "label": data["normalized"], "value": data["normalized"], "properties": data, "confidence": 0.86 if data.get("valid_shape") else 0.38}]}': '        return {"entities": [{"type": "Vehicle", "label": data["normalized"], "value": data["normalized"], "properties": {**data, "evidence_kind": "local_algorithm"}, "confidence": 0.86 if data.get("valid_shape") else 0.38}]}',
    '        return {"entities": _dork_entities(generate_dorks("plate", value))}': '        return _plate_public_evidence(value)',
    '        return {"human_tasks": [human_task("Registro Civil o canal vehicular autorizado", normalize_plate(value)["normalized"], "Consultar antecedentes vehiculares solo con permisos aplicables."), human_task("Municipalidades/multas públicas", normalize_plate(value)["normalized"], "Revisar fuentes municipales abiertas si sus términos lo permiten.")]}': '        return {"human_tasks": [human_task("Registro Civil o canal vehicular autorizado", normalize_plate(value)["normalized"], "Consultar antecedentes vehiculares sólo con permisos aplicables.", google_search_url(f"certificado anotaciones vigentes patente {normalize_plate(value)[\"normalized\"]}")), human_task("Volante o Maleta / informe vehicular autorizado", normalize_plate(value)["normalized"], "Consultar informe vehicular sólo si el operador cuenta con autorización y acepta términos aplicables.", google_search_url(f"Volante o Maleta patente {normalize_plate(value)[\"normalized\"]}")), human_task("Municipalidades/multas públicas", normalize_plate(value)["normalized"], "Revisar fuentes municipales abiertas si sus términos lo permiten.", google_search_url(f"multas patente {normalize_plate(value)[\"normalized\"]} municipalidad Chile"))]}',
    '        return {"entities": [{"type": "Domain", "label": data["domain"], "value": data["domain"], "properties": data, "confidence": 0.86 if data.get("valid") else 0.4}, {"type": "WebArtifact", "label": f"https://{data[\'domain\']}", "value": f"https://{data[\'domain\']}", "properties": {"artifact_type": "url_candidate", **data}, "confidence": 0.62}]}': '        return {"entities": [{"type": "Domain", "label": data["domain"], "value": data["domain"], "properties": {**data, "evidence_kind": "local_algorithm"}, "confidence": 0.86 if data.get("valid") else 0.4}, {"type": "WebArtifact", "label": f"https://{data[\'domain\']}", "value": f"https://{data[\'domain\']}", "properties": {"artifact_type": "url_candidate", "evidence_kind": "local_algorithm", **data}, "confidence": 0.62}]}',
    '        return {"entities": _dork_entities(generate_dorks("domain", value))}': '        return _generic_public_evidence("domain", value)',
    '        return {"human_tasks": [human_task("Diario Oficial", value, "Buscar constituciones, modificaciones o publicaciones societarias."), human_task("Mercado Público", value, "Revisar proveedor, adjudicaciones o contratos públicos."), human_task("Registro de Empresas y Sociedades", value, "Contrastar razón social y representantes si existe autorización.")]}': '        return {"human_tasks": [human_task("Diario Oficial", value, "Buscar constituciones, modificaciones o publicaciones societarias.", google_search_url(f"site:diariooficial.interior.gob.cl {value}")), human_task("Mercado Público", value, "Revisar proveedor, adjudicaciones o contratos públicos.", google_search_url(f"site:mercadopublico.cl {value}")), human_task("Registro de Empresas y Sociedades", value, "Contrastar razón social y representantes si existe autorización.", google_search_url(f"Registro de Empresas y Sociedades {value}"))]}',
    '        return {"entities": _dork_entities(generate_dorks(input_type, value))}': '        return _generic_public_evidence(input_type, value)',
}
for old, new in exec_replacements.items():
    if old not in text:
        raise SystemExit(f'No encontré execute esperado: {old[:120]}')
    text = text.replace(old, new)
path.write_text(text)
