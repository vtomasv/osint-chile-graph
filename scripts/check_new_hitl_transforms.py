from app.transforms import execute_transform, transform_catalog

CASES = [
    ("cl.rut.diario_oficial.human", "rut", "60.803.000-K"),
    ("cl.rut.poder_judicial.human", "rut", "12.345.678-5"),
    ("cl.phone.caller_id.human", "phone", "+56 9 8765 4321"),
    ("cl.phone.denuncias_sernac_subtel.human", "phone", "+56 9 8765 4321"),
    ("cl.plate.registro_civil.human", "plate", "ABCD12"),
    ("cl.plate.sernac.human", "plate", "ABCD12"),
    ("cl.email.breach_check.human", "email", "persona@example.cl"),
    ("cl.name.linkedin.human", "name", "Juan Perez"),
]

catalog_ids = {item["id"] for item in transform_catalog()}
missing = [case[0] for case in CASES if case[0] not in catalog_ids]
if missing:
    raise SystemExit(f"Missing catalog ids: {missing}")

for transform_id, input_type, value in CASES:
    output = execute_transform(transform_id, input_type, value)
    evidence = output.get("evidence", [])
    entities = output.get("entities", [])
    tasks = output.get("human_tasks", [])
    print(f"{transform_id}: evidence={len(evidence)} entities={len(entities)} human_tasks={len(tasks)}")
    if evidence or entities:
        raise SystemExit(f"{transform_id} should not create factual evidence/entities without operator capture")
    if not tasks:
        raise SystemExit(f"{transform_id} did not create a HITL task")
print("new HITL transforms OK")
