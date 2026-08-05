# Arquitectura de Carlos Revert Accounts

> **Una cuenta, una sesión y una cuota compartida** para Home, Juridia, CLARK y Transcriptor.

| Papel | Tecnología | Responsabilidad |
| :-- | :-- | :-- |
| **Servicio central** | Django 5 + Django REST Framework | Identidad, sesiones, planes y consumo |
| **Persistencia** | PostgreSQL | Usuarios, planes, reservas y auditoría |
| **Clientes** | Aplicaciones web y backends de IA | Solicitan sesión y consumen reservas validadas |
| **Operación** | Docker + Django Admin | Despliegue, administración y métricas |

---

## Mapa rápido

```mermaid
flowchart LR
    U([Usuario]) --> W[Home · Juridia · CLARK · Transcriptor]
    W -->|Sesión + CSRF| A[🛡️ Carlos Revert Accounts]
    W -->|POST /api/v1/usage/reserve/| A
    A --> Q[⚙️ Servicio de cuota]
    Q --> DB[(🗄️ PostgreSQL)]
    I[Backends de IA] -->|Clave de aplicación| A
    A -->|Reserva validada| I
    D[👩‍💼 Django Admin] --> A

    classDef client fill:#0ea5e9,stroke:#0369a1,color:#ffffff;
    classDef core fill:#6366f1,stroke:#4338ca,color:#ffffff;
    classDef data fill:#10b981,stroke:#047857,color:#ffffff;
    classDef internal fill:#f59e0b,stroke:#b45309,color:#111827;
    class W client;
    class A,Q core;
    class DB data;
    class I,D internal;
```

El repositorio **no procesa las respuestas de IA**. Es la autoridad común que decide quién puede usar los productos, con qué plan y cuántas interacciones puede realizar.

---

## Las cuatro capas

```text
┌─────────────────────────────────────────────────────────────┐
│  1. PRESENTACIÓN                                              │
│  Páginas Django, formularios, sesión y panel Mi cuenta        │
├─────────────────────────────────────────────────────────────┤
│  2. API V1                                                    │
│  Registro, login, perfil, reserva, historial y métricas       │
├─────────────────────────────────────────────────────────────┤
│  3. DOMINIO                                                    │
│  Planes, cuota compartida, idempotencia y ciclo de eventos    │
├─────────────────────────────────────────────────────────────┤
│  4. INFRAESTRUCTURA                                            │
│  PostgreSQL, caché de límites, Docker y configuración         │
└─────────────────────────────────────────────────────────────┘
```

| Capa | Dónde leerla | Idea clave |
| :-- | :-- | :-- |
| Rutas | [`config/urls.py`](config/urls.py) | Separa la web, `/api/v1/`, salud y OpenAPI. |
| API | [`apps/api/`](apps/api/) | Expone el contrato consumido por web y servicios internos. |
| Dominio | [`apps/usage/services/quota_service.py`](apps/usage/services/quota_service.py) | Protege el contador frente a reintentos y concurrencia. |
| Datos | [`apps/*/models.py`](apps/) | Modela usuarios, planes, aplicaciones y auditoría. |
| Pruebas | [`tests/`](tests/) | Verifica permisos, cuota, correo y endurecimiento de producción. |

---

## Flujo 1 · Crear y usar una cuenta

```mermaid
sequenceDiagram
    autonumber
    participant U as Usuario
    participant C as Cliente web
    participant A as Accounts
    participant P as PostgreSQL

    U->>C: Registro
    C->>A: POST /auth/register/
    A->>P: Crea User + plan FREE
    A-->>U: Envía código de verificación
    U->>C: Introduce código
    C->>A: POST /auth/verify-email/
    A->>P: Marca email_verified=True
    A-->>C: Crea sesión Django
```

La sesión se comparte bajo los subdominios autorizados. Por ello, una misma cuenta puede entrar en los distintos productos sin crear identidades duplicadas.

---

## Flujo 2 · Consumir una interacción de IA

