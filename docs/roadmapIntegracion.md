# Roadmap técnico — Integración del sistema Django de usuarios con las aplicaciones

## 1. Propósito del documento

Este documento define cómo integrar el servicio central Django de usuarios, cuentas, planes y cuotas con las siguientes aplicaciones:

- `https://carlosrevert.es` /home/revert/Repositorios/dev_tanian/Home
- `https://juridia.carlosrevert.es` /home/revert/Repositorios/boe/juridia/production/app
- `https://clark.carlosrevert.es` /home/revert/Repositorios/RevertDev/NCElevacion
- `https://transcriptor.carlosrevert.es` /home/revert/Repositorios/dev_tanian/transcriptor

Está diseñado para ser entregado a un agente de IA de desarrollo. El agente debe analizar cada repositorio, aplicar los cambios de integración, añadir pruebas y documentar la configuración sin reescribir la lógica principal de las aplicaciones.

El servicio Django central se asumirá publicado en:

```text
https://cuenta.carlosrevert.es
```

---

## 2. Resultado esperado

Al finalizar la integración:

1. Todas las webs serán públicas y navegables sin cuenta.
2. Todas mostrarán opciones coherentes de:
   - Registrarse.
   - Iniciar sesión.
   - Ver la cuenta.
   - Cerrar sesión.
   - Volver a `carlosrevert.es`.
3. Solo los usuarios autenticados podrán lanzar procesos de IA.
4. Los usuarios FREE dispondrán de cinco interacciones diarias totales.
5. Los usuarios PREMIUM dispondrán de veinte interacciones diarias totales.
6. El límite se compartirá entre Juridia, CLARK y Transcriptor.
7. La Home no consumirá interacciones por navegación.
8. El usuario verá su plan, uso y saldo restante.
9. La autenticación se compartirá entre subdominios.
10. Ningún frontend podrá saltarse la cuota llamando directamente a un backend público.

---

## 3. Principios de integración

### 3.1. No reescribir las aplicaciones

No migrar las aplicaciones existentes a Django.

Mantener:

- Frontends actuales.
- Backends actuales.
- Bases de datos actuales.
- Sistemas RAG.
- Colas de procesamiento.
- Modelos de IA.
- Flujos funcionales existentes.

Solo modificar:

- Navegación común.
- Estado de autenticación.
- Protección de acciones de IA.
- Reserva y registro de cuota.
- Comunicación segura con Django.
- Tratamiento de errores de autenticación y cuota.

### 3.2. Django es la autoridad

Las aplicaciones no deben decidir localmente si un usuario es FREE o PREMIUM.

Django será la fuente única de verdad para:

- Sesión.
- Usuario.
- Plan.
- Límite.
- Consumo.
- Bloqueo.
- Autorización de interacción.

### 3.3. Los backends de IA no deben confiar en el navegador

No es suficiente con ocultar botones en React.

La autorización debe comprobarse en servidor antes de ejecutar IA.

### 3.4. El backend de IA debe quedar protegido

Cuando sea posible:

- Retirar la exposición pública directa del backend de IA.
- Exponer solo el frontend y el servicio Django.
- Comunicar servicios mediante red privada Docker, LAN o Tailscale.

---

## 4. Arquitectura objetivo

```text
Navegador
   │
   ├── carlosrevert.es
   ├── juridia.carlosrevert.es
   ├── clark.carlosrevert.es
   ├── transcriptor.carlosrevert.es
   └── cuenta.carlosrevert.es
          │
          ▼
Servicio Django central
- sesión
- usuario
- plan
- cuota
- auditoría
          │
          ├── autoriza Juridia
          ├── autoriza CLARK
          └── autoriza Transcriptor
                  │
                  ▼
Backends internos de IA
```

---

## 5. Estrategia de autenticación entre subdominios

## 5.1. Estrategia preferida

Usar sesiones Django con cookie compartida para:

```text
.carlosrevert.es
```

Configuración esperada en Django:

```python
SESSION_COOKIE_DOMAIN = ".carlosrevert.es"
CSRF_COOKIE_DOMAIN = ".carlosrevert.es"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
```

