# Notas de investigación inicial: frameworks obligatorios

## PageIndex

Repositorio: https://github.com/VectifyAI/PageIndex

PageIndex se presenta como un sistema de RAG sin base vectorial, orientado a documentos largos y complejos. Construye un índice jerárquico tipo “tabla de contenidos” y luego realiza recuperación razonada mediante búsqueda en árbol. Para el MVP OSINT chileno conviene integrarlo como un adaptador opcional para documentos descargados o cargados por el usuario, especialmente PDFs, documentos legales, informes públicos, resoluciones, actas y documentos técnicos.

Decisión de integración: crear una interfaz `DocumentIndexer` y una implementación `PageIndexAdapter`. El MVP puede persistir metadatos y árboles semánticos en PostgreSQL/Neo4j, dejando la ejecución real de PageIndex como módulo opcional instalable, para evitar acoplar el arranque de Docker a paquetes de investigación inestables.

## graphify

Repositorio: https://github.com/safishamsi/graphify

Graphify transforma carpetas de código, documentos, esquemas SQL, PDFs, imágenes, audio y video en un grafo de conocimiento consultable. Indica soporte para exportación a Neo4j mediante generación de Cypher o push directo, además de consultas de grafo y MCP. Declara procesamiento local para código con tree-sitter y uso de modelos externos/locales para contenido semántico en documentos, imágenes y PDFs.

Decisión de integración: usar graphify como herramienta opcional para indexar documentación del proyecto, fuentes OSINT recolectadas por investigación y reportes, generando artefactos que puedan importarse a Neo4j. En el MVP se implementará un adaptador `GraphifyAdapter` con comandos configurables, sin obligar al usuario a instalarlo dentro del contenedor principal.

## Restricciones de seguridad y cumplimiento

El usuario pidió capacidades ofensivas como evadir CAPTCHA, automatizar portales restringidos y recolectar datos no públicos. Esto no se implementará. La alternativa segura será una arquitectura human-in-the-loop: tareas que requieren login, CAPTCHA, consentimiento o revisión manual quedan en estado `requires_human`, con instrucciones, URL de destino, campos esperados y almacenamiento de resultados provistos manualmente por el operador autorizado.

## Implicación arquitectónica

La plataforma debe diferenciar explícitamente entre:

| Categoría | Ejecución | Ejemplos |
|---|---|---|
| Fuente pública pasiva | Automática | Dorks, datos abiertos, páginas públicas, datasets descargables |
| Fuente autorizada con API | Automática con credenciales | APIs configuradas por variables de entorno |
| Fuente con login/CAPTCHA/restricción | Human-in-the-loop | Portales estatales, consultas que exigen verificación manual |
| Fuente no pública o no autorizada | No soportada | Datos privados, bypass, scraping restringido |

Estas decisiones deben quedar documentadas en README y en una política de uso aceptable del proyecto.

## Referencias revisadas

[1]: https://github.com/VectifyAI/PageIndex "VectifyAI/PageIndex"
[2]: https://github.com/safishamsi/graphify "safishamsi/graphify"

## ai-knowledge-graph

Repositorio: https://github.com/robert-mcdermott/ai-knowledge-graph

El proyecto genera grafos de conocimiento desde texto no estructurado mediante extracción de tripletas Sujeto-Predicado-Objeto (SPO). Incluye chunking, extracción con LLM, estandarización de entidades, inferencia de relaciones y visualización interactiva. Declara compatibilidad con endpoints tipo OpenAI, incluyendo Ollama, LM Studio, OpenAI, vLLM y LiteLLM. Para el MVP chileno conviene usar su patrón conceptual: extracción de entidades y relaciones desde hallazgos textuales, documentos públicos y notas de investigación, persistiendo tripletas en Neo4j y en tablas relacionales de auditoría.

Decisión de integración: implementar una interfaz `KnowledgeGraphExtractor` con una implementación propia ligera compatible con OpenAI/Ollama y una ruta de integración futura con este proyecto. El MVP debe exponer prompts configurables para extracción de entidades, normalización, inferencia y generación de hipótesis.

## local-deep-research

Repositorio: https://github.com/LearningCircuit/local-deep-research

