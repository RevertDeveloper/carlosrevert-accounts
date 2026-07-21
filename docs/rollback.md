# Rollback

El estado normal de producción exige Accounts. Los flags `DJANGO_ACCOUNTS_ENABLED=false` de las aplicaciones son solo una medida temporal de diagnóstico; no deben dejar un backend de IA abierto de forma permanente.

## Accounts

1. Conserva `.env` y el volumen `postgres_data`; nunca los incluyas en Git.
2. Vuelve al commit o imagen conocido y ejecuta `docker compose -f compose.yaml up -d --build web`.
3. Ejecuta `docker compose -f compose.yaml exec web python manage.py migrate` si la versión lo requiere.
4. Comprueba `/health/`, `/api/v1/auth/me/`, el estado `healthy`, la política `unless-stopped` y una reserva real.

Las migraciones actuales son aditivas. No elimines columnas ni el volumen durante un rollback.

## Aplicaciones

Repliega solo el frontend/backend del repositorio afectado desde su commit anterior. Conserva las bases de datos propias. Si una incidencia obliga a desactivar temporalmente la integración, restringe o detén antes el endpoint de IA para que no exista un bypass público. Restablece `DJANGO_ACCOUNTS_ENABLED=true`, recrea el backend y valida una reserva completa antes de reabrirlo.

## Credenciales

Ante exposición o duda, rota únicamente la clave de `ClientApplication` afectada en Django Admin, actualiza su `.env` y recrea ese backend. Una clave de otra aplicación nunca debe servir como sustituta.