Los frontends harán peticiones a Django con credenciales:

```javascript
fetch("https://cuenta.carlosrevert.es/api/v1/auth/me/", {
  credentials: "include",
});
```

No guardar tokens de sesión en `localStorage`.

## 5.2. CORS y CSRF

Django debe permitir únicamente:

```text
https://carlosrevert.es
https://juridia.carlosrevert.es
https://clark.carlosrevert.es
https://transcriptor.carlosrevert.es
https://cuenta.carlosrevert.es
```

Para peticiones mutables:

- Obtener cookie CSRF.
- Enviar `X-CSRFToken`.
- Enviar `credentials: include`.

## 5.3. Fallback

Si las sesiones compartidas no funcionan correctamente por la arquitectura de frontend o proxy, implementar un flujo de token de corta duración.

El fallback debe:

- Evitar tokens permanentes.
- Evitar almacenamiento en `localStorage` cuando sea posible.
- Usar cookies HttpOnly para refresh.
- Rotar refresh tokens.
- Mantener Django como emisor y autoridad.

No implementar el fallback salvo que la estrategia de sesión sea técnicamente inviable.

---

## 6. Cliente compartido de autenticación

Crear en cada frontend un módulo equivalente a:

```text
src/lib/accounts-client.ts
```

Interfaz mínima:

```typescript
export interface AuthUser {
  id: number;
  username: string;
  email: string;
  plan: "FREE" | "PREMIUM";
}

export interface UsageSummary {
  plan: "FREE" | "PREMIUM";
  daily_limit: number;
  used_today: number;
  remaining_today: number;
  resets_at: string;
}

export async function getCurrentUser(): Promise<AuthUser | null>;
export async function getUsageSummary(): Promise<UsageSummary>;
export async function reserveInteraction(input: ReserveInput): Promise<ReserveResult>;
export async function logout(): Promise<void>;
```

### Requisitos

- URL base obtenida de variable de entorno.
- Timeout.
- Tratamiento uniforme de 401, 403, 429 y 5xx.
- Nunca incluir secretos internos en el bundle frontend.
- Pruebas unitarias del cliente.

Variable sugerida:

```text
VITE_ACCOUNTS_API_URL=https://cuenta.carlosrevert.es/api/v1
```

Para Next.js adaptar el prefijo de variable según el framework.

---

## 7. Estado global de autenticación

Crear un contexto, store o provider común en cada aplicación:

```text
AuthProvider
```

Estado mínimo:

```typescript
{
  loading: boolean;
  authenticated: boolean;
  user: AuthUser | null;
  usage: UsageSummary | null;
  refreshAuth: () => Promise<void>;
  refreshUsage: () => Promise<void>;
  logout: () => Promise<void>;
}
```

Comportamiento:

1. Al cargar la aplicación, llamar a `/auth/me/`.
2. Si el usuario está autenticado, cargar `/usage/summary/`.
3. No bloquear la navegación pública mientras se resuelve la sesión.
4. Mostrar skeleton o indicador solo en componentes dependientes de cuenta.
5. Actualizar el consumo tras cada interacción.

---

## 8. Navegación común

Todas las aplicaciones deben mostrar una navegación coherente.

### Elementos mínimos

- Logo o nombre de Carlos Revert.
- Botón `Inicio` hacia `https://carlosrevert.es`.
- Selector o enlaces a proyectos.
- Estado de cuenta.

### Usuario anónimo

```text
Registrarse | Iniciar sesión
```

Enlaces:

```text
https://cuenta.carlosrevert.es/register/?next=<url-actual>
https://cuenta.carlosrevert.es/login/?next=<url-actual>
```

### Usuario autenticado

```text
Mi cuenta | Cerrar sesión
```

Mostrar opcionalmente:

```text
FREE · 3/5
PREMIUM · 8/20
```

### Redirección posterior al login

Django debe validar el parámetro `next` para evitar open redirects.

Solo aceptar destinos bajo:

```text
carlosrevert.es
*.carlosrevert.es
```

---

## 9. Protección de acciones de IA

Crear un componente o función reutilizable:

