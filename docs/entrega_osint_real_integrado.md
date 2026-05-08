# Entrega OSINT Chile: backend integrado, evidencia real y HITL

Esta guía consolida los pasos para actualizar, reconstruir, verificar y operar la versión en la que la interfaz deja de depender de un backend local externo y consume rutas OSINT integradas en el propio proyecto Manus.

## Actualización del repositorio

Para obtener la versión publicada en GitHub:

```bash
git fetch github main
git checkout main
git pull github main
```

El commit principal de esta entrega es:

```text
d388606 Integrate real OSINT backend routes and HITL evidence flow
```

## Instalación y verificación local

Desde la raíz del proyecto:

```bash
pnpm install
pnpm test
pnpm run check
pnpm run build
```

Las validaciones esperadas para esta entrega son que **Vitest**, **TypeScript** y **build de producción** terminen sin errores. La prueba nueva `server/osintRoutes.test.ts` valida explícitamente que los transforms no fabriquen evidencia ficticia y que, cuando una fuente chilena requiere revisión humana, se registren estados de fuente y tareas HITL trazables.

## Arranque local

Para ejecutar la aplicación con backend integrado:

```bash
pnpm dev
```

Luego abrir la URL local informada por el servidor. La UI debe consumir rutas relativas bajo `/api`, por ejemplo `/api/transforms`, `/api/transforms/run`, `/api/graph/demo` y `/api/investigations/demo/findings`, sin apuntar a `http://localhost:8000` desde el navegador.

## Rebuild de contenedor frontend sin caché

Si se usa el flujo Docker previamente corregido, reconstruir sin caché y verificar que el runner resuelva dependencias de producción:

```bash
docker build --no-cache -f Dockerfile.frontend -t osint-chile-graph-frontend:latest .
docker run --rm -p 4173:4173 -e PORT=4173 osint-chile-graph-frontend:latest
curl -I http://localhost:4173/
```

La respuesta HTTP debe ser exitosa y el contenedor no debe fallar por `Cannot find package 'express'` ni por ausencia de `node_modules`.

## Uso operativo del expediente OSINT

Primero se agrega una semilla chilena, por ejemplo **RUT**, teléfono, patente, email, dominio, nombre o empresa. Luego se selecciona un transform y se ejecuta desde el panel lateral.

Los transforms automáticos sólo pueden crear evidencia cuando el conector obtiene una fuente real o cuando el resultado es explícitamente un cálculo local declarado, por ejemplo validación/normalización de RUT. Las fuentes que no deben automatizarse irresponsablemente, como SII, Rutificador, Volante o Maleta y consultas con CAPTCHA, sesión o restricciones anti-scraping, quedan como **HITL** con URL, instrucciones y formulario de captura.

En el expediente se deben revisar las pestañas **Expediente**, **Evidencias**, **Fuentes** y **HITL operativo**. Si no hay evidencia verificable, la UI debe decir **demo desactivado** o **sin evidencia OSINT verificada**, no mostrar datos de ejemplo. Si una fuente no es automatizable, debe mostrarse como **sin acceso automatizado** o **requiere HITL**.

Para convertir una tarea HITL en evidencia, abrir la tarea, consultar la fuente autorizada, pegar URL/extracto verificable, indicar confianza y guardar. Sólo esa acción convierte la revisión humana en evidencia citable asociada al objetivo.
