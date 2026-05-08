from __future__ import annotations

import json
import time

from app.transforms import execute_transform

CASES = [
    ("cl.rut.dorks", "rut", "76.972.430-9"),
    ("cl.rut.dorks", "rut", "60.803.000-K"),
    ("cl.phone.dorks", "phone", "+56 9 8765 4321"),
    ("cl.plate.dorks", "plate", "ABCD12"),
]

for transform_id, input_type, value in CASES:
    started = time.time()
    print(f"CASE_START {transform_id} {value}", flush=True)
    output = execute_transform(transform_id, input_type, value)
    elapsed = time.time() - started
    evidence = output.get("evidence", [])
    entities = output.get("entities", [])
    statuses = output.get("source_statuses", [])
    human = output.get("human_tasks", [])
    print(f"CASE_DONE {transform_id} {value} elapsed={elapsed:.2f}s", flush=True)
    print(f"COUNTS evidence={len(evidence)} entities={len(entities)} source_statuses={len(statuses)} human_tasks={len(human)}", flush=True)
    for item in evidence[:3]:
        print("EVIDENCE", item.get("source_name"), item.get("extract", "")[:240].replace("\n", " "), flush=True)
    for item in statuses[:5]:
        print("STATUS", item.get("source"), item.get("status"), item.get("message", "")[:200].replace("\n", " "), flush=True)
    for item in human[:3]:
        print("HITL", item.get("source"), item.get("reason", "")[:160].replace("\n", " "), flush=True)
    print("SOURCE_STATUS_JSON", json.dumps(statuses[:2], ensure_ascii=False), flush=True)
    print("---", flush=True)