```text
requireAuthenticatedInteraction
```

Flujo esperado:

1. Usuario pulsa el botón que lanza IA.
2. El frontend comprueba el estado local.
3. Si es anónimo:
   - No ejecutar la acción.
   - Mostrar modal de autenticación.
   - Ofrecer registro o login.
4. Si está autenticado:
   - Generar un `request_id` UUID v4.
   - Solicitar reserva a Django.
5. Si Django autoriza:
   - Enviar la petición al backend correspondiente.
6. Si Django devuelve 429:
   - No llamar al backend de IA.
   - Mostrar el límite alcanzado.
7. Al terminar:
   - El backend informa a Django del resultado.
   - El frontend actualiza el resumen de uso.

El frontend no puede ser la única capa que realiza este flujo.

---

## 10. Patrón de integración servidor a servidor

### Opción recomendada

Cada backend de aplicación debe validar una reserva emitida por Django antes de procesar.

Flujo:

```text
Frontend
  -> Django: reserveInteraction
  <- Django: request_id autorizado
Frontend
  -> Backend de aplicación: payload + request_id
Backend de aplicación
  -> Django interno: validar request_id
  <- Django: válido, usuario, aplicación, acción
Backend procesa IA
Backend
  -> Django interno: complete o fail
```

### Endpoint interno de validación

Django debe exponer un endpoint protegido, por ejemplo:

```http
POST /api/v1/internal/usage/validate/
```

Entrada:

```json
{
  "request_id": "uuid",
  "application": "juridia",
  "action": "legal_query"
}
```

Salida:

```json
{
  "valid": true,
  "user_id": 12,
  "plan": "FREE"
}
```

### Autenticación interna

Cada backend debe usar una credencial diferente:

```text
JURIDIA_SERVICE_TOKEN
CLARK_SERVICE_TOKEN
TRANSCRIPTOR_SERVICE_TOKEN
```

No incluir estas claves en frontend.

### Idempotencia

- El mismo `request_id` no puede procesarse dos veces.
- Django debe registrar estado.
- El backend debe rechazar una repetición si la operación ya está en curso o completada.

---

## 11. Integración de `carlosrevert.es`

## 11.1. Función de la Home

La Home será:

- Portfolio.
- Catálogo de aplicaciones.
- Punto de entrada común.
- Acceso a cuenta.
- Explicación de planes.

No consumirá cuota por navegar.

## 11.2. Cambios obligatorios

- Añadir estado de sesión.
- Añadir botones Registro/Login o Cuenta/Logout.
- Mostrar tarjetas para Juridia, CLARK y Transcriptor.
- Mostrar claramente qué acciones requieren cuenta.
- Añadir sección de planes:
  - FREE: 5 interacciones diarias.
  - PREMIUM: 20 interacciones diarias.
- Aclarar que Premium se asigna manualmente durante esta fase.
- Añadir enlace a privacidad y términos.

## 11.3. Consumo de API Django

La Home debe consumir al menos:

```text
GET /api/v1/auth/me/
GET /api/v1/usage/summary/
GET /api/v1/applications/
```

Esto ayudará a demostrar integración real de React con Django en el PFM.

## 11.4. Criterios de aceptación

- [ ] Visitante puede navegar.
- [ ] Visitante ve login y registro.
- [ ] Usuario autenticado ve cuenta y plan.
- [ ] Los enlaces a las apps funcionan.
- [ ] Logout invalida sesión para todos los subdominios.

---

## 12. Integración de Juridia

Juridia será la aplicación principal del PFM y debe recibir la integración más completa.

## 12.1. Acciones que consumen cuota

Identificar todos los procesos de IA. Como mínimo:

```text
legal_query
```

Si existen otras acciones:

```text
document_analysis
query_expansion
report_generation
```

No contabilizar procesos internos auxiliares como interacciones independientes salvo decisión explícita. Una acción de usuario debe consumir normalmente una única interacción, aunque internamente utilice varias llamadas de IA.

## 12.2. Cambios frontend

