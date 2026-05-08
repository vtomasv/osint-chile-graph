# OSINT Chile Graph Workbench

**OSINT Chile Graph Workbench** es un MVP local para investigación OSINT orientada a Chile. La interfaz está inspirada en flujos de trabajo tipo grafo, con semillas como RUT, correo `.cl`, patente chilena, teléfono, dominio, nombre o empresa. El backend organiza transforms auditables, entidades, relaciones, evidencias, tareas **human-in-the-loop**, prompts configurables e integración con IA local mediante Ollama o con APIs externas compatibles.

El proyecto está preparado para ejecutarse localmente mediante **Docker Compose** en Apple Silicon, incluido Apple M3 Max. Ollama queda fuera del Compose por defecto y corre en macOS; la API accede al servicio del host desde los contenedores mediante `host.docker.internal:11434`, mecanismo soportado por Docker Desktop para alcanzar servicios del host desde contenedores.[1] Ollama expone por defecto su API local en el puerto `11434`.[2]

## Alcance responsable

La herramienta implementa conectores automáticos para normalización local, generación de consultas, fuentes públicas o fuentes donde exista autorización operacional. No implementa evasión de CAPTCHA, bypass anti-bot, recolección de datos no públicos, fuerza bruta ni automatización contra portales restringidos. Las fuentes que requieran login, CAPTCHA, autorización explícita, revisión legal o validación manual se modelan como tareas **human-in-the-loop** para que un analista opere el portal fuera del sistema y registre evidencia verificable.

| Tipo de fuente | Estado en el MVP | Comportamiento esperado |
|---|---:|---|
| Normalización local de RUT, email, teléfono y patente | Automático | Crea entidades y relaciones trazables sin consultar servicios externos. |
| Dorks y fuentes públicas | Asistido | Genera consultas y evidencia para revisión manual o APIs autorizadas. |
| Portales con login, CAPTCHA o validación manual | Human-in-the-loop | Crea una tarea para que el analista complete la revisión con autorización. |
| Datos no públicos, filtrados o protegidos | No soportado | El sistema no automatiza ni facilita acceso no autorizado. |
| Escaneo activo ofensivo | No habilitado por defecto | Debe agregarse solo bajo autorización expresa y controles de alcance. |

## Stack técnico

El frontend usa React, TypeScript y React Flow para representar el grafo de investigación.[3] La API usa FastAPI, una pila habitual para construir APIs Python tipadas y documentadas automáticamente.[4] La persistencia combina PostgreSQL para expedientes y evidencias, Neo4j para relaciones de grafo y Redis para estado ligero o colas futuras.

| Capa | Tecnología | Puerto local por defecto |
|---|---|---:|
| Frontend | React, TypeScript, React Flow, Tailwind, shadcn/ui | `3000` |
| API | FastAPI + Uvicorn | `8000` |
| Base relacional | PostgreSQL 16 | `5432` |
| Grafo | Neo4j 5 Community | `7474`, `7687` |
| Cache/estado | Redis 7 | `6379` |
| IA local | Ollama en macOS, fuera del Compose | `11434` |
| IA externa | API compatible con OpenAI vía variables de entorno | Configurable |

## Requisitos locales

Para probar el proyecto en tu Apple M3 Max necesitas Docker Desktop para macOS, Git, Make y Ollama si quieres ejecutar análisis con modelos locales. Docker Compose viene integrado en Docker Desktop moderno; si prefieres no usar `make`, todos los comandos equivalentes se muestran más abajo.

| Herramienta | Uso | Verificación recomendada |
|---|---|---|
| Docker Desktop | Ejecutar PostgreSQL, Neo4j, Redis, API y frontend | `docker compose version` |
| Git | Clonar el repositorio | `git --version` |
| Make | Ejecutar atajos del proyecto | `make --version` |
| Ollama | Ejecutar modelos locales fuera de Docker | `ollama --version` |

## Instalación rápida

Primero clona el repositorio, copia la configuración de ejemplo y levanta los servicios. El archivo `.env.example` contiene valores de desarrollo local y no incluye secretos reales.

