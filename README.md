# Carlos Revert Accounts

Servicio central Django para identidad, cuentas, planes y cuota de procesos de IA de `carlosrevert.es`, Juridia, CLARK y Transcriptor. Las aplicaciones públicas conservan sus propios backends: este repositorio es exclusivamente la autoridad de identidad y consumo.

## Arquitectura

- Django 5, Django REST Framework y PostgreSQL.
- Sesiones Django con cookie HttpOnly compartible bajo `*.carlosrevert.es` en producción.
- API versionada bajo `/api/v1/`, OpenAPI en `/api/schema/` y Swagger en `/api/docs/`.
- Motor de cuota transaccional e idempotente por `request_id`.
- Docker: web `10401`, PostgreSQL solo local `127.0.0.1:10410`.

## Inicio local

```bash
cp .env.example .env
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements/local.txt
python manage.py migrate
python manage.py seed_plans
python manage.py seed_applications
python manage.py createsuperuser
python manage.py runserver
```

Para desarrollo Docker con código montado, usa explícitamente `docker compose -f compose.yaml -f compose.dev.yaml up`.

## Docker

```bash
cp .env.example .env
# Establece un POSTGRES_PASSWORD y un DJANGO_SECRET_KEY seguros.
docker compose -f compose.yaml up --build
```

El proxy inverso debe dirigir `cuenta.carlosrevert.es` a `:10401`. Consulta [despliegue](docs/deployment.md).

La documentación transversal incluye el [tour completo de producción](docs/production-tour.md), el [inventario de aplicaciones](docs/integration-inventory.md), las [evidencias E2E](docs/pfm-evidence.md) y el [procedimiento de rollback](docs/rollback.md).

## API principal

- `GET /api/v1/auth/me/`
- `GET /api/v1/auth/csrf/`
- `POST /api/v1/auth/register/`, `verify-email/`, `verify-email/resend/`, `login/`, `logout/`
- `GET /api/v1/usage/summary/`, `history/`
- `POST /api/v1/usage/reserve/`
- `POST /api/v1/usage/{request_id}/complete/` y `fail/` para servicios internos
- `GET /api/v1/applications/`
- `GET /api/v1/admin/metrics/` para staff

Consulta [la referencia completa](docs/api.md).

## Operación

```bash
ruff check .
ruff format --check .
pytest
python manage.py check
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py check --deploy
```

Los planes se editan desde Django Admin. Los comandos `seed_plans` y `seed_applications` son idempotentes. Las cuentas se crean desde cero en Django; no existe migración ni importación desde Keycloak.

## Seguridad y límites

FREE recibe 5 interacciones/día; PREMIUM, 20. El contador es común a todas las aplicaciones que consumen cuota. Las reservas se bloquean en base de datos, usan `request_id` idempotente y devuelven 429 cuando se supera el límite. No se registran prompts ni respuestas en los eventos por defecto. Consulta [seguridad](docs/security.md) y [política de cuota](docs/quota-policy.md).

## Limitaciones y evolución

No hay pagos ni migración de identidades Keycloak. El cambio de PREMIUM es manual en Admin. El correo de verificación usa códigos de un solo uso y límites en la caché PostgreSQL; Redis distribuido queda como evolución para gran escala.