- Añadir navegación común.
- Añadir `AuthProvider`.
- Mostrar plan y saldo.
- Proteger el botón principal de consulta.
- Conservar la consulta escrita al redirigir al login.
- Mostrar modal de autenticación al visitante.
- Mostrar mensaje específico al superar cuota.
- Actualizar contador tras respuesta.

Mensaje sugerido para anónimo:

```text
Necesitas una cuenta para realizar consultas jurídicas. El registro gratuito incluye 5 interacciones diarias.
```

Mensaje sugerido para límite:

```text
Has alcanzado el límite diario de tu plan. Podrás volver a consultar cuando se reinicie la cuota.
```

## 12.3. Cambios backend

- Exigir `request_id` en el endpoint de consulta.
- Validar `request_id` con Django antes de ejecutar RAG o LLM.
- Rechazar peticiones no autorizadas.
- Informar a Django al completar o fallar.
- Añadir timeout y reintentos controlados para llamadas a Django.
- No registrar documentos sensibles en logs.

## 12.4. Exposición de red

- Mantener el frontend público.
- Mantener el backend detrás de proxy o red privada cuando sea posible.
- Si el backend debe seguir público, exigir reserva válida y autenticación interna.

## 12.5. Pruebas

- Visitante puede abrir Juridia.
- Visitante no puede consultar.
- FREE puede consultar cinco veces sumando todas las apps.
- Sexta consulta rechazada.
- PREMIUM puede consultar hasta veinte.
- `request_id` inválido rechazado.
- `request_id` reutilizado rechazado.
- Error del LLM se notifica a Django.
- El frontend actualiza el saldo.

## 12.6. Criterio de aceptación

Juridia debe demostrar el flujo completo en la defensa del PFM:

```text
registro -> login -> consulta -> Django autoriza -> RAG responde -> consumo se actualiza
```

---

## 13. Integración de CLARK

## 13.1. Acciones públicas

Deben seguir públicas:

- Navegación del catálogo.
- Fichas de producto.
- Filtros.
- Comparador manual.
- Información de empresa.
- Carrito o preparación de presupuesto no basada en IA, si existe.

## 13.2. Acciones que consumen cuota

Identificar, por ejemplo:

```text
product_ai_query
assistant_recommendation
quote_ai_assistance
```

Una conversación puede contabilizarse:

- Por mensaje enviado por el usuario, o
- Por tarea completa.

Para mantener coherencia con Juridia, usar una interacción por acción explícita del usuario que active IA.

## 13.3. Cambios frontend

- Navegación común.
- Estado de cuenta.
- Protección del asistente IA.
- Modal de login.
- Indicador de saldo.
- Tratamiento de 429.

## 13.4. Cambios backend

- Requerir `request_id`.
- Validar con Django.
- Informar complete/fail.
- No permitir acceso directo sin reserva.

## 13.5. Pruebas

- Catálogo público.
- Asistente bloqueado para anónimo.
- Cuota compartida con Juridia.
- Errores tratados sin romper el catálogo.

---

## 14. Integración de Transcriptor

## 14.1. Acciones públicas

Pueden ser públicas:

- Landing.
- Explicación del servicio.
- Formatos soportados.
- Información de privacidad.

## 14.2. Acción que consume cuota

Definir una unidad clara:

```text
transcription_job
```

Una subida y procesamiento completo debe consumir una interacción, aunque internamente incluya:

- Conversión de audio.
- STT.
- Resumen.
- Generación de informe.

No cobrar una interacción distinta por cada paso interno.

## 14.3. Momento de reserva

Reservar antes de aceptar definitivamente el trabajo.

Flujo:

1. Usuario selecciona fichero.
2. Validación local de tipo y tamaño.
3. Reserva de interacción.
4. Subida del fichero.
5. Validación del backend.
6. Inicio del trabajo.
7. Complete/fail en Django.

Si la subida falla antes de que el backend acepte el trabajo, aplicar la política de reembolso definida por Django.

## 14.4. Privacidad

- No enviar audio a Django.
- Django solo almacena metadatos mínimos.
- El fichero debe permanecer en el backend de Transcriptor.
- No incluir nombres de archivo sensibles en logs salvo necesidad.
- Documentar retención y borrado.