```bash
git clone https://github.com/vtomasv/osint-chile-graph.git
cd osint-chile-graph
cp .env.example .env
make dev
```

Si prefieres no usar Make, ejecuta directamente:

```bash
cp .env.example .env
docker compose up --build
```

Cuando los contenedores terminen de levantar, abre los servicios desde tu navegador.

| Servicio | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Healthcheck API | http://localhost:8000/health |
| Documentación API | http://localhost:8000/docs |
| Neo4j Browser | http://localhost:7474 |

## Configuración de Ollama local

Ollama debe ejecutarse en tu Mac, no dentro de Docker Compose. Este diseño evita empaquetar modelos pesados dentro del MVP y permite que el usuario seleccione modelos locales según la memoria disponible.

```bash
ollama serve
ollama pull llama3.1:8b
```

La configuración por defecto usa `OLLAMA_BASE_URL=http://host.docker.internal:11434` y `OLLAMA_MODEL=llama3.1:8b`. Puedes cambiar el modelo en `.env` o desde los endpoints de configuración de IA si agregas una interfaz administrativa. Si ya tienes otro modelo descargado, por ejemplo `mistral`, `qwen2.5` o `llama3.2`, reemplaza `OLLAMA_MODEL` por el nombre correspondiente.

## Comandos de operación

El Makefile encapsula las acciones más frecuentes, pero no oculta Docker Compose. Los comandos están pensados para desarrollo local y pruebas iniciales.

| Comando | Efecto |
|---|---|
| `make dev` | Copia `.env` si no existe y ejecuta `docker compose up --build` en primer plano. |
| `make up` | Levanta los servicios en segundo plano con rebuild si corresponde. |
| `make down` | Detiene y elimina contenedores del proyecto, conservando volúmenes. |
| `make logs` | Sigue logs de API, frontend, PostgreSQL, Neo4j y Redis. |
| `make doctor` | Muestra las URLs esperadas de los servicios principales. |
| `./scripts_validate_repo.sh` | Ejecuta validaciones locales de backend, tests, TypeScript y build del frontend. |

## Validación realizada en sandbox

El entorno de sandbox no tiene Docker disponible, por lo que no fue posible ejecutar `docker compose up --build` dentro de Manus. Sí se corrigió el contexto de build del Dockerfile de la API para que Docker Compose copie correctamente `apps/api` y `prompts` desde la raíz del repositorio. Además, se ejecutó el script de validación reproducible con resultados correctos.

| Validación | Resultado |
|---|---:|
| Compilación Python de `apps/api/app` y tests | OK |
| Import de `app.main` con SQLite temporal | OK |
| Pruebas `pytest` del backend | `4 passed` |
| TypeScript `pnpm run check` | OK |
| Build de producción `pnpm run build` | OK |
| Reinicio del servidor de desarrollo frontend | OK |
| Docker Compose runtime | Pendiente de validar en tu Mac porque Docker no existe en el sandbox |

## Transforms incluidos

Los transforms siguen un contrato inspirado en herramientas de investigación por grafo. Cada ejecución produce entidades, relaciones, evidencias y, cuando corresponde, tareas human-in-the-loop.

| Transform | Descripción | Modo |
|---|---|---|
| `cl.rut.normalize` | Valida dígito verificador y normaliza RUT chileno. | Automático |
| `cl.email.analyze` | Analiza correo, dominio y TLD `.cl`. | Automático |
| `cl.phone.normalize` | Normaliza número chileno y crea tarea de enriquecimiento autorizado. | Automático + HITL |
| `cl.plate.normalize` | Valida formatos frecuentes de patente chilena. | Automático |
| `cl.dork.generate` | Genera consultas para fuentes públicas y documentos. | Automático asistido |
| `cl.source.diario_oficial.human` | Prepara búsqueda manual en Diario Oficial. | HITL |
| `cl.source.registro_empresas.human` | Prepara consulta manual societaria. | HITL |
| `ai.extract_entities` | Punto de entrada para extracción de entidades con IA. | IA configurable |

