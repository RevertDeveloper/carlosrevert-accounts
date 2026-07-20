# Política de cuota

FREE dispone de 5 y PREMIUM de 20 interacciones por día local. El contador es único por usuario y día y suma todas las aplicaciones con `consumes_quota=True`. Una aplicación como Home puede estar registrada sin consumir.

```mermaid
sequenceDiagram
  participant A as Aplicación
  participant Q as Servicio de cuota
  participant D as PostgreSQL
  A->>Q: reserve(request_id)
  Q->>D: crea reserva idempotente y bloquea DailyUsage
  alt hay cuota
    Q->>D: incrementa contador y crea UsageEvent autorizado
    Q-->>A: autorizado
  else sin cuota
    Q->>D: crea UsageEvent rechazado
    Q-->>A: 429
  end
```

Un fallo `before_processing` reembolsa una reserva porque se produjo antes de usar recursos del modelo. Otros fallos permanecen consumidos. La lista puede cambiarse con `QUOTA_REFUNDABLE_ERROR_CODES`.
