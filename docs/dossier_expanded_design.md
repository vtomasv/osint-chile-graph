# Diseño de expediente OSINT legible y accionable

## Propósito

La siguiente iteración convierte la pantalla de hallazgos desde una bitácora técnica hacia un **expediente de inteligencia**. El usuario debe poder seleccionar cualquier entidad del objetivo —RUT, teléfono, patente, email, dominio, persona o empresa— y leer qué se sabe, qué evidencia lo sostiene, qué relaciones existen, qué tareas humanas quedan pendientes y cómo continuar la investigación sin perder trazabilidad.

## Modelo de lectura

| Capa | Rol en la pantalla | Resultado esperado |
|---|---|---|
| Expediente del objetivo | Vista ejecutiva de toda la investigación | Síntesis narrativa, métricas, vacíos y próximos pasos |
| Ficha de entidad | Vista focalizada por RUT/teléfono/patente/etc. | Datos asociados, relaciones, evidencias, tareas HITL y descripción AI/local |
| Evidencia | Hechos o extractos con fuente, confianza y fecha | Sustento verificable de cada afirmación |
| HITL | Tareas que requieren navegador humano o autorización | Apertura de fuente, captura de resultado, normalización y guardado en DB |
| Visualizaciones | Lectura analítica del objetivo | Grafo, treemap, Sankey, timeline y clusters semánticos |

## Flujo HITL accionable

Las fuentes con login, CAPTCHA o validación manual no se automatizan. Cada tarea HITL se muestra como una estación de trabajo con instrucciones, fuente sugerida, URL de búsqueda cuando existe, preview embebido si el sitio lo permite y fallback de apertura en pestaña externa. El operador pega el resultado, define confianza, URL consultada, extracto, entidades encontradas y relación con la entidad objetivo. El backend persiste esto como `Evidence`, crea o fusiona entidades y agrega relaciones `CONFIRMED_BY_HUMAN` o `MENTIONED_IN`.

## Narrativa AI/local

La app debe producir una explicación legible incluso si no hay proveedor LLM configurado. Para ello, el backend construye una síntesis determinística de tipo **AI-assisted local reasoning** con hechos, relaciones, señales débiles, vacíos y próximos pasos. Cuando el entorno tenga Ollama o API externa configurada, la misma estructura podrá enriquecerse con prompts existentes.

## Visualizaciones solicitadas

| Visualización | Fuente de datos | Uso analítico |
|---|---|---|
| Grafo de relaciones | `entities` + `relationships` | Entender conexiones directas e indirectas |
| Treemap | Conteo por tipo de entidad y evidencia | Ver concentración de hallazgos |
| Sankey | Transformación → entidad/evidencia/tarea | Medir qué transforms generan valor |
| Relaciones semánticas | Agrupación por tipo y confianza | Diferenciar hechos, inferencias y tareas pendientes |
| Timeline | Evidencia y ejecuciones | Reconstruir secuencia de investigación |

## Criterio de éxito

La bitácora queda relegada a depuración. La pantalla principal de resultados debe responder preguntas operativas: quién o qué es el objetivo, qué datos útiles se encontraron, cómo se conectan, qué tan confiables son, qué falta validar y cómo se incorpora la respuesta humana al banco de datos.
