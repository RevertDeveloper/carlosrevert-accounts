# Arquitectura

```mermaid
flowchart LR
  PublicApps[Home / Juridia / CLARK / Transcriptor] -->|Cookie de sesión + CSRF| Accounts[Django Accounts]
  PublicApps -->|reserve| API[API v1]
  API --> Quota[Servicio de cuota]
  Quota --> PG[(PostgreSQL)]
  Admin[Django Admin] --> PG
  Internal[Backends IA] -->|clave de aplicación| API
```

Los límites viven en `Plan`, no en código. `UserPlan` es uno a uno, `DailyUsage` es único por usuario y fecha y `UsageEvent` mantiene el historial. `InteractionReservation` se crea antes de cualquier incremento para hacer idempotente el `request_id` bajo concurrencia.
