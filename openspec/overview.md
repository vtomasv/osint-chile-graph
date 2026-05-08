# OpenSpec: OSINT Chile Graph MVP

## Objetivo

Construir una plataforma local, auditable y extensible para investigación OSINT chilena basada en entidades, transforms, evidencias, grafo de conocimiento e IA configurable.

## Capacidades iniciales

| Capacidad | Estado MVP |
|---|---|
| Investigación por RUT | Normalización y validación local |
| Investigación por email .cl | Análisis de dominio y generación de consultas |
| Investigación por teléfono chileno | Normalización E.164 y tarea HITL para enriquecimiento |
| Investigación por patente chilena | Normalización y validación de formato |
| Grafo estilo Maltego | React Flow + persistencia relacional + Neo4j opcional |
| IA local | Ollama externo configurable |
| APIs externas | OpenAI-compatible mediante variables de entorno |
| Prompts de sistema | YAML editable y endpoint de consulta |
| Fuentes restringidas | Human-in-the-loop, no automatización evasiva |

## Requisito de cumplimiento

Cada resultado debe incluir fuente, evidencia o indicación explícita de que es inferencia. Las inferencias de IA no se deben mezclar con hechos confirmados.
