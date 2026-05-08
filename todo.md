# TODO — corrección build Docker frontend

- [x] Leer el error reportado por Tom desde `pasted_content_2.txt`.
- [x] Identificar causa probable: `pnpm install` en Docker no encuentra `patches/wouter@3.7.1.patch` porque el Dockerfile del frontend copia `package.json` y `pnpm-lock.yaml`, pero no copia el directorio `patches` antes de instalar dependencias.
- [x] Revisar `Dockerfile.frontend`, `package.json` y existencia de `patches/wouter@3.7.1.patch`.
- [x] Corregir `Dockerfile.frontend` para incluir `patches` antes de `pnpm install`, o eliminar la dependencia parcheada si ya no es necesaria.
- [x] Ejecutar validaciones disponibles en sandbox: `pytest` pasó con 4 pruebas, `tsc --noEmit` pasó, `pnpm build` pasó y se verificó que `patches` se copie antes de `pnpm install`.
- [ ] Crear commit bajo `vtomasv <vtomasv@gmail.com>` y publicar en GitHub.
- [ ] Entregar a Tom los comandos exactos para actualizar y volver a probar en su Mac.
