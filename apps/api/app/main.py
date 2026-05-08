from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from .ai import load_prompts, run_ai_prompt, save_prompt
from .config import get_settings
from .db import Entity, Evidence, Investigation, Relationship, TransformRun, init_db, session_scope
from .graph import sync_entity_to_neo4j, sync_relationship_to_neo4j
from .schemas import AIRequest, GraphOut, InvestigationCreate, PromptUpdate, SeedRequest, TransformRunRequest
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
        for item in output.get("entities", []):
            entity_id = make_id(item["type"], f"{payload.investigation_id}:{item.get('value') or item['label']}")
            entity = Entity(id=entity_id, investigation_id=payload.investigation_id, type=item["type"], label=item["label"], value=item.get("value", ""), properties=item.get("properties", {}), confidence=item.get("confidence", 0.8))
            session.merge(entity)
            edge_id = make_id("edge", f"{seed_id}:{entity_id}:{payload.transform_id}")
            edge = Relationship(id=edge_id, investigation_id=payload.investigation_id, source_id=seed_id, target_id=entity_id, type="FOUND_BY", properties={"transform_id": payload.transform_id, "run_id": run_id}, confidence=entity.confidence)
            session.merge(edge)
            session.add(Evidence(id=make_id("evidence", f"{run_id}:{entity_id}"), investigation_id=payload.investigation_id, source_name=payload.transform_id, source_url="", extract=f"Transform {payload.transform_id} produjo {entity.label}", confidence=entity.confidence, properties=item.get("properties", {})))
            created_entities.append({"id": entity_id, "type": entity.type, "label": entity.label, "value": entity.value, "properties": entity.properties, "confidence": entity.confidence})
            created_edges.append({"id": edge_id, "source_id": seed_id, "target_id": entity_id, "type": "FOUND_BY", "confidence": entity.confidence})
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
