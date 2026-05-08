# Diseño técnico — Hallazgos detallados y transforms OSINT Chile

## Modelo de hallazgos detallados

La pantalla de resultados debe consolidar información que ya existe en la base local: entidades, relaciones, evidencias, ejecuciones de transforms y tareas humanas. Para evitar acoplar la UI a múltiples endpoints, se agregará `GET /api/investigations/{investigation_id}/findings`, que devolverá un resumen ejecutivo y colecciones normalizadas.

| Bloque | Fuente local | Uso en UI |
| --- | --- | --- |
| `summary` | Conteos derivados de entidades, relaciones, evidencias y runs | KPIs de investigación, cobertura y confianza media. |
| `entities` | Tabla `entities` | Tabla filtrable de hallazgos con tipo, valor, confianza, propiedades y fecha. |
| `relationships` | Tabla `relationships` | Trazabilidad entre seed y hallazgo, transform que originó el vínculo y confianza. |
| `evidence` | Tabla `evidence` | Evidencias generadas por transform con fuente, extracto, propiedades y confianza. |
| `transform_runs` | Tabla `transform_runs` | Línea de tiempo de ejecución, input, output y estado. |
| `human_tasks` | Entidades de tipo `HumanTask` | Checklist HITL para fuentes que requieren autorización, CAPTCHA, login o verificación manual. |

## Catálogo ampliado de transforms

Se mantendrá una separación clara entre transforms **automáticos locales**, que solo derivan información del valor ingresado, y transforms **HITL**, que preparan consultas para fuentes públicas o autorizadas sin evadir restricciones. El objetivo es aumentar la cantidad de acciones útiles sin convertir la herramienta en un scraper invasivo.

| Tipo | Transforms automáticos propuestos | Transforms HITL propuestos |
| --- | --- | --- |
| RUT | Normalización, variantes de búsqueda, perfil tributario inferido, dorks especializados, consistencia de DV. | Diario Oficial, Registro de Empresas, SII/boletas solo con autorización, Mercado Público, causas/documentos públicos. |
| Teléfono | Normalización E.164 Chile, clasificación móvil/fijo/geográfico, variantes, dorks y artefactos de contacto. | Verificación WhatsApp/manual, carrier o portabilidad autorizada, directorios públicos permitidos. |
| Patente | Normalización, detección formato antiguo/nuevo/moto, variantes, dorks vehiculares, artefacto vehículo. | Registro Civil/consulta autorizada, multas/municipalidades, marketplace/repuestos si aplica. |
| Email/dominio | Normalización, dominio, TLD, organización probable, dorks y artefactos web. | WHOIS/DNS, sitio institucional, repositorios públicos. |
| Nombre/empresa | Variantes, alias, dorks por documentos públicos, entidades de búsqueda. | Diario Oficial, Mercado Público, RES, prensa y documentos públicos autorizados. |

## Decisiones de implementación

El backend se ampliará primero para que el frontend reciba datos reales. Luego la pantalla de resultados se integrará en `Home.tsx` como un panel detallado con pestañas ligeras, filtros locales y copia/exportación JSON básica. La interfaz conservará el estilo forense existente y no agregará dependencias nuevas salvo que el build lo requiera.
