# Política de evidencia real para OSINT Chile Graph

Tom reportó correctamente que una transformación OSINT no puede limitarse a describir una consulta o fabricar una entidad desde un dork. Desde esta iteración, el sistema debe distinguir estrictamente entre **hechos observados**, **tareas humanas pendientes**, **salidas locales de normalización** y **datos demostrativos desactivados**.

## Regla central

Una transformación automática sólo puede crear una entidad de hallazgo si existe una de estas bases verificables: una respuesta HTTP consultada durante la ejecución, una API pública/autorizada, un documento público recuperado, una evidencia capturada manualmente por el operador, o un algoritmo local declarado como tal, por ejemplo validación matemática de RUT o normalización de teléfono. Un dork por sí solo ya no es evidencia ni debe presentarse como hallazgo.

## Estados de fuente

| Estado | Significado | Persistencia permitida |
| --- | --- | --- |
| `verified_evidence` | El conector consultó una fuente pública/autorizada y capturó URL, extracto y fecha. | Crear evidencia, entidad y relación `SUPPORTED_BY_EVIDENCE`. |
| `operator_required` | La fuente requiere CAPTCHA, sesión, pago, aceptación de términos, interacción manual o revisión legal. | Crear tarea HITL con URL e instrucciones; no crear entidad factual. |
| `local_algorithm` | La salida deriva de algoritmo local, como RUT válido o formato de patente. | Crear entidad técnica con nota de que no confirma identidad/titularidad. |
| `no_results` | El conector automático consultó una fuente y no encontró resultados. | Registrar evidencia negativa o estado de ejecución, no inferir ausencia definitiva. |
| `blocked_or_unavailable` | La fuente no pudo consultarse sin controles adicionales. | Crear tarea HITL o evento de fuente; no simular hallazgos. |

## Fuentes iniciales

| Fuente | Modo | Decisión |
| --- | --- | --- |
| Búsqueda web pública HTML | Automático responsable | Usar para producir evidencia citada desde resultados reales, con título, URL y snippet. |
| Diario Oficial | HITL y búsqueda web focalizada | El sitio puede exponer protecciones anti-bot; se generará búsqueda focalizada y tarea manual si no hay API estable. |
| SII situación tributaria de terceros | HITL | La consulta pública informa RUT, nombre/razón social, inicio de actividades, actividades, documentos timbrados y observaciones según ChileAtiende, pero la prueba HTTP exige CAPTCHA; no se automatiza ni se evade. |
| Mercado Público | Búsqueda web focalizada/HITL | Automatizar sólo vía resultados públicos indexados; consulta avanzada queda HITL si requiere sesión o controles. |
| Rutificador, Volante o Maleta y servicios similares | HITL | No se automatiza scraping de sitios que puedan exponer datos personales, bloquear automatización o requerir interacción. La herramienta abre el sitio y captura evidencia provista explícitamente por el operador. |

## Criterio de UI

La interfaz debe mostrar etiquetas visibles: **Evidencia real**, **Algoritmo local**, **Requiere humano**, **Sin resultados** o **No automatizable**. El fallback demostrativo no debe mezclarse con investigaciones reales.
