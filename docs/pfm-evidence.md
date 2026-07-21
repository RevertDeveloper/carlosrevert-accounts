# Evidencias de integración

Verificación ejecutada el 21 de julio de 2026 contra los servicios desplegados.

## Sesión y navegación

- Registro y login reales en Cuenta; la misma cookie mostró sesión autenticada en Home, Juridia, CLARK y Transcriptor.
- Logout iniciado desde Transcriptor dejó anónimas las cuatro webs.
- Las cuatro webs permanecieron navegables sin cuenta y mostraron acceso/registro.
- Home obtuvo `/auth/me/`, `/usage/summary/` y `/applications/` sin reservar cuota.

## Cuota compartida

- Usuario FREE desde cero: reservas válidas repartidas como Juridia 2, CLARK 2 y Transcriptor 1; total `5/5`.
- Sexta reserva en Juridia: HTTP 429 `daily_quota_exceeded`.
- Cambio manual a PREMIUM mediante el mismo servicio usado por Admin: resumen `5/20`.
- Quince reservas adicionales autorizadas; la interacción 21 devolvió 429 y el resumen quedó `20/20`.
- Repetir un `request_id` autorizado no incrementa el contador; la suite lo prueba sobre PostgreSQL.

## Seguridad y E2E de IA

- Juridia: registro, reserva, validación, RAG NDJSON y evento final `completed`. Sin UUID 401, UUID falso 404 y clave falsa 403.
- CLARK: reserva y stream real de 50 eventos SSE; evento `completed`. UUID falso 404 y reutilización rechazada.
- Transcriptor: audio sintético, `QUEUED -> PROCESSING -> COMPLETED`, transcripción e informe generados; evento `completed`. Sin UUID 401, falso 404 y reutilizado 409.
- Una clave real de CLARK usada contra una reserva de Juridia devolvió 403.
- Los clientes internos prueban timeout/indisponibilidad de Accounts y fallan cerrados antes de IA. Los errores previos al proveedor usan `before_processing`; los posteriores permanecen consumidos.

## Automatización y despliegue

- Accounts: 18 pruebas tras retirar la importación legacy; Django checks y PostgreSQL real.
- Juridia: 23 pruebas de integración; suite global 188 pass, 10 skip, con 20 fallos preexistentes no relacionados.
- Home: 2 pruebas, ESLint y build Vite.
- CLARK: 3 pruebas backend, 14 pruebas frontend focalizadas, lint, tipos y build.
- Transcriptor: 80 pruebas backend y 39 frontend; build y lint de los archivos integrados.
- UI de las cuatro aplicaciones revisada en escritorio y móvil sin overflow ni errores de consola en los flujos de cuenta.
- Todos los dominios respondieron por HTTPS y los contenedores críticos quedaron `healthy` con política de reinicio persistente.

El dashboard de Django Admin ofrece usuarios, asignaciones de plan y eventos. `/api/v1/admin/metrics/` aporta consumo por aplicación, estados, rechazos y usuarios activos sin exponer prompts, respuestas, audio ni credenciales.
