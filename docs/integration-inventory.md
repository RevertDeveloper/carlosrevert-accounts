# Inventario de integración

Inventario levantado antes de integrar cada repositorio. Cada aplicación conserva su arquitectura y base de datos; Accounts solo centraliza identidad, plan, cuota y auditoría.

| Aplicación | Arquitectura | Flujo de IA protegido | Producción | Keycloak |
| --- | --- | --- | --- | --- |
| Home | React/Vite y API FastAPI de catálogo | Ninguno; consulta sesión, cuota y aplicaciones sin consumir | `carlosrevert.es`, web `10000`, API `10001` | Sin integración activa |
| Juridia | React/Vite, FastAPI, PostgreSQL/Qdrant y RAG | `POST /api/answer`, acción `legal_query` | `juridia.carlosrevert.es`, web `10100`, API privada `10101` | Sin integración activa |
| CLARK | Next.js, FastAPI, PostgreSQL, Redis, Meilisearch y Ollama | `POST /api/v1/ai/chat/stream` (`clark_chat`) y `/ai/stt/transcribe` (`clark_stt`) | `clark.carlosrevert.es`, web `10200`, API privada `10201` | Solo referencias históricas |
| Transcriptor | React/Vite, FastAPI, PostgreSQL y worker de trabajos | Subida efímera o persistente, acción única `transcription_job` | `transcriptor.carlosrevert.es`, web `10300`, API `10301`, DB `10310` | Adaptador backend aislado e inoperante; documentación legacy |
| Accounts | Django, DRF y PostgreSQL | Reserva global, validación exacta una vez y callbacks `complete/fail` | `cuenta.carlosrevert.es`, web `10401`, DB local `10410` | Sistema nuevo; no importa usuarios ni datos |

## Contrato común

El navegador consulta Django con cookie compartida `.carlosrevert.es`, `credentials: include` y CSRF. Cada acción de IA crea un UUID y reserva cuota. El backend receptor exige ese UUID y lo valida con una credencial exclusiva de su aplicación antes de invocar el proveedor. Accounts no disponible, UUID ausente/falso/reutilizado, acción manipulada o credencial cruzada producen fallo cerrado.

La Home no reserva. FREE comparte 5 interacciones diarias y PREMIUM 20 entre Juridia, CLARK y Transcriptor. Los secretos internos solo existen en los `.env` de backend.

## Cambios entregados

- Accounts: `a000586`, `2a98d44`, `2a2ca53`, `67155f2`, `71e5dee`.
- Juridia: `d15e8cf`, `a025547`.
- Home: `8f92cb7`, `94a8653`, `447b979`.
- CLARK: `748a635`.
- Transcriptor: `441b47f`, `ff2c7b7`.

Los detalles de variables, flujos y operación viven en `docs/accounts-integration.md` o `DOCS/accounts-integration.md` dentro de cada repositorio.