## 14.5. Pruebas

- Landing pública.
- Subida bloqueada para anónimo.
- Reserva antes del procesamiento.
- Error de formato no debe consumir si no se inicia trabajo.
- Trabajo aceptado consume una interacción.
- Estado se actualiza en Django.

---

## 15. UX común para autenticación y cuota

Crear patrones consistentes.

### Modal de autenticación

Contenido:

```text
Inicia sesión para continuar

Las herramientas pueden explorarse libremente. Para ejecutar procesos de IA necesitas una cuenta.

Plan FREE: 5 interacciones diarias.
Plan PREMIUM: 20 interacciones diarias.
```

Botones:

```text
Crear cuenta
Iniciar sesión
Cancelar
```

### Indicador de cuota

FREE:

```text
3 de 5 utilizadas hoy
```

PREMIUM:

```text
8 de 20 utilizadas hoy
```

### Límite alcanzado

Mostrar:

- Plan.
- Límite.
- Consumo.
- Hora de reinicio.
- Enlace a cuenta.

No mostrar mensajes genéricos como `Error 429` al usuario final.

---

## 16. Gestión de errores

Los clientes deben normalizar:

| HTTP | Código | Comportamiento |
|---:|---|---|
| 401 | `authentication_required` | Mostrar login |
| 403 | `account_blocked` o `forbidden` | Bloquear acción y explicar |
| 409 | `request_already_used` | Evitar duplicado |
| 429 | `daily_quota_exceeded` | Mostrar límite |
| 502/503 | `accounts_unavailable` | No ejecutar IA y permitir reintento |
| 504 | `service_timeout` | Informar sin duplicar consumo |

### Regla de seguridad

Si Django no está disponible, las aplicaciones deben fallar de forma cerrada:

```text
No ejecutar procesos de IA sin autorización.
```

La navegación pública debe continuar funcionando.

---

## 17. Variables de entorno por aplicación

### Frontend

```text
ACCOUNTS_PUBLIC_URL=https://cuenta.carlosrevert.es
ACCOUNTS_API_URL=https://cuenta.carlosrevert.es/api/v1
APP_SLUG=juridia|clark|transcriptor|home
```

Adaptar nombres al framework:

- `VITE_*` para Vite.
- `NEXT_PUBLIC_*` para Next.js.

### Backend

```text
ACCOUNTS_INTERNAL_API_URL=
ACCOUNTS_SERVICE_TOKEN=
APP_SLUG=
ACCOUNTS_TIMEOUT_SECONDS=5
```

Nunca exponer `ACCOUNTS_SERVICE_TOKEN` en el frontend.

---

## 18. Nginx Proxy Manager y red

## 18.1. Proxy hosts públicos

Mantener:

```text
carlosrevert.es
juridia.carlosrevert.es
clark.carlosrevert.es
transcriptor.carlosrevert.es
cuenta.carlosrevert.es
```

Todos con:

- HTTPS.
- Force SSL.
- HTTP/2.
- Certificado válido.

## 18.2. APIs internas

Preferir:

- Red Docker compartida.
- LAN privada.
- Tailscale entre VMs.

No publicar los endpoints internos de Django en Internet cuando puedan limitarse a red privada.

## 18.3. Cabeceras proxy

Asegurar:

```text
X-Forwarded-Proto
X-Forwarded-For
Host
```

Django debe confiar correctamente en el proxy HTTPS mediante su configuración de seguridad.

---

## 19. Migración desde Keycloak

## 19.1. Retirada progresiva

No eliminar Keycloak hasta validar la nueva integración.

Secuencia:

1. Levantar Django en paralelo.
2. Integrar primero la Home.
3. Integrar Juridia.
4. Validar sesiones y cuotas.
5. Integrar CLARK.
6. Integrar Transcriptor.
7. Desactivar login de Keycloak.
8. Conservar backup/exportación.
9. Retirar sus contenedores de producción cuando no haya dependencias.

## 19.2. Código reutilizable

Se puede reutilizar:

