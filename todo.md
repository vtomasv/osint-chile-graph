# TODO — corrección build Docker frontend

- [x] Leer el error reportado por Tom desde `pasted_content_2.txt`.
- [x] Identificar causa probable: `pnpm install` en Docker no encuentra `patches/wouter@3.7.1.patch` porque el Dockerfile del frontend copia `package.json` y `pnpm-lock.yaml`, pero no copia el directorio `patches` antes de instalar dependencias.
- [x] Revisar `Dockerfile.frontend`, `package.json` y existencia de `patches/wouter@3.7.1.patch`.
- [x] Corregir `Dockerfile.frontend` para incluir `patches` antes de `pnpm install`, o eliminar la dependencia parcheada si ya no es necesaria.
- [x] Ejecutar validaciones disponibles en sandbox: `pytest` pasó con 4 pruebas, `tsc --noEmit` pasó, `pnpm build` pasó y se verificó que `patches` se copie antes de `pnpm install`.
- [x] Crear commit bajo `vtomasv <vtomasv@gmail.com>`, guardar checkpoint local y publicar en GitHub usando el remoto `github` (`main -> main`, commit `cd10619`).
- [x] Entregar a Tom los comandos exactos para actualizar y volver a probar en su Mac.

## Nuevo reporte de Tom: Dockerfile.frontend todavía aparece sin `COPY patches`

- [x] Confirmar en el repositorio local del sandbox que `Dockerfile.frontend` sí contiene `COPY patches ./patches` antes de `pnpm install`.
- [x] Comparar el log enviado por Tom con el Dockerfile corregido: su log muestra `RUN corepack enable && pnpm install` en la línea 4, mientras el corregido tiene `COPY patches ./patches` en la línea 4 y el `RUN` en la línea 5; por lo tanto Tom está construyendo desde una copia anterior o desde otro directorio.
- [x] Preparar comandos de recuperación: la corrección ya fue publicada en GitHub con `git push github main`; Tom puede usar `git fetch origin main` y `git reset --hard origin/main` si no tiene cambios locales, o parche manual si su copia apunta a otro directorio.
- [x] Incluir limpieza de caché de build Docker y verificación previa con `nl -ba Dockerfile.frontend` antes de reconstruir.

## Nuevo reporte de Tom: frontend container falla por `ERR_MODULE_NOT_FOUND: express`

- [x] Revisar `Dockerfile.frontend`, `package.json` y `server/index.ts`: el build usa `esbuild --packages=external`, por lo que `dist/index.js` conserva `import express from "express"` y la imagen final debe incluir `node_modules`.
- [x] Corregir la imagen final del frontend agregando una etapa `prod-deps` con `pnpm prune --prod` y copiando `/app/node_modules` al runner.
- [x] Validar que `pnpm build` siga pasando y que el artefacto final pueda resolver `express`; se simuló el runner con `dist`, `package.json` y `node_modules`, sirviendo HTML correctamente en `PORT=4173`.
- [x] Crear commit bajo `vtomasv <vtomasv@gmail.com>` y publicar en GitHub (`85e4f15`, `main -> main`); queda pendiente guardar checkpoint final.
- [ ] Entregar a Tom comandos de actualización, rebuild sin caché y verificación del contenedor frontend.

## Solicitud de Tom: pantalla detallada de hallazgos y más transformaciones

- [x] Inspeccionar `client/src/pages/Home.tsx`, componentes disponibles y contrato actual de datos: la UI consume `/api/transforms`, `/api/graph/{id}` y `/api/transforms/run`; el backend persiste evidencias y ejecuciones, pero todavía no las expone en un reporte detallado.
- [x] Definir una pantalla/panel de resultados detallados con resumen ejecutivo, entidades, relaciones, evidencias, tareas HITL, línea de tiempo, confianza, fuente y trazabilidad; se implementará como módulo inferior conectado a un nuevo endpoint `/api/investigations/{id}/findings`.
- [x] Ampliar el catálogo de transformaciones para RUT con validación, normalización, variaciones de búsqueda, dorks, vínculos societarios/HITL, documentos públicos/HITL y análisis de consistencia.
- [x] Ampliar el catálogo de transformaciones para teléfono con normalización E.164 Chile, detección móvil/fijo, carrier/HITL, WhatsApp/HITL, dorks y vínculos por evidencia.
- [x] Ampliar el catálogo de transformaciones para patente con normalización, formato antiguo/nuevo, consultas vehiculares/HITL, dorks, vínculos geográficos y evidencia manual.
- [x] Agregar transformaciones transversales para email `.cl`, dominio, nombre/persona y empresa cuando el modelo actual lo permita.
- [x] Implementar la UI respetando la estética forense actual, con panel detallado de hallazgos, tabs, métricas, tablas, badges de confianza, bitácora y resumen HITL.
- [x] Validar TypeScript (`pnpm exec tsc --noEmit`), build de producción (`vite build` + `esbuild`), pruebas backend (`PYTHONPATH=apps/api python -m pytest apps/api/tests -q`) y revisar que `Dockerfile.frontend` mantenga las correcciones previas.
- [x] Crear commit, publicar en GitHub y guardar checkpoint final (`99141e9` + checklist `6018941`, checkpoint `60189414`).
- [ ] Entregar a Tom instrucciones de actualización y prueba local.

