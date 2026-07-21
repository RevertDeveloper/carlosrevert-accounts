# API v1

Los endpoints de sesión usan cookie y requieren `credentials: 'include'`. Antes de un POST desde otro subdominio, solicita `GET /api/v1/auth/csrf/` y envía el valor de la cookie `csrftoken` como `X-CSRFToken`.

| Ruta | Método | Acceso |
|---|---|---|
| `/auth/me/` | GET | Público |
| `/auth/register/`, `/auth/login/` | POST | Público, limitado por IP |
| `/auth/logout/` | POST | Sesión |
| `/usage/summary/`, `/usage/history/` | GET | Sesión |
| `/usage/reserve/` | POST | Sesión, limitado por usuario |
| `/usage/{id}/complete/`, `/fail/` | POST | Credencial interna |
| `/internal/usage/validate/` | POST | Credencial interna por aplicación |
| `/applications/` | GET | Público |
| `/admin/metrics/` | GET | Staff |

Reserva: `{"application":"juridia","action":"legal_query","request_id":"UUID"}`. Antes de ejecutar IA, el backend valida esa reserva una sola vez en `/internal/usage/validate/`. Los callbacks internos deben mandar `X-Application-Slug` y `X-Service-Key`, con una clave distinta por aplicación y rotada desde Admin. El esquema OpenAPI es la fuente de contrato viva.