- Diseño visual de login.
- Textos.
- Navegación.
- Lógica de redirección.
- Conceptos de roles.
- Configuración de proxy.
- Componentes frontend no acoplados.

No reutilizar sin revisión:

- Adaptadores OIDC.
- Tokens Keycloak.
- Dependencias del SDK.
- Lectura de roles desde claims antiguos.
- Base de datos interna de Keycloak.

## 19.3. Limpieza por repositorio

Eliminar o desactivar:

- Variables `KEYCLOAK_*`.
- SDKs OIDC no utilizados.
- Guards de autenticación antiguos.
- Refresh token antiguo.
- Rutas callback antiguas.

Hacerlo solo después de que el flujo Django esté probado.

---

## 20. Orden de integración recomendado

## Fase 0 — Inventario técnico

Para cada repositorio, documentar:

- Framework frontend.
- Framework backend.
- Endpoints que lanzan IA.
- Variables de entorno.
- Contenedores.
- Puertos.
- Dominios.
- Integración Keycloak existente.
- Pruebas existentes.

Crear una tabla de inventario antes de modificar código.

## Fase 1 — Home

- Añadir navegación y estado de sesión.
- Probar cookies compartidas.
- Probar login/logout global.

### Criterio de salida

Login en `cuenta.carlosrevert.es` se refleja en `carlosrevert.es`.

## Fase 2 — Juridia frontend

- Añadir cliente Django.
- Añadir estado global.
- Añadir modal.
- Añadir cuota.

### Criterio de salida

El frontend distingue correctamente visitante y usuario.

## Fase 3 — Juridia backend

- Validar reservas.
- Proteger IA.
- Notificar resultado.

### Criterio de salida

No es posible ejecutar una consulta sin autorización válida.

## Fase 4 — Flujo E2E Juridia

- Registro.
- Login.
- Cinco consultas FREE.
- Sexta bloqueada.
- Cambio manual a PREMIUM.
- Veinte consultas.
- Logout global.

### Criterio de salida

Flujo completo listo para PFM.

## Fase 5 — CLARK

- Repetir patrón.
- Verificar cuota compartida.

## Fase 6 — Transcriptor

- Repetir patrón.
- Revisar política de reembolso.
- Revisar privacidad.

## Fase 7 — Retirada de Keycloak

- Desactivar.
- Limpiar dependencias.
- Actualizar documentación.

## Fase 8 — Observabilidad y seguridad

- Logs estructurados.
- Métricas.
- Alertas.
- Rate limiting.
- Revisión de CORS/CSRF.

## Fase 9 — Documentación final

- Diagramas.
- Matriz de integración.
- Manual de despliegue.
- Manual de rollback.
- Evidencias para PFM.

---

## 21. Estrategia de ramas y commits

Crear una rama por repositorio:

```text
feat/django-accounts-integration
```

Commits sugeridos:

```text
feat: add shared account api client
feat: expose global authentication state
feat: add common account navigation
feat: protect ai actions behind django quota
feat: validate interaction reservations in backend
feat: report completed and failed interactions
fix: handle quota and authentication errors
security: remove public unauthenticated ai endpoint
test: cover django account integration
docs: document accounts variables and deployment
chore: remove deprecated keycloak integration
```

No mezclar refactorizaciones visuales no relacionadas con la integración.

---

## 22. Pruebas end-to-end obligatorias

Automatizar cuando sea posible con Playwright, Cypress o herramienta equivalente.

### Sesión global

- Login en Cuenta.
- Abrir Home y comprobar usuario.
- Abrir Juridia y comprobar usuario.
- Abrir CLARK y comprobar usuario.
- Abrir Transcriptor y comprobar usuario.
- Logout en una app.
- Verificar logout en todas.

### Usuario FREE

- Ejecutar dos consultas en Juridia.
- Ejecutar dos acciones en CLARK.
- Ejecutar una tarea en Transcriptor.
- Confirmar total cinco.
- Confirmar sexta bloqueada en cualquiera.

### Usuario PREMIUM

- Cambiar plan en Django Admin.
- Refrescar aplicación.
- Confirmar límite veinte.

### Seguridad

