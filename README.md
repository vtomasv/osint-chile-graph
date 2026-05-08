# OSINT Chile Graph

**OSINT Chile Graph** es un MVP local de plataforma OSINT para Chile, inspirado conceptualmente en Maltego y deQuiénes, con grafo investigativo, transforms auditables, evidencias, tareas **human-in-the-loop**, integración con IA local vía Ollama y APIs externas configurables.

El proyecto está pensado para ejecutarse en una máquina Apple Silicon, como un **Apple M3 Max**, mediante Docker Compose. Ollama corre por defecto en la máquina local del usuario y la API accede a él desde los contenedores usando `host.docker.internal:11434`.

## Alcance responsable

La plataforma implementa conectores automáticos solo para fuentes públicas, pasivas o autorizadas. No implementa evasión de CAPTCHA, bypass anti-bot, recolección no pública, fuerza bruta ni automatización contra portales restringidos. Las fuentes que requieran login, CAPTCHA, autorización, revisión legal o validación manual se modelan como tareas **human-in-the-loop**.

| Tipo de fuente | Estado MVP |
|---|---|
| Algoritmos locales de normalización | Automático |
| Dorks y fuentes públicas | Generación de consulta y ejecución manual/API autorizada |
| Portales con login/CAPTCHA | Human-in-the-loop |
| Datos no públicos o filtrados | No soportado |
| Escaneo activo ofensivo | No soportado por defecto |

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | React, TypeScript, React Flow, Tailwind, shadcn/ui |
| API | FastAPI |
| Base relacional | PostgreSQL |
| Grafo | Neo4j |
| Cache/estado | Redis |
| IA local | Ollama externo al compose |
| IA externa | API compatible con OpenAI mediante variables de entorno |
| Orquestación | Docker Compose multi-arch/Apple Silicon |

## Inicio rápido

```bash
git clone https://github.com/vtomasv/osint-chile-graph.git
cd osint-chile-graph
cp .env.example .env
make dev
```

Luego abrir:

| Servicio | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000/health |
| Documentación API | http://localhost:8000/docs |
| Neo4j Browser | http://localhost:7474 |

## Ollama local

Instala y ejecuta Ollama en tu Mac. Por ejemplo:

```bash
ollama serve
ollama pull llama3.1:8b
```

La variable `OLLAMA_BASE_URL` por defecto es `http://host.docker.internal:11434` para que los contenedores accedan al Ollama del host macOS.

## Transforms incluidos

| Transform | Descripción | Modo |
|---|---|---|
| `cl.rut.normalize` | Valida dígito verificador y normaliza RUT chileno | Automático |
| `cl.email.analyze` | Analiza email, dominio y TLD `.cl` | Automático |
| `cl.phone.normalize` | Normaliza número chileno y crea tarea de enriquecimiento autorizado | Automático + HITL |
| `cl.plate.normalize` | Valida formatos frecuentes de patente chilena | Automático |
| `cl.dork.generate` | Genera consultas para fuentes públicas y documentos | Automático |
| `cl.source.diario_oficial.human` | Prepara búsqueda manual en Diario Oficial | HITL |
| `cl.source.registro_empresas.human` | Prepara consulta manual societaria | HITL |
| `ai.extract_entities` | Punto de entrada para extracción de entidades con IA | IA configurable |

## Prompts configurables

Los prompts de sistema viven en `prompts/system_prompts.yaml`. El MVP incluye prompts para extracción de entidades, síntesis semántica, análisis de vínculos, clasificación de fuentes y planificación de investigación profunda. También existe `PUT /api/prompts/{prompt_id}` para editar prompts desde una futura UI o un cliente autorizado local. Cada ejecución de IA acepta `provider` y `model` para seleccionar Ollama o una API externa compatible.

## Referencias arquitectónicas

El diseño incorpora patrones de PageIndex, graphify, ai-knowledge-graph y local-deep-research como adaptadores o módulos conceptuales. Los detalles están documentados en `docs/architecture.md`.

## Desarrollo

```bash
# Backend tests
cd apps/api
python -m pytest -q

# Frontend typecheck
pnpm check
```

## Licencia

MIT. Este repositorio no copia código de herramientas con licencias incompatibles; usa referencias conceptuales documentadas y conectores propios.
