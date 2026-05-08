from typing import Any
from neo4j import GraphDatabase
from .config import get_settings


def sync_entity_to_neo4j(entity: dict[str, Any]) -> None:
    settings = get_settings()
    try:
        driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
        with driver.session() as session:
            session.run(
                "MERGE (e:Entity {id: $id}) SET e.type=$type, e.label=$label, e.value=$value, e.confidence=$confidence",
                id=entity["id"], type=entity["type"], label=entity["label"], value=entity.get("value", ""), confidence=entity.get("confidence", 1.0),
            )
        driver.close()
    except Exception:
        # Neo4j es deseable pero no debe bloquear el MVP si el servicio aún está iniciando.
        return


def sync_relationship_to_neo4j(edge: dict[str, Any]) -> None:
    settings = get_settings()
    try:
        driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
        with driver.session() as session:
            session.run(
                "MATCH (a:Entity {id: $source_id}) MATCH (b:Entity {id: $target_id}) MERGE (a)-[r:RELATED {id: $id}]->(b) SET r.type=$type, r.confidence=$confidence",
                id=edge["id"], source_id=edge["source_id"], target_id=edge["target_id"], type=edge["type"], confidence=edge.get("confidence", 0.7),
            )
        driver.close()
    except Exception:
        return