- Llamar al backend de IA sin `request_id`.
- Llamar con `request_id` falso.
- Reutilizar un `request_id`.
- Manipular `APP_SLUG`.
- Usar credencial de CLARK contra Juridia.
- Confirmar rechazo.

### Fallos

- Django no disponible.
- Backend de IA no disponible.
- Timeout.
- Doble clic.
- Recarga durante procesamiento.
- Error al completar.

---

## 23. Observabilidad

Cada petición debe poder correlacionarse mediante:

```text
request_id
```

Logs mínimos:

- Aplicación.
- Acción.
- Usuario interno o hash no sensible.
- Estado.
- Tiempo.
- Código de error.

No registrar:

- Contraseña.
- Cookie.
- Token de servicio.
- Audio.
- Prompt completo, salvo modo de depuración expresamente controlado.

Crear panel básico desde Django Admin o dashboard:

- Consumo por aplicación.
- Errores.
- Rechazos por cuota.
- Usuarios activos.

---

## 24. Rollback

Cada integración debe poder revertirse.

### Estrategia

- Mantener variables de feature flag:

```text
DJANGO_ACCOUNTS_ENABLED=true
```

- Mantener temporalmente el flujo antiguo desactivable durante pruebas.
- No retirar Keycloak hasta validar producción.
- Crear backup de configuraciones.
- Documentar cómo volver al despliegue anterior.

En producción final, eliminar el bypass que permita ejecutar IA sin Django.

---

## 25. Evidencias para el PFM

Capturar y documentar:

1. Registro de usuario.
2. Login.
3. Sesión compartida.
4. Dashboard Django.
5. Usuario FREE con saldo.
6. Consulta en Juridia.
7. Actualización de saldo.
8. Sexta interacción bloqueada.
9. Cambio a PREMIUM en Django Admin.
10. Nuevo límite de veinte.
11. Historial de uso.
12. Diagrama de arquitectura.
13. Endpoint React consumiendo Django.
14. Pruebas automáticas.
15. Despliegue Docker y HTTPS.

---

## 26. Criterios de aceptación globales

- [ ] Las cuatro webs son navegables sin cuenta.
- [ ] Las tres aplicaciones de IA exigen autenticación para interactuar.
- [ ] La Home muestra sesión y aplicaciones.
- [ ] La sesión se comparte entre subdominios.
- [ ] Login y logout funcionan globalmente.
- [ ] FREE tiene cinco interacciones diarias totales.
- [ ] PREMIUM tiene veinte interacciones diarias totales.
- [ ] El cambio a PREMIUM se realiza desde Django Admin.
- [ ] La cuota se comparte entre Juridia, CLARK y Transcriptor.
- [ ] Django autoriza cada interacción.
- [ ] Los backends validan la reserva antes de procesar.
- [ ] No existe bypass público hacia la IA.
- [ ] Las reservas son idempotentes.
- [ ] Los errores se notifican a Django.
- [ ] El frontend muestra mensajes útiles.
- [ ] Las credenciales internas no aparecen en el navegador.
- [ ] CORS y CSRF están restringidos.
- [ ] Keycloak queda retirado o inoperante.
- [ ] Existen pruebas unitarias, integración y E2E.
- [ ] Cada repositorio documenta sus variables.
- [ ] Existe procedimiento de rollback.
- [ ] Juridia demuestra el flujo completo del PFM.

---

## 27. Instrucción final para el agente

Ejecuta este roadmap de forma incremental y repositorio por repositorio.

Antes de modificar cada proyecto:

1. Analiza su arquitectura actual.
2. Identifica el flujo exacto de IA.
3. Localiza y documenta cualquier integración Keycloak.
4. Añade la integración Django sin alterar funcionalidades públicas.
5. Protege la acción en frontend y backend.
6. Añade pruebas.
7. Ejecuta el proyecto localmente.
8. Verifica sesión, cuota y errores.
9. Documenta variables de entorno.
10. Crea commits pequeños y descriptivos.

Prioriza Juridia. No empieces CLARK o Transcriptor hasta que el flujo completo funcione en Juridia y pueda demostrarse de extremo a extremo.
