# AGENTS.md

## Principio de trabajo

Este repositorio implementa un MVP local de investigación OSINT para Chile. Todo cambio debe preservar el enfoque de **cartografía forense neo-brutalista chilena**, trazabilidad de evidencias, separación entre hechos e inferencias, y límites de cumplimiento.

## Restricciones de seguridad y cumplimiento

No se debe implementar evasión de CAPTCHA, bypass de sistemas anti-bot, fuerza bruta, scraping de información no pública, explotación, phishing, abuso de portales o automatización contra servicios restringidos. Las fuentes que requieran login, CAPTCHA, consentimiento, autorización o validación manual deben modelarse como tareas `human-in-the-loop`.

## Stack objetivo

El MVP usa FastAPI, PostgreSQL, Neo4j, Redis, React/TypeScript, React Flow, Docker Compose y Ollama local fuera del compose por defecto. Las APIs externas se configuran por variables de entorno y nunca deben incluir credenciales reales en el repositorio.

## Convenciones

Los commits se realizan como `vtomasv <vtomasv@gmail.com>`. Los prompts deben permanecer configurables en `prompts/*.yaml`. Los transforms deben declarar modo de ejecución, nivel de riesgo, fuentes y si requieren intervención humana.
