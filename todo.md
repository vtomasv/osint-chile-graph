# TODO — estabilización para instalación local

- [x] Auditar estado Git, remotos, archivos no versionados y artefactos generados.
- [x] Revisar estructura del monorepo y archivos críticos de configuración.
- [x] Ejecutar validación inicial de frontend y backend.
- [x] Corregir Dockerfile de la API: el `COPY ../../prompts` fallaba con el contexto de build anterior.
- [x] Robustecer scripts de validación para que no hereden variables `.env` del entorno Manus.
- [x] Eliminar artefactos que no deben entrar al repositorio y reforzar `.gitignore`.
- [x] Validar build del frontend y pruebas del backend luego de las correcciones.
- [x] Validar la configuración de Docker Compose por medios disponibles en el sandbox: Docker no está disponible aquí, pero el contexto de build fue corregido y queda documentada la prueba local.
- [x] Actualizar README con instalación paso a paso en Apple M3 Max, Ollama local y troubleshooting.
- [x] Confirmar estado de credenciales GitHub antes del push final.
- [ ] Crear commit/checkpoint final limpio bajo `vtomasv <vtomasv@gmail.com>` y publicar si GitHub lo permite.
