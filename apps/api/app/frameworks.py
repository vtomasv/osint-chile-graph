from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class FrameworkAdapter:
    id: str
    name: str
    upstream_url: str
    role: str
    integration_status: str
    local_mount: str
    notes: str


ADAPTERS = [
    FrameworkAdapter(
        id="pageindex",
        name="PageIndex",
        upstream_url="https://github.com/VectifyAI/PageIndex",
        role="Indexación de páginas y documentos recolectados para búsqueda semántica y recuperación.",
        integration_status="adapter_placeholder",
        local_mount="integrations/pageindex",
        notes="El MVP define el punto de extensión; la ejecución debe instalarse como servicio autorizado o worker local.",
    ),
    FrameworkAdapter(
        id="graphify",
        name="graphify",
        upstream_url="https://github.com/safishamsi/graphify",
        role="Conversión de contenido y repositorios en grafos de conocimiento.",
        integration_status="adapter_placeholder",
        local_mount="integrations/graphify",
        notes="Se mapeará a entidades/relaciones del esquema interno cuando se incorpore como dependencia.",
    ),
    FrameworkAdapter(
        id="ai-knowledge-graph",
        name="ai-knowledge-graph",
        upstream_url="https://github.com/robert-mcdermott/ai-knowledge-graph",
        role="Extracción de triples y relaciones asistida por LLM.",
        integration_status="adapter_placeholder",
        local_mount="integrations/ai-knowledge-graph",
        notes="Debe producir relaciones etiquetadas como confirmadas o inferidas según evidencia.",
    ),
    FrameworkAdapter(
        id="local-deep-research",
        name="local-deep-research",
        upstream_url="https://github.com/LearningCircuit/local-deep-research",
        role="Planificación y ejecución de investigaciones profundas locales con modelos configurables.",
        integration_status="adapter_placeholder",
        local_mount="integrations/local-deep-research",
        notes="Se limita a fuentes públicas/autorizadas o tareas human-in-the-loop.",
    ),
]


def framework_catalog() -> list[dict[str, Any]]:
    return [asdict(adapter) for adapter in ADAPTERS]
