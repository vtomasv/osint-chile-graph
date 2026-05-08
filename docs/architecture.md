# Arquitectura del MVP OSINT Chile

Autor: **Manus AI**  
Fecha: 2026-05-07

## Propósito

El MVP propone una plataforma local de investigación OSINT para Chile, inspirada conceptualmente en Maltego y deQuiénes, pero diseñada como un sistema propio, modular y extensible. El flujo principal parte de entidades semilla, tales como **RUT**, **correo .cl**, **patente chilena**, **teléfono chileno**, **dominio**, **nombre de persona** o **empresa**, y expande hallazgos mediante transforms auditables. Cada hallazgo conserva fuente, evidencia, confianza, timestamp y trazabilidad.

La solución se ejecutará mediante **Docker Compose** en Apple Silicon, usando **FastAPI**, **PostgreSQL**, **Neo4j**, **Redis**, frontend **React/TypeScript**, visualización con **React Flow** y/o **Cytoscape**, y una capa de IA que usa **Ollama local** por defecto mediante endpoint configurable. Las APIs externas se configuran por variables de entorno y permiten seleccionar modelo y prompts.

## Límite de cumplimiento y seguridad

La plataforma no implementará evasión de CAPTCHA, elusión de controles anti-bot, bypass de restricciones, fuerza bruta, scraping de información no pública ni automatización de portales cuyo acceso requiera autorización no disponible. En su lugar, las operaciones que requieran login, CAPTCHA, consentimiento, validación manual o interpretación jurídica se modelan como tareas **human-in-the-loop**.

> Una tarea human-in-the-loop es una unidad de investigación que el sistema puede preparar, documentar y auditar, pero cuya ejecución requiere intervención humana autorizada. El sistema registra la URL, la razón de intervención, los campos esperados, instrucciones y evidencia ingresada por el operador.

| Categoría de fuente | Automatización permitida en el MVP | Ejecución | Ejemplos |
|---|---:|---|---|
| Fuente pública pasiva | Sí | Backend transform | Dorks seguros, datasets abiertos, páginas públicas, documentos públicos |
| Fuente con API autorizada | Sí | Backend transform con credenciales | APIs configuradas por variables de entorno |
| Fuente con login o CAPTCHA | No automática | Human-in-the-loop | Portales estatales con validación, servicios con sesión |
| Fuente con restricciones anti-bot | No automática | Placeholder/HITL | Sitios con controles técnicos o ToS restrictivos |
| Fuente no pública | No soportada | Bloqueada | Datos privados, filtrados o sin base legal |
| Escaneo activo ofensivo | No soportado por defecto | Bloqueado o solo laboratorio autorizado futuro | nmap, fuzzing, explotación, fuerza bruta |

## Componentes principales

| Componente | Tecnología | Responsabilidad |
|---|---|---|
| API | FastAPI | Orquestar investigaciones, transforms, evidencias, IA y grafo |
| Base relacional | PostgreSQL | Investigaciones, tareas, evidencias, prompts, conectores, usuarios futuros |
| Grafo | Neo4j | Entidades, relaciones, caminos, expansión y análisis topológico |
| Cache/cola ligera | Redis | Jobs, estados, locks y cache de resultados |
| Frontend | React/TypeScript + Bulma | Interfaz de investigación, grafo, configuración y reportes |
| Visualización | React Flow inicialmente; Cytoscape preparado | Exploración estilo Maltego |
| IA local | Ollama externo a Docker por defecto | Síntesis, extracción SPO, normalización, hipótesis |
| IA externa | OpenAI-compatible API | Proveedor opcional configurable |
| Búsqueda | Plantillas dork y conectores | Generación de consultas seguras y registro de fuentes |
| Human-in-the-loop | Workflow de tareas | Preparar acciones manuales y registrar resultados autorizados |

## Modelo conceptual de dominio

| Entidad | Campos mínimos | Uso |
|---|---|---|
| `Person` | nombre, alias, identificadores, país | Nodo central de investigación personal |
| `Company` | razón social, RUT, giro, dominio | Investigación corporativa |
| `Identifier` | tipo, valor normalizado, país | RUT, email, teléfono, patente, dominio |
| `Vehicle` | patente, tipo, marca opcional | Búsqueda vehicular autorizada |
| `Phone` | número E.164, país, carrier inferido | Enriquecimiento telefónico |
| `Email` | dirección, dominio, TLD | Dorks y vínculos con dominios |
| `Document` | título, URL, hash, MIME, texto extraído | Evidencia documental |
| `Source` | nombre, URL, tipo, política | Fuente OSINT |
| `Evidence` | extracto, URL, hash, confianza | Prueba trazable de hallazgo |
| `Investigation` | nombre, objetivo, estado | Caso de investigación |
| `HumanTask` | URL, instrucciones, estado, resultado | Tareas asistidas |

## Relaciones de grafo

| Relación | Origen | Destino | Semántica |
|---|---|---|---|
| `HAS_IDENTIFIER` | Person/Company/Vehicle | Identifier | Vincula una entidad con un identificador |
| `MENTIONED_IN` | Entity | Document/Evidence | Evidencia textual o documental |
| `ASSOCIATED_WITH` | Entity | Entity | Asociación inferida o explícita |
| `OWNS` | Person/Company | Company/Asset | Propiedad o participación declarada |
| `REPRESENTS` | Person | Company | Representación legal o societaria |
| `REGISTERED_TO` | Domain/Phone/Vehicle | Entity | Registro atribuido, si fuente lo permite |
| `FOUND_BY` | Entity/Evidence | TransformRun | Trazabilidad del transform |
| `REQUIRES_HUMAN` | TransformRun | HumanTask | Bloqueo por login/CAPTCHA/autorización |
| `SIMILAR_TO` | Entity | Entity | Similaridad semántica calculada por IA |
| `INFERRED_LINK` | Entity | Entity | Hipótesis generada por IA, no hecho confirmado |