## Prompts configurables e IA

Los prompts de sistema viven en `prompts/system_prompts.yaml`. El MVP incluye prompts para extracción de entidades, síntesis semántica, análisis de vínculos, clasificación de fuentes y planificación de investigación profunda. El backend expone rutas para listar y editar prompts, además de rutas para seleccionar proveedor y modelo. Las claves de proveedores externos no deben versionarse; deben ir en `.env` local o en el gestor de secretos del entorno donde se despliegue.

| Proveedor | Variable principal | Uso esperado |
|---|---|---|
| Ollama | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | Modelos locales ejecutados en macOS. |
| API externa compatible | `EXTERNAL_AI_BASE_URL`, `EXTERNAL_AI_API_KEY`, `EXTERNAL_AI_MODEL` | Modelos remotos autorizados por el usuario. |

## Referencias arquitectónicas

El diseño incorpora patrones conceptuales de PageIndex, graphify, ai-knowledge-graph y local-deep-research como adaptadores documentados. En esta versión se declaran módulos de integración y contratos para indexación, grafo de conocimiento e investigación profunda, sin copiar código de terceros de forma incompatible. Los detalles técnicos están en `docs/architecture.md`.

## Troubleshooting en Apple Silicon

Si el frontend carga pero no encuentra la API, confirma que el contenedor de API esté arriba con `docker compose ps` y abre `http://localhost:8000/health`. Si el análisis de IA falla, verifica que Ollama esté ejecutándose en macOS con `curl http://localhost:11434/api/tags` y que el modelo configurado exista en `ollama list`. Si Neo4j tarda en iniciar, revisa `docker compose logs -f neo4j`; el primer arranque puede demorar más por creación de volúmenes.

| Síntoma | Diagnóstico | Acción recomendada |
|---|---|---|
| `api` no conecta a PostgreSQL | Base aún no saludable o credenciales alteradas | Ejecuta `docker compose logs -f postgres api` y compara `.env` con `.env.example`. |
| IA responde con error de conexión | Ollama no está activo en macOS | Ejecuta `ollama serve` y prueba `curl http://localhost:11434/api/tags`. |
| Neo4j Browser pide credenciales | Es el comportamiento normal | Usa `neo4j` y `osint_neo4j_password`, salvo que cambies `.env`. |
| Build de API falla copiando prompts | Versión antigua del repositorio | Asegúrate de tener el Dockerfile corregido con contexto raíz en `docker-compose.yml`. |
| Puerto ocupado | Otro servicio usa el puerto | Cambia los puertos en `docker-compose.yml` o detén el servicio conflictivo. |

## Desarrollo local sin Docker

Para depurar el backend sin contenedores, instala dependencias Python y ejecuta pruebas. Para el frontend, usa `pnpm install` y los scripts definidos en `package.json`.

```bash
sudo pip3 install -r apps/api/requirements.txt
PYTHONPATH=apps/api pytest -q apps/api/tests
pnpm install
pnpm run check
pnpm run build
```

El script `scripts_validate_repo.sh` configura una base SQLite temporal para validar imports sin depender de PostgreSQL ni credenciales externas del entorno. Este script es útil antes de hacer commits o antes de reportar errores.

## Estado de publicación

El commit local está preparado con autor `vtomasv <vtomasv@gmail.com>`. Si el push automático falla por credenciales de GitHub, ejecuta estos comandos desde tu máquina una vez autenticado con `gh auth login` o con tu remoto HTTPS/SSH configurado.

```bash
git remote -v
git push -u origin main
```

## Licencia

MIT. Este repositorio no copia código de herramientas con licencias incompatibles; usa referencias conceptuales documentadas y conectores propios.

## References

[1]: https://docs.docker.com/desktop/features/networking/ "Docker Desktop networking features"
[2]: https://github.com/ollama/ollama/blob/main/docs/api.md "Ollama API documentation"
[3]: https://reactflow.dev/ "React Flow documentation"
[4]: https://fastapi.tiangolo.com/ "FastAPI documentation"