```mermaid
sequenceDiagram
    autonumber
    participant W as Aplicación web
    participant A as Accounts API
    participant D as PostgreSQL
    participant I as Backend de IA

    W->>A: Reserva con request_id único
    A->>D: Crea InteractionReservation
    A->>D: Bloquea DailyUsage del usuario y día
    alt Hay cuota disponible
        A->>D: Incrementa contador y crea UsageEvent autorizado
        A-->>W: Autorizada + cuota restante
        I->>A: Valida reserva con clave de aplicación
        A->>D: authorized → processing
        A-->>I: Reserva válida
        I->>A: Completa o informa fallo
        A->>D: Actualiza evento final
    else Sin cuota
        A->>D: Registra evento rechazado
        A-->>W: HTTP 429 daily_quota_exceeded
    end
```

### Por qué este flujo es robusto

- **Transaccional:** `transaction.atomic()` agrupa cada reserva para que no exista un incremento a medias.
- **Seguro ante concurrencia:** `select_for_update()` bloquea el contador diario mientras se actualiza.
- **Idempotente:** repetir el mismo `request_id` devuelve la reserva original; no cobra dos veces.
- **Trazable:** cada intento genera un `UsageEvent`, incluido un rechazo por falta de cuota.
- **Aislado por aplicación:** el backend de Juridia no puede validar una reserva creada para CLARK.

---

## Modelo de datos

```mermaid
erDiagram
    USER ||--|| USER_PLAN : tiene
    PLAN ||--o{ USER_PLAN : asigna
    USER ||--o{ DAILY_USAGE : acumula
    USER ||--o{ USAGE_EVENT : realiza
    CLIENT_APPLICATION ||--o{ USAGE_EVENT : origina
    USAGE_EVENT ||--|| INTERACTION_RESERVATION : protege

    USER {
        string email UK
        boolean email_verified
        boolean is_blocked
    }
    PLAN {
        string code UK
        int daily_interaction_limit
    }
    DAILY_USAGE {
        date date
        int interaction_count
    }
    USAGE_EVENT {
        uuid request_id UK
        string status
        string action
    }
```

| Entidad | Responde a |
| :-- | :-- |
| `User` | ¿Quién es la persona y puede usar el servicio? |
| `Plan` / `UserPlan` | ¿Cuál es su límite diario? |
| `DailyUsage` | ¿Cuántas interacciones ha usado hoy? |
| `InteractionReservation` | ¿Este reintento ya se procesó? |
| `UsageEvent` | ¿Qué ocurrió durante el ciclo de la interacción? |
| `ClientApplication` | ¿Qué producto solicita la operación y tiene autorización interna? |

---

## Estados de una interacción

```mermaid
stateDiagram-v2
    [*] --> authorized: cuota reservada
    authorized --> processing: backend valida
    processing --> completed: trabajo terminado
    processing --> failed: error técnico
    authorized --> rejected_auth: cuenta o aplicación no válida
    [*] --> rejected_quota: límite diario agotado
    failed --> [*]
    completed --> [*]
    rejected_auth --> [*]
    rejected_quota --> [*]
```

> Los errores configurados como previos al procesamiento pueden devolver una unidad de cuota. Los demás permanecen registrados como consumo porque el proveedor de IA ya pudo haber trabajado.

---

## Seguridad incorporada

| Protección | Aplicación práctica |
| :-- | :-- |
| Sesión segura | Cookies `Secure`, `HttpOnly` y CSRF para operaciones con sesión. |
| Verificación de correo | Código de un solo uso, caducidad y límites de reenvío/intentos. |
| Antifraude | Rate limiting por IP e identificador; solo se confía en proxies declarados. |
| Servicios internos | Cabeceras de aplicación + clave guardada como hash. |
| Privacidad | Los metadatos eliminan prompts, respuestas y cuerpos sensibles. |
| Auditoría | Historial de planes, eventos de consumo y métricas agregadas. |

---

## Recorrido recomendado del código

1. [`README.md`](README.md): visión global y comandos de operación.
2. [`config/urls.py`](config/urls.py): todos los puntos de entrada.
3. [`apps/api/views.py`](apps/api/views.py): contrato HTTP y permisos por endpoint.
4. [`apps/usage/services/quota_service.py`](apps/usage/services/quota_service.py): núcleo de negocio.
5. [`apps/usage/models.py`](apps/usage/models.py): reserva, contador y auditoría.
6. [`tests/test_quota.py`](tests/test_quota.py) y [`tests/test_api_permissions.py`](tests/test_api_permissions.py): evidencia automatizada de los casos críticos.

---

## Idea final

**Accounts convierte varios productos de IA en una plataforma coherente:** una identidad verificable, planes configurables, cuota común y un registro fiable de cada operación.