## Nueva solicitud de Tom: expediente OSINT legible, AI y HITL accionable

- [x] Revisar el estado actual de la pantalla de hallazgos, endpoint `/findings`, modelos de DB y transformaciones para identificar por qué sólo aparecen logs poco útiles.
- [x] Crear una vista de expediente por entidad donde se pueda seleccionar un RUT, teléfono, patente, email, dominio, persona o empresa y ver todos sus datos asociados, relaciones, evidencias y tareas pendientes.
- [x] Agregar narrativas AI/locales de hallazgos por objetivo y por entidad, con explicación legible, hipótesis, vacíos de información y próximos pasos sugeridos.
- [x] Reemplazar el reporte de logs por secciones de valor: resumen del objetivo, fichas enriquecidas, relaciones, fuentes, confianza, timeline y matriz de hallazgos.
- [x] Implementar continuidad HITL: abrir/preview de fuentes cuando sea posible, formulario para capturar resultados humanos, guardar evidencia estructurada y asociarla al objetivo/entidad.
- [x] Agregar visualizaciones de informe: grafo de relaciones, treemap de tipos de entidades/evidencias, Sankey de origen→transformación→hallazgo y relaciones semánticas agrupadas.
- [x] Validar backend/frontend; falta publicar commit en GitHub y guardar checkpoint final.
- [ ] Entregar a Tom instrucciones de uso y prueba del nuevo expediente.

## Corrección crítica solicitada por Tom: OSINT real, no máscara de datos

- [x] Auditar transformaciones actuales para identificar cuáles producen evidencia real, cuáles sólo generan dorks/descripciones y cuáles deben pasar a HITL.
- [x] Eliminar o rotular explícitamente cualquier fallback/demo para que nunca se confunda con evidencia OSINT real.
- [x] Implementar conectores verificables para fuentes públicas/autorizadas, empezando por API oficial de Mercado Público y dejando SII/Diario Oficial como HITL cuando no corresponde automatizar sin operador.
- [x] Para fuentes como Rutificador, Volante o Maleta, SII u otras que requieran CAPTCHA, sesión, aceptación manual o restrinjan scraping, crear tareas HITL con navegador integrado, instrucciones, URL de búsqueda y formulario de captura de evidencia real.
- [x] Persistir evidencia durante la sesión del expediente con URL, fecha de consulta, conector, estado, extracto textual, entidades extraídas, confianza y relación con el objetivo.
- [x] Actualizar UI para distinguir con claridad `evidencia real`, `pendiente humano`, `sin acceso automatizado` y `demo desactivado`.
- [x] Validar que las transformaciones ya no creen entidades útiles a partir de texto ficticio sino desde resultados reales o desde captura humana explícita.
- [x] Ejecutar pruebas, publicar commit en GitHub y guardar checkpoint final. Validaciones locales pasan: `pnpm test`, `pnpm run check`, `pnpm run build`; commit publicado en GitHub: `d388606`.

## Ajuste arquitectónico: backend accesible desde la app Manus

- [x] Resolver conflictos de la actualización full-stack sin perder la interfaz forense ni los cambios OSINT previos.
- [x] Implementar endpoints/procedures del backend Manus para transforms, grafo, hallazgos, estados de fuente y tareas HITL.
- [x] Migrar la UI para invocar el backend del propio proyecto, eliminando la dependencia de `http://localhost:8000` desde el navegador.
- [x] Añadir pruebas Vitest que demuestren que los transforms no devuelven evidencia ficticia y sí devuelven estados de fuente/HITL verificables.
