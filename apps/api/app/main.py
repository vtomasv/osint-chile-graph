from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from .ai import load_prompts, run_ai_prompt, save_prompt
from .config import get_settings
from .db import Entity, Evidence, Investigation, Relationship, TransformRun, init_db, session_scope
from .graph import sync_entity_to_neo4j, sync_relationship_to_neo4j
from .schemas import AIRequest, GraphOut, HumanTaskCompletionRequest, InvestigationCreate, PromptUpdate, SeedRequest, TransformRunRequest
from .transforms import TRANSFORMS, execute_transform, make_id, transform_catalog
from .frameworks import framework_catalog


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with session_scope() as session:
        if not session.get(Investigation, "demo"):
            session.add(Investigation(id="demo", title="Caso demo: mapa OSINT Chile", objective="Demostrar transforms seguros con RUT, email, teléfono y patente."))
    yield


settings = get_settings()
app = FastAPI(title="OSINT Chile Graph API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def _entity_payload(entity: Entity) -> dict:
    return {"id": entity.id, "type": entity.type, "label": entity.label, "value": entity.value, "properties": entity.properties or {}, "confidence": entity.confidence}


def _evidence_kind(evidence: Evidence) -> str:
    props = evidence.properties or {}
    if props.get("human_task_completed"):
        return "operator_captured_evidence"
    return str(props.get("evidence_kind") or props.get("source_state") or "unspecified")


def _is_source_status(evidence: Evidence) -> bool:
    return _evidence_kind(evidence) == "source_status" or evidence.source_name.startswith("source_status:")


def _is_verified_evidence(evidence: Evidence) -> bool:
    return _evidence_kind(evidence) in {"verified_evidence", "verified_public_search_result", "verified_public_api_result", "operator_captured_evidence"}


def _is_local_algorithm_record(evidence: Evidence) -> bool:
    return _evidence_kind(evidence) == "local_algorithm"


def _source_statuses_from_runs(runs: list[TransformRun]) -> list[dict]:
    statuses: list[dict] = []
    for run in runs:
        for status in (run.output or {}).get("source_statuses", []):
            statuses.append({
                **status,
                "transform_id": run.transform_id,
                "run_id": run.id,
                "input_type": run.input_type,
                "input_value": run.input_value,
                "created_at": run.created_at.isoformat(),
            })
    return statuses


def _evidence_payload(evidence: Evidence) -> dict:
    props = evidence.properties or {}
    return {
        "id": evidence.id,
        "source_name": evidence.source_name,
        "source_url": evidence.source_url,
        "extract": evidence.extract,
        "confidence": evidence.confidence,
        "properties": props,
        "evidence_kind": _evidence_kind(evidence),
        "is_verified_osint": _is_verified_evidence(evidence),
        "created_at": evidence.created_at.isoformat(),
    }


def _relationship_payload(rel: Relationship, entity_lookup: dict[str, Entity]) -> dict:
    source = entity_lookup.get(rel.source_id)
    target = entity_lookup.get(rel.target_id)
    return {
        "id": rel.id,
        "type": rel.type,
        "source_id": rel.source_id,
        "source_label": source.label if source else rel.source_id,
        "source_type": source.type if source else "Unknown",
        "target_id": rel.target_id,
        "target_label": target.label if target else rel.target_id,
        "target_type": target.type if target else "Unknown",
        "properties": rel.properties or {},
        "confidence": rel.confidence,
    }


def _find_related_evidence(entity: Entity, evidence_rows: list[Evidence], relationships: list[Relationship]) -> list[Evidence]:
    related_ids = {entity.id}
    for rel in relationships:
        if rel.source_id == entity.id:
            related_ids.add(rel.target_id)
        if rel.target_id == entity.id:
            related_ids.add(rel.source_id)
    matches = []
    for evidence in evidence_rows:
        props = evidence.properties or {}
        prop_ids = {str(props.get("entity_id", "")), str(props.get("task_id", ""))}
        prop_ids.update(str(item) for item in props.get("related_entity_ids", []) if item)
        text = f"{evidence.extract} {evidence.source_name}".lower()
        if related_ids.intersection(prop_ids) or entity.label.lower() in text or (entity.value and entity.value.lower() in text):
            matches.append(evidence)
    return matches[:12]


def _describe_entity(entity: Entity, rels: list[dict], evidence_items: list[dict], task_count: int) -> dict:
    outgoing = [rel for rel in rels if rel["source_id"] == entity.id]
    incoming = [rel for rel in rels if rel["target_id"] == entity.id]
    evidence_count = len(evidence_items)
    relation_count = len(outgoing) + len(incoming)
    props = entity.properties or {}
    facts = []
    if entity.type == "Seed":
        facts.append(f"Dato semilla de tipo {props.get('input_type', 'desconocido')}; sirve como punto de entrada del expediente.")
    elif entity.type == "HumanTask":
        facts.append("Compuerta human-in-the-loop pendiente o resuelta; requiere revisión manual autorizada antes de confirmar el dato.")
    else:
        facts.append(f"Entidad {entity.type} encontrada con confianza {round((entity.confidence or 0) * 100)}%.")
    if evidence_count:
        facts.append(f"Tiene {evidence_count} evidencia(s) asociada(s) que pueden revisarse y citarse en informe.")
    if relation_count:
        connected_labels = []
        for rel in (outgoing + incoming)[:4]:
            other = rel["target_label"] if rel["source_id"] == entity.id else rel["source_label"]
            connected_labels.append(other)
        facts.append("Se conecta con " + ", ".join(dict.fromkeys(connected_labels)) + ".")
    if task_count:
        facts.append(f"Mantiene {task_count} tarea(s) humanas relacionadas para validación o enriquecimiento.")
    gaps = []
    if not evidence_count:
        gaps.append("No hay evidencia textual capturada para respaldar esta entidad; conviene ejecutar transforms o completar tareas HITL.")
    if entity.confidence < 0.7:
        gaps.append("La confianza es media/baja; se recomienda corroborar en una segunda fuente.")
    if entity.type in {"Rut", "RUT", "Phone", "Plate", "Vehicle", "Company", "Person"} and task_count:
        gaps.append("Existen fuentes manuales sugeridas que podrían aportar datos útiles si se consultan con autorización.")
    return {
        "title": f"Perfil analítico de {entity.label}",
        "summary": " ".join(facts),
        "facts": facts,
        "gaps": gaps or ["No se detectan brechas críticas con los datos actualmente disponibles."],
        "next_steps": [
            "Revisar evidencias asociadas y conservar URL, fecha y extracto verificable.",
            "Completar tareas HITL vinculadas y guardar resultados estructurados.",
            "Cruzar relaciones con otras entidades del objetivo antes de elevar inferencias a hechos.",
        ],
        "mode": "AI-assisted local reasoning",
    }


def _build_search_url(source: str, value: str, purpose: str = "") -> str:
    source_l = source.lower()
    query = value
    if "diario oficial" in source_l:
        query = f"site:diariooficial.interior.gob.cl {value}"
    elif "mercado público" in source_l or "mercado publico" in source_l:
        query = f"site:mercadopublico.cl {value}"
    elif "registro de empresas" in source_l:
        query = f"site:registrodeempresasysociedades.cl {value}"
    elif "municipal" in source_l:
        query = f"{value} multas municipalidad Chile"
    elif "documentos" in source_l:
        query = f"{value} filetype:pdf Chile"
    elif source_l.startswith("authorized"):
        query = f"{value} teléfono Chile fuente autorizada"
    else:
        query = f"{source} {value} {purpose}".strip()
    return "https://www.google.com/search?q=" + query.replace(" ", "+")


def _build_dossier_analysis(investigation: Investigation, entities: list[Entity], relationships: list[Relationship], evidence_rows: list[Evidence], runs: list[TransformRun]) -> dict:
    meaningful = [e for e in entities if e.type != "HumanTask"]
    human_tasks = [e for e in entities if e.type == "HumanTask"]
    verified_evidence = [e for e in evidence_rows if _is_verified_evidence(e)]
    local_only = [e for e in meaningful if (e.properties or {}).get("evidence_kind") == "local_algorithm"]
    top_types: dict[str, int] = {}
    for entity in meaningful:
        top_types[entity.type] = top_types.get(entity.type, 0) + 1
    strongest = sorted(meaningful, key=lambda item: item.confidence or 0, reverse=True)[:5]
    pending = [task for task in human_tasks if (task.properties or {}).get("status", "pending_manual_review") != "completed_by_operator"]
    executive = (
        f"El expediente '{investigation.title}' contiene {len(meaningful)} entidades, "
        f"pero sólo {len(verified_evidence)} evidencia(s) OSINT verificable(s) con URL/extracto o captura humana. "
        f"Hay {len(local_only)} entidad(es) derivadas por algoritmos locales y {len(pending)} tarea(s) HITL pendiente(s). "
        "Las entidades locales no deben tratarse como hallazgos confirmados hasta asociarlas con evidencia citada."
    )
    key_findings = [
        f"Evidencia verificada desde {e.source_name}: {e.extract[:160]}" for e in verified_evidence[:5]
    ]
    if not key_findings:
        key_findings = ["Todavía no hay evidencia OSINT verificada; complete tareas HITL o configure conectores/API públicos autorizados."]
    return {
        "mode": "evidence-first local reasoning",
        "executive_summary": executive,
        "key_findings": key_findings,
        "candidate_entities": [
            f"{entity.type}: {entity.label} · confianza algorítmica {round((entity.confidence or 0) * 100)}%" for entity in strongest
        ],
        "gaps": [
            "Las fuentes con CAPTCHA, login, términos restrictivos o bloqueo anti-bot se registran como HITL, no como evidencia automática.",
            "Los algoritmos locales sólo normalizan o generan variantes; no confirman identidad, titularidad ni relación factual.",
            "Para convertir una hipótesis en hallazgo debe existir URL, extracto, fecha de consulta, fuente y confianza explícita.",
        ],
        "recommended_next_steps": [
            "Completar primero las tareas HITL asociadas al dato central y pegar extracto verificable desde la fuente.",
            "Configurar conectores/API oficiales permitidos para automatizar fuentes que expongan acceso documentado.",
            "Usar Sankey y estados de fuente para ver qué transforms realmente produjeron evidencia y cuáles sólo prepararon trabajo humano.",
        ],
        "entity_type_distribution": top_types,
        "ai_status": "Narrativa local basada estrictamente en evidencia persistida; no inventa datos externos.",
    }


def _build_visualizations(entities: list[Entity], relationships: list[Relationship], runs: list[TransformRun], evidence_rows: list[Evidence]) -> dict:
    treemap = []
    grouped: dict[str, int] = {}
    for entity in entities:
        grouped[entity.type] = grouped.get(entity.type, 0) + 1
    for kind, count in grouped.items():
        treemap.append({"name": kind, "size": count, "fill": kind})

    node_index: dict[str, int] = {}
    sankey_nodes: list[dict] = []
    sankey_links: list[dict] = []

    def idx(name: str) -> int:
        if name not in node_index:
            node_index[name] = len(sankey_nodes)
            sankey_nodes.append({"name": name})
        return node_index[name]

    for run in runs[:30]:
        out = run.output or {}
        transform_name = f"Transform: {run.transform_id}"
        source_i = idx(transform_name)
        if out.get("entities"):
            sankey_links.append({"source": source_i, "target": idx("Entidades útiles"), "value": max(1, len(out.get("entities", [])))})
        if out.get("human_tasks"):
            sankey_links.append({"source": source_i, "target": idx("Tareas HITL"), "value": max(1, len(out.get("human_tasks", [])))})
    if evidence_rows:
        sankey_links.append({"source": idx("Tareas HITL"), "target": idx("Evidencia capturada"), "value": len([e for e in evidence_rows if (e.properties or {}).get("human_task_completed")]) or len(evidence_rows)})

    semantic_clusters: dict[str, dict] = {}
    for rel in relationships:
        bucket = rel.type
        semantic_clusters.setdefault(bucket, {"name": bucket, "count": 0, "avg_confidence": 0, "examples": []})
        semantic_clusters[bucket]["count"] += 1
        semantic_clusters[bucket]["avg_confidence"] += rel.confidence or 0
        if len(semantic_clusters[bucket]["examples"]) < 4:
            semantic_clusters[bucket]["examples"].append({"source_id": rel.source_id, "target_id": rel.target_id, "confidence": rel.confidence})
    for value in semantic_clusters.values():
        value["avg_confidence"] = round(value["avg_confidence"] / value["count"], 3) if value["count"] else 0

    return {
        "treemap": treemap,
        "sankey": {"nodes": sankey_nodes, "links": sankey_links},
        "semantic_clusters": list(semantic_clusters.values()),
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "osint-chile-graph-api", "ai_provider": settings.ai_provider, "ollama_base_url": settings.ollama_base_url}


@app.get("/api/transforms")
def list_transforms():
    return transform_catalog()


@app.get("/api/prompts")
def list_prompts():
    return load_prompts()


@app.put("/api/prompts/{prompt_id}")
def update_prompt(prompt_id: str, payload: PromptUpdate):
    if prompt_id != payload.prompt_id:
        raise HTTPException(status_code=400, detail="prompt_id de ruta y payload no coinciden")
    return save_prompt(payload.prompt_id, payload.system, payload.user_template, payload.provider, payload.model)


@app.get("/api/frameworks")
def list_framework_adapters():
    return framework_catalog()


@app.get("/api/investigations")
def list_investigations():
    with session_scope() as session:
        rows = session.scalars(select(Investigation).order_by(Investigation.created_at.desc())).all()
        return [{"id": row.id, "title": row.title, "objective": row.objective, "status": row.status, "created_at": row.created_at.isoformat()} for row in rows]


@app.post("/api/investigations")
def create_investigation(payload: InvestigationCreate):
    investigation = Investigation(id=str(uuid4()), title=payload.title, objective=payload.objective)
    with session_scope() as session:
        session.add(investigation)
    return {"id": investigation.id, "title": investigation.title, "objective": investigation.objective, "status": investigation.status}


@app.post("/api/seeds")
def add_seed(payload: SeedRequest):
    investigation_id = payload.investigation_id or "demo"
    entity_id = make_id(payload.input_type, f"{investigation_id}:{payload.value}")
    entity = Entity(id=entity_id, investigation_id=investigation_id, type="Seed", label=payload.value, value=payload.value, properties={"input_type": payload.input_type}, confidence=1.0)
    with session_scope() as session:
        session.merge(entity)
    sync_entity_to_neo4j({"id": entity_id, "type": "Seed", "label": payload.value, "value": payload.value, "confidence": 1.0})
    return {"id": entity_id, "type": "Seed", "label": payload.value, "value": payload.value, "properties": {"input_type": payload.input_type}, "confidence": 1.0}


@app.post("/api/transforms/run")
def run_transform(payload: TransformRunRequest):
    if not any(t.id == payload.transform_id for t in TRANSFORMS):
        raise HTTPException(status_code=404, detail="Transform no encontrado")
    if payload.transform_id.startswith("ai."):
        raise HTTPException(status_code=400, detail="Use /api/ai/run para transforms de IA")
    try:
        output = execute_transform(payload.transform_id, payload.input_type, payload.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    run_id = str(uuid4())
    created_entities = []
    created_edges = []
    with session_scope() as session:
        session.add(TransformRun(id=run_id, investigation_id=payload.investigation_id, transform_id=payload.transform_id, input_type=payload.input_type, input_value=payload.value, output=output))
        seed_id = make_id(payload.input_type, f"{payload.investigation_id}:{payload.value}")
        if not session.get(Entity, seed_id):
            session.add(Entity(id=seed_id, investigation_id=payload.investigation_id, type="Seed", label=payload.value, value=payload.value, properties={"input_type": payload.input_type}, confidence=1.0))
        persisted_evidence: list[dict] = []
        for item in output.get("entities", []):
            entity_id = make_id(item["type"], f"{payload.investigation_id}:{item.get('value') or item['label']}")
            properties = item.get("properties", {}) or {}
            evidence_kind = properties.get("evidence_kind", "local_algorithm")
            entity = Entity(id=entity_id, investigation_id=payload.investigation_id, type=item["type"], label=item["label"], value=item.get("value", ""), properties=properties, confidence=item.get("confidence", 0.8))
            session.merge(entity)
            edge_id = make_id("edge", f"{seed_id}:{entity_id}:{payload.transform_id}")
            edge = Relationship(id=edge_id, investigation_id=payload.investigation_id, source_id=seed_id, target_id=entity_id, type="FOUND_BY", properties={"transform_id": payload.transform_id, "run_id": run_id, "evidence_kind": evidence_kind}, confidence=entity.confidence)
            session.merge(edge)
            if evidence_kind == "verified_evidence":
                evidence = Evidence(
                    id=make_id("evidence", f"{run_id}:{entity_id}:{properties.get('source_url', '')}"),
                    investigation_id=payload.investigation_id,
                    source_name=properties.get("source_name") or properties.get("connector") or payload.transform_id,
                    source_url=properties.get("source_url", ""),
                    extract=properties.get("extract") or f"Resultado público verificado: {entity.label}",
                    confidence=entity.confidence,
                    properties={**properties, "transform_id": payload.transform_id, "run_id": run_id, "entity_id": entity_id},
                )
                session.merge(evidence)
                persisted_evidence.append({"id": evidence.id, "source_name": evidence.source_name, "source_url": evidence.source_url})
            elif evidence_kind == "local_algorithm":
                evidence = Evidence(
                    id=make_id("evidence", f"{run_id}:{entity_id}:local_algorithm"),
                    investigation_id=payload.investigation_id,
                    source_name=f"local_algorithm:{payload.transform_id}",
                    source_url="",
                    extract=properties.get("risk_note") or f"Dato derivado por algoritmo local desde la semilla; no constituye OSINT externo verificado: {entity.label}",
                    confidence=entity.confidence,
                    properties={**properties, "transform_id": payload.transform_id, "run_id": run_id, "entity_id": entity_id},
                )
                session.merge(evidence)
                persisted_evidence.append({"id": evidence.id, "source_name": evidence.source_name, "source_url": evidence.source_url})
            created_entities.append({"id": entity_id, "type": entity.type, "label": entity.label, "value": entity.value, "properties": entity.properties, "confidence": entity.confidence})
            created_edges.append({"id": edge_id, "source_id": seed_id, "target_id": entity_id, "type": "FOUND_BY", "confidence": entity.confidence})
        for evidence_item in output.get("evidence", []):
            properties = evidence_item.get("properties", {}) or {}
            evidence = Evidence(
                id=make_id("evidence", f"{run_id}:{evidence_item.get('source_name', '')}:{evidence_item.get('source_url', '')}:{evidence_item.get('extract', '')[:80]}"),
                investigation_id=payload.investigation_id,
                source_name=evidence_item.get("source_name", payload.transform_id),
                source_url=evidence_item.get("source_url", ""),
                extract=evidence_item.get("extract", "Evidencia pública registrada por conector."),
                confidence=evidence_item.get("confidence", 0.65),
                properties={**properties, "transform_id": payload.transform_id, "run_id": run_id},
            )
            session.merge(evidence)
            persisted_evidence.append({"id": evidence.id, "source_name": evidence.source_name, "source_url": evidence.source_url})
        # Los estados de fuente son telemetría operacional, no evidencia OSINT.
        # Se conservan dentro del TransformRun para explicar bloqueos, ausencia de API o pasos HITL,
        # pero no se persisten como Evidence ni se cuentan como hallazgos útiles del objetivo.
        output["persisted_evidence"] = persisted_evidence
        for task in output.get("human_tasks", []):
            task_id = make_id("HumanTask", f"{payload.investigation_id}:{task['source']}:{payload.value}")
            entity = Entity(id=task_id, investigation_id=payload.investigation_id, type="HumanTask", label=f"HITL: {task['source']}", value=payload.value, properties=task, confidence=0.6)
            session.merge(entity)
            edge_id = make_id("edge", f"{seed_id}:{task_id}:requires-human")
            edge = Relationship(id=edge_id, investigation_id=payload.investigation_id, source_id=seed_id, target_id=task_id, type="REQUIRES_HUMAN", properties={"transform_id": payload.transform_id, "run_id": run_id}, confidence=0.6)
            session.merge(edge)
            created_entities.append({"id": task_id, "type": "HumanTask", "label": entity.label, "value": payload.value, "properties": task, "confidence": 0.6})
            created_edges.append({"id": edge_id, "source_id": seed_id, "target_id": task_id, "type": "REQUIRES_HUMAN", "confidence": 0.6})

    for entity in created_entities:
        sync_entity_to_neo4j(entity)
    for edge in created_edges:
        sync_relationship_to_neo4j(edge)
    return {"run_id": run_id, "output": output, "created_entities": created_entities, "created_edges": created_edges}


@app.get("/api/investigations/{investigation_id}/findings")
def get_investigation_findings(investigation_id: str):
    with session_scope() as session:
        investigation = session.get(Investigation, investigation_id)
        if not investigation:
            raise HTTPException(status_code=404, detail="Investigación no encontrada")
        entities = session.scalars(select(Entity).where(Entity.investigation_id == investigation_id).order_by(Entity.type.asc(), Entity.label.asc())).all()
        relationships = session.scalars(select(Relationship).where(Relationship.investigation_id == investigation_id)).all()
        evidence_rows_raw = session.scalars(select(Evidence).where(Evidence.investigation_id == investigation_id).order_by(Evidence.created_at.desc())).all()
        runs = session.scalars(select(TransformRun).where(TransformRun.investigation_id == investigation_id).order_by(TransformRun.created_at.desc())).all()
        evidence_rows = [evidence for evidence in evidence_rows_raw if not _is_source_status(evidence)]
        verified_evidence_rows = [evidence for evidence in evidence_rows if _is_verified_evidence(evidence)]
        source_statuses = _source_statuses_from_runs(runs)

        entity_lookup = {entity.id: entity for entity in entities}
        human_tasks = [entity for entity in entities if entity.type == "HumanTask"]
        evidence_by_source: dict[str, int] = {}
        for evidence in verified_evidence_rows:
            evidence_by_source.setdefault(evidence.source_name, 0)
            evidence_by_source[evidence.source_name] += 1

        entity_types: dict[str, int] = {}
        confidence_sum = 0.0
        for entity in entities:
            entity_types[entity.type] = entity_types.get(entity.type, 0) + 1
            confidence_sum += entity.confidence or 0

        relationship_items = [_relationship_payload(rel, entity_lookup) for rel in relationships]
        evidence_items = [_evidence_payload(evidence) for evidence in verified_evidence_rows]

        run_items = [
            {
                "id": run.id,
                "transform_id": run.transform_id,
                "input_type": run.input_type,
                "input_value": run.input_value,
                "created_at": run.created_at.isoformat(),
                "output_summary": {
                    "entities": len((run.output or {}).get("entities", [])),
                    "human_tasks": len((run.output or {}).get("human_tasks", [])),
                    "relationships": len((run.output or {}).get("relationships", [])),
                },
            }
            for run in runs
        ]

        timeline = []
        for evidence in verified_evidence_rows:
            timeline.append({"at": evidence.created_at.isoformat(), "kind": "verified_evidence", "title": evidence.source_name, "detail": evidence.extract, "confidence": evidence.confidence})
        for status in source_statuses:
            timeline.append({"at": status.get("created_at", ""), "kind": "source_status", "title": status.get("source", "Fuente"), "detail": f"{status.get('status', 'estado')} · {status.get('reason', '')}", "confidence": 0.0})
        for run in runs:
            timeline.append({"at": run.created_at.isoformat(), "kind": "transform", "title": run.transform_id, "detail": f"{run.input_type}={run.input_value}", "confidence": 1.0})
        timeline = sorted(timeline, key=lambda item: item["at"], reverse=True)[:120]

        entity_profiles = []
        for entity in entities:
            entity_evidence_rows = _find_related_evidence(entity, verified_evidence_rows, relationships)
            entity_evidence = [_evidence_payload(evidence) for evidence in entity_evidence_rows]
            direct_relationships = [rel for rel in relationship_items if rel["source_id"] == entity.id or rel["target_id"] == entity.id]
            task_count = len([rel for rel in direct_relationships if rel["type"] == "REQUIRES_HUMAN"])
            entity_profiles.append({
                "entity": _entity_payload(entity),
                "analysis": _describe_entity(entity, direct_relationships, entity_evidence, task_count),
                "relationships": direct_relationships,
                "evidence": entity_evidence,
                "stats": {
                    "relationships": len(direct_relationships),
                    "evidence": len(entity_evidence),
                    "human_tasks": task_count if entity.type != "HumanTask" else 1,
                    "confidence": entity.confidence,
                },
            })

        task_items = []
        for task in human_tasks:
            props = task.properties or {}
            task_items.append({
                "id": task.id,
                "label": task.label,
                "value": task.value,
                "properties": {**props, "search_url": props.get("search_url") or _build_search_url(props.get("source", task.label), task.value, props.get("purpose", ""))},
                "confidence": task.confidence,
                "status": props.get("status", "pending_manual_review"),
            })

        return {
            "investigation": {"id": investigation.id, "title": investigation.title, "objective": investigation.objective, "status": investigation.status, "created_at": investigation.created_at.isoformat()},
            "summary": {
                "entities": len(entities),
                "relationships": len(relationships),
                "evidence": len(verified_evidence_rows),
                "evidence_total_records": len(evidence_rows),
                "source_statuses": len(source_statuses),
                "human_tasks": len(human_tasks),
                "pending_human_tasks": len([task for task in task_items if task["status"] != "completed_by_operator"]),
                "transform_runs": len(runs),
                "average_confidence": round(confidence_sum / len(entities), 3) if entities else 0,
                "entity_types": entity_types,
                "evidence_by_source": evidence_by_source,
            },
            "analysis": _build_dossier_analysis(investigation, entities, relationships, evidence_rows, runs),
            "entities": [_entity_payload(n) for n in entities],
            "entity_profiles": entity_profiles,
            "relationships": relationship_items,
            "evidence": evidence_items,
            "human_tasks": task_items,
            "runs": run_items,
            "timeline": timeline,
            "source_statuses": source_statuses,
            "visualizations": _build_visualizations(entities, relationships, runs, verified_evidence_rows),
        }


@app.post("/api/human-tasks/{task_id}/complete")
def complete_human_task(task_id: str, payload: HumanTaskCompletionRequest):
    with session_scope() as session:
        task = session.get(Entity, task_id)
        if not task or task.type != "HumanTask":
            raise HTTPException(status_code=404, detail="Tarea HITL no encontrada")
        if task.investigation_id != payload.investigation_id:
            raise HTTPException(status_code=400, detail="La tarea no pertenece a la investigación indicada")

        props = task.properties or {}
        props = {**props, "status": "completed_by_operator", "operator_status": payload.status, "operator_notes": payload.notes, "last_source_url": payload.source_url}
        task.properties = props
        task.confidence = max(task.confidence or 0.6, payload.confidence)
        session.merge(task)

        evidence_id = make_id("evidence", f"{task_id}:{payload.source_name}:{payload.source_url}:{payload.extract[:80]}")
        evidence = Evidence(
            id=evidence_id,
            investigation_id=payload.investigation_id,
            source_name=payload.source_name,
            source_url=payload.source_url,
            extract=payload.extract,
            confidence=payload.confidence,
            properties={
                "human_task_completed": True,
                "task_id": task_id,
                "entity_id": payload.task_entity_id or task_id,
                "status": payload.status,
                "notes": payload.notes,
                "related_entity_ids": [task_id],
            },
        )
        session.merge(evidence)

        created_entities = []
        created_relationships = []
        for observed in payload.observed_entities:
            label = str(observed.get("label") or observed.get("value") or "").strip()
            if not label:
                continue
            entity_type = str(observed.get("type") or "ObservedEntity")[:64]
            entity_value = str(observed.get("value") or label)
            entity_id = make_id(entity_type, f"{payload.investigation_id}:{entity_value}")
            observed_props = dict(observed.get("properties") or {})
            observed_props.update({"from_human_task": task_id, "source_name": payload.source_name, "source_url": payload.source_url})
            entity = Entity(id=entity_id, investigation_id=payload.investigation_id, type=entity_type, label=label, value=entity_value, properties=observed_props, confidence=float(observed.get("confidence") or payload.confidence))
            session.merge(entity)
            rel_id = make_id("edge", f"{task_id}:{entity_id}:confirmed-by-human")
            rel = Relationship(id=rel_id, investigation_id=payload.investigation_id, source_id=task_id, target_id=entity_id, type="CONFIRMED_BY_HUMAN", properties={"evidence_id": evidence_id, "source_name": payload.source_name}, confidence=entity.confidence)
            session.merge(rel)
            created_entities.append(_entity_payload(entity))
            created_relationships.append(_relationship_payload(rel, {task_id: task, entity_id: entity}))

        rel_evidence_id = make_id("edge", f"{task_id}:{evidence_id}:evidence")
        session.merge(Relationship(id=rel_evidence_id, investigation_id=payload.investigation_id, source_id=task_id, target_id=task_id, type="EVIDENCE_CAPTURED", properties={"evidence_id": evidence_id, "source_name": payload.source_name}, confidence=payload.confidence))

    for entity in created_entities:
        sync_entity_to_neo4j(entity)
    for rel in created_relationships:
        sync_relationship_to_neo4j({"id": rel["id"], "source_id": rel["source_id"], "target_id": rel["target_id"], "type": rel["type"], "confidence": rel["confidence"]})

    return {"status": "saved", "task_id": task_id, "evidence_id": evidence_id, "created_entities": created_entities, "created_relationships": created_relationships}


@app.get("/api/graph/{investigation_id}", response_model=GraphOut)
def get_graph(investigation_id: str):
    with session_scope() as session:
        nodes = session.scalars(select(Entity).where(Entity.investigation_id == investigation_id)).all()
        edges = session.scalars(select(Relationship).where(Relationship.investigation_id == investigation_id)).all()
        return {
            "nodes": [{"id": n.id, "type": n.type, "label": n.label, "value": n.value, "properties": n.properties or {}, "confidence": n.confidence} for n in nodes],
            "edges": [{"id": e.id, "source": e.source_id, "target": e.target_id, "type": e.type, "properties": e.properties or {}, "confidence": e.confidence} for e in edges],
        }


@app.post("/api/ai/run")
async def ai_run(payload: AIRequest):
    try:
        return await run_ai_prompt(payload.prompt_id, payload.variables, payload.provider, payload.model)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