El proyecto opera como asistente de investigación profunda local, soporta Ollama, motores de búsqueda como SearXNG y múltiples modelos locales/cloud, produce reportes con citas, permite bases de conocimiento privadas e incluye Docker Compose. Su arquitectura resulta útil como referencia para un módulo de investigaciones: cola de tareas, estrategias de búsqueda, síntesis con citas, almacenamiento de fuentes y reportes reproducibles.

Decisión de integración: en el MVP se implementará un módulo `deep_research` minimalista que registre objetivos, consultas, fuentes, evidencias y síntesis. La ejecución avanzada quedará abstraída para conectarse posteriormente a local-deep-research o ejecutar un servicio externo configurado por URL. Se incluirá SearXNG opcional como endpoint de búsqueda, pero el primer MVP debe funcionar incluso sin motores externos.

## Nuevas referencias revisadas

[3]: https://github.com/robert-mcdermott/ai-knowledge-graph "robert-mcdermott/ai-knowledge-graph"
[4]: https://github.com/LearningCircuit/local-deep-research "LearningCircuit/local-deep-research"

## osintChile

Repositorio: https://github.com/diegoespindola/osintChile

El repositorio `osintChile` declara búsqueda automática de información de personas en Chile mediante scraping y contempla parámetros para RUT, patente y teléfono. La licencia visible es GPL-3.0, por lo que no conviene copiar código directamente en un proyecto nuevo si se desea flexibilidad de licencia; se usará solo como referencia conceptual. El README contiene un enfoque educativo y advierte el problema de privacidad de datos.

Decisión de integración: crear transforms propios para normalización/validación de RUT, patente y teléfono, y conectores compatibles con fuentes públicas o autorizadas. Los conectores que apunten a fuentes “no tan abiertas” se marcarán como human-in-the-loop o no soportados, según corresponda.

## 0xSS3K/OSINT-CHILE

Repositorio: https://github.com/0xSS3K/OSINT-CHILE

El repositorio ofrece una guía de recursos chilenos y dorks específicos. Incluye ejemplos para Diario Oficial y repositorios universitarios, además de una orientación hacia investigación basada en enlaces y dorks. La licencia visible es MIT, pero de todas formas se usará como fuente de ideas y no se copiarán textos extensos literalmente.

Decisión de integración: modelar los dorks como plantillas parametrizables en YAML/JSON, por ejemplo para nombre, RUT, empresa, email, dominio, repositorios universitarios, prensa y documentos públicos. El backend generará consultas y registrará evidencias, pero la ejecución real contra buscadores externos será configurable y podrá quedar en modo manual si no hay API autorizada.

## Referencias adicionales revisadas

[5]: https://github.com/diegoespindola/osintChile "diegoespindola/osintChile"
[6]: https://github.com/0xSS3K/OSINT-CHILE "0xSS3K/OSINT-CHILE"

## Maltego

Sitio: https://www.maltego.com/

Maltego se presenta como una plataforma de investigaciones OSINT y ciberinvestigación basada en grafos, entidades, integraciones y “transforms”. El patrón clave a reutilizar conceptualmente es el flujo: una entidad inicial genera nuevas entidades por medio de transformaciones; cada hallazgo queda trazado con fuente, timestamp, tipo de relación y confianza.

Decisión de integración: el MVP chileno implementará `entities`, `relationships`, `transforms` y `evidence`. La UI debe permitir partir desde RUT, email, patente, teléfono, dominio, nombre o empresa y expandir el grafo transform por transform.

## deQuiénes

Sitio: https://dequienes.cl/

La página pública visible permite buscar accionistas o empresas por nombre o RUT. Está orientada a una experiencia de búsqueda directa, con foco en sociedades, accionistas y empresas. No se automatizarán consultas restringidas ni se intentará eludir controles; se tomará como inspiración de UX y se dejarán conectores human-in-the-loop cuando una consulta requiera interacción del usuario.

Decisión de integración: incluir entidades `Person`, `Company`, `Shareholder`, `Role`, `Document` y relaciones como `OWNS`, `REPRESENTS`, `MENTIONED_IN`, `HAS_IDENTIFIER` y `ASSOCIATED_WITH`. La búsqueda por RUT debe estar habilitada como semilla del grafo, pero las fuentes con restricciones deben quedar en modo asistido.

## Referencias adicionales revisadas

[7]: https://www.maltego.com/ "Maltego"
[8]: https://dequienes.cl/ "deQuiénes"