## Contrato de transform

Los transforms se definen como unidades idempotentes y auditables. Cada transform declara entradas, salidas, política de ejecución, nivel de riesgo, fuentes y si puede ejecutarse automáticamente.

```json
{
  "id": "cl.rut.normalize",
  "name": "Normalizar y validar RUT chileno",
  "input_entity_types": ["Identifier"],
  "output_entity_types": ["Identifier"],
  "execution_mode": "automatic",
  "risk_level": "low",
  "requires_human": false,
  "source_policy": "local_algorithm",
  "prompt_ids": [],
  "rate_limit": null
}
```

## Transforms iniciales del MVP

| Transform | Entrada | Salida | Modo | Descripción |
|---|---|---|---|---|
| `cl.rut.normalize` | RUT | RUT normalizado | Automático | Valida dígito verificador y formato |
| `cl.email.analyze` | Email | Dominio, TLD, hipótesis país | Automático | Analiza email .cl y dominio asociado |
| `cl.phone.normalize` | Teléfono | E.164, país, carrier placeholder | Automático | Normaliza número chileno y prepara enriquecimiento |
| `cl.plate.normalize` | Patente | Patente normalizada | Automático | Valida formato patente chilena moderna/antigua |
| `cl.dork.generate` | Persona/Empresa/RUT/Email | DorkQuery | Automático | Genera consultas seguras y auditables |
| `cl.source.diario_oficial.human` | Nombre/RUT/Empresa | HumanTask | HITL | Prepara búsqueda manual en Diario Oficial |
| `cl.source.registro_empresas.human` | RUT/Empresa | HumanTask | HITL | Prepara consulta manual autorizada |
| `ai.extract_entities` | Texto/Evidencia | Entidades y relaciones | Automático | Extrae tripletas e identidades usando prompts configurables |
| `ai.semantic_summary` | Evidencias | Síntesis | Automático | Resume hallazgos con citas internas |
| `ai.link_analysis` | Grafo | Hipótesis | Automático | Sugiere cruces y vínculos probables marcados como inferidos |

## Integración de frameworks obligatorios

| Framework | Integración en MVP | Implementación inicial |
|---|---|---|
| PageIndex | Indexación razonada de documentos largos | Adaptador opcional `PageIndexAdapter`, configuración y placeholder funcional |
| graphify | Generar/importar grafos de conocimiento desde carpetas y documentos | Adaptador `GraphifyAdapter`, exportación futura a Neo4j |
| ai-knowledge-graph | Extracción SPO y visualización de relaciones | Implementación propia ligera compatible con Ollama/OpenAI y prompts configurables |
| local-deep-research | Investigación profunda con fuentes y citas | Módulo `deep_research` con estado, evidencias y punto de integración futuro |
| SpiderFoot/Sublist3r | Inspiración de conectores y enumeración pasiva | Solo módulos pasivos/autorizados; escaneo activo bloqueado |
| Scrapling | Scraping estructurado | Solo modo estándar respetuoso; stealth/anti-bot excluido |

## Configuración de IA y prompts

Los prompts se almacenan inicialmente como archivos YAML editables y además se exponen por API. El usuario podrá configurar el proveedor, endpoint, modelo, temperatura y prompts de sistema por tarea.

| Prompt | Uso |
|---|---|
| `entity_extraction` | Extraer entidades, identificadores y relaciones desde texto |
| `semantic_summary` | Sintetizar hallazgos con distinción entre hechos e inferencias |
| `link_analysis` | Proponer cruces de información y caminos relevantes en el grafo |
| `source_triage` | Clasificar fuentes por utilidad, riesgo y necesidad de HITL |
| `deep_research_plan` | Generar plan de investigación con preguntas y fuentes sugeridas |

## Docker Compose para Apple Silicon

La composición incluirá imágenes multi-architecture cuando sea posible. Ollama se tratará como servicio externo por defecto, accesible desde contenedores en macOS mediante `host.docker.internal:11434`. Neo4j, PostgreSQL, Redis, API y frontend correrán dentro de Docker Compose.

## Repositorio y prácticas de desarrollo

El repositorio nuevo será público y se inicializará con commits bajo:

```text
user.name = vtomasv
user.email = vtomasv@gmail.com
```

Se incluirán `AGENTS.md`, documentación de arquitectura, especificación OpenSpec ligera en `openspec/`, y estructura preparada para integración futura con flujos de planificación como vibekanban u oencode cuando estén disponibles.

## Referencias

[1]: https://github.com/VectifyAI/PageIndex "VectifyAI/PageIndex"
[2]: https://github.com/safishamsi/graphify "safishamsi/graphify"
[3]: https://github.com/robert-mcdermott/ai-knowledge-graph "robert-mcdermott/ai-knowledge-graph"
[4]: https://github.com/LearningCircuit/local-deep-research "LearningCircuit/local-deep-research"
[5]: https://github.com/diegoespindola/osintChile "diegoespindola/osintChile"
[6]: https://github.com/0xSS3K/OSINT-CHILE "0xSS3K/OSINT-CHILE"
[7]: https://www.maltego.com/ "Maltego"
[8]: https://dequienes.cl/ "deQuiénes"
