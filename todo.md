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
