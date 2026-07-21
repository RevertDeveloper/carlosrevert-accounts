# Tour de producción de Carlos Revert Accounts

Esta guía permite validar y operar el servicio central sin acceder directamente a PostgreSQL ni exponer secretos. Ejecuta los comandos desde `/home/revert/Repositorios/carlosrevert-accounts`.

## 1. Regla de despliegue

Producción siempre debe indicar el fichero Compose para no cargar `compose.override.yaml`, que está reservado al desarrollo:

```bash
docker compose -f compose.yaml up -d --build
docker compose -f compose.yaml ps
```

Los servicios `web` y `postgres` deben aparecer `Up` y `healthy`. Docker debe arrancar con el sistema:

```bash
systemctl is-active docker
systemctl is-enabled docker
```

## 2. Verificación técnica inicial

```bash
. .venv/bin/activate
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py showmigrations --plan
python -m pytest -q
```

`check --deploy` debe terminar sin avisos. `manage.py` carga `.env` antes de seleccionar settings, por lo que el host y Docker usan `config.settings.production`. La comprobación equivalente sobre la imagen desplegada es:

```bash
docker compose -f compose.yaml exec web python manage.py check --deploy
docker compose -f compose.yaml exec web python manage.py showmigrations --plan
```

Comprueba salud local y pública:

```bash
curl -fsS http://127.0.0.1:10401/health/ -H 'X-Forwarded-Proto: https'
curl -fsS https://cuenta.carlosrevert.es/health/
```

La respuesta esperada es `{"status":"ok","database":"ok"}`. Este endpoint también comprueba PostgreSQL.

## 3. Crear el primer superusuario

Usa el contenedor para garantizar que escribes en la base de producción:

```bash
docker compose -f compose.yaml exec web python manage.py createsuperuser
```

Django solicitará usuario, email y una contraseña robusta. No uses una contraseña compartida con otros servicios. Alternativa con usuario y email predefinidos, manteniendo la contraseña interactiva:

```bash
docker compose -f compose.yaml exec web python manage.py createsuperuser \
  --username carlos-admin --email TU_EMAIL_REAL
```

No uses `--noinput` con una contraseña escrita en el historial de la terminal.

## 4. Entrar en los paneles

- Cuenta personal: `https://cuenta.carlosrevert.es/`
- Django Admin: `https://cuenta.carlosrevert.es/admin/`
- Documentación Swagger: `https://cuenta.carlosrevert.es/api/docs/`
- Métricas JSON para staff: `https://cuenta.carlosrevert.es/api/v1/admin/metrics/`

En Admin aparecen estas áreas:

- **Usuarios > Users**: usuarios, plan actual, bloqueo, actividad y permisos staff.
- **Planes > Plans**: límites FREE y PREMIUM.
- **Planes > User plans**: asignaciones en modo solo lectura.
- **Planes > Plan change logs**: auditoría inmutable de cambios.
- **Applications > Client applications**: aplicaciones y credenciales internas.
- **Usage > Daily usages**: contador agregado diario, solo lectura.
- **Usage > Usage events**: historial y resultado de cada interacción, solo lectura.
- **Usage > Interaction reservations**: UUID e idempotencia, solo lectura.
- **Axes**: intentos y bloqueos de autenticación.

Los usuarios y registros de consumo no pueden borrarse desde Admin. Una baja se realiza desactivando el usuario para conservar auditoría.

## 5. Crear un usuario normal

### Registro realizado por el usuario

1. Abre `https://cuenta.carlosrevert.es/register/` en una ventana privada.
2. Completa usuario, email, nombre, contraseña y aceptación legal.
3. Al terminar entrarás automáticamente en **Mi cuenta**.
4. Comprueba que aparece `FREE`, límite 5 y saldo 5.

Todo usuario nuevo recibe FREE automáticamente y genera un registro de asignación inicial.

### Alta desde Django Admin

1. Entra en **Usuarios > Users**.
2. Pulsa **Add user**.
3. Introduce usuario y contraseña; completa después email y datos personales.
4. Guarda y verifica que la columna **Plan** muestra FREE.

No crees usuarios directamente en `User plans`: esa pantalla es deliberadamente de solo lectura.

## 6. Subir un usuario a PREMIUM

1. En **Usuarios > Users**, busca por email o usuario.
2. Marca la casilla del usuario.
3. En **Action**, elige **Marcar como PREMIUM**.
4. Pulsa **Go**.
5. Comprueba que la columna Plan cambia a PREMIUM.
6. Abre **Planes > Plan change logs** y verifica actor, plan anterior, nuevo plan y fecha.
7. Pide al usuario que recargue cualquiera de las aplicaciones; el límite debe mostrar 20.

Para volver a FREE usa **Marcar como FREE**. No edites `User plans`, porque los cambios de plan deben pasar por el servicio auditado.

## 7. Bloquear, desactivar y reactivar

Desde **Usuarios > Users**:

- **Bloquear usuario**: impide login y nuevas interacciones de IA.
- **Desbloquear usuario**: retira el bloqueo.
- **Desactivar usuario sin borrar su auditoría**: baja lógica completa.
- **Reactivar usuario**: recupera una cuenta desactivada.

`is_staff` permite entrar en Admin. `is_superuser` concede todos los permisos; resérvalo para administradores reales.

## 8. Tour de sesión compartida

1. Inicia sesión en Cuenta con un usuario de prueba.
2. Abre `https://carlosrevert.es`: debe mostrar Cuenta/Cerrar sesión y el plan.
3. Abre Juridia, CLARK y Transcriptor: las tres deben reconocer al mismo usuario.
4. Cierra sesión desde cualquiera de ellas.
5. Recarga las demás: todas deben volver a mostrar Acceder/Registrarse.

La sesión usa una cookie HttpOnly, Secure y SameSite=Lax para `.carlosrevert.es`; no existe token de usuario en `localStorage`.

## 9. Tour de cuota

Usa una cuenta de prueba, no el superusuario:

1. Confirma en **Mi cuenta** que empieza en `0/5`.
2. Ejecuta una consulta real en Juridia.
3. Revisa **Usage events**: aplicación `juridia`, acción `legal_query` y estado final `completed` o `failed`.
4. Ejecuta acciones en CLARK o Transcriptor y comprueba que aumentan el mismo contador.
5. Al llegar a 5, una sexta acción debe bloquearse antes de llamar a IA.
6. Cambia la cuenta a PREMIUM y comprueba que el resumen pasa a límite 20 sin perder el consumo del día.

Estados principales:

- `authorized`: cuota reservada.
- `processing`: backend validó el UUID y comenzó el trabajo.
- `completed`: final correcto.
- `failed`: el proveedor o procesamiento falló.
- `rejected_quota`: límite agotado.
- `rejected_auth`: cuenta o aplicación no autorizada.

Un fallo `before_processing` devuelve la unidad porque no llegó a utilizar IA. Los fallos posteriores al inicio permanecen consumidos.

## 10. Aplicaciones y claves internas

En **Applications > Client applications** deben existir:

- `home`: activa, no consume cuota y no necesita clave interna.
- `juridia`, `clark`, `transcriptor`: activas, consumen y tienen clave configurada.

La acción **Rotar credencial de servicio** muestra la nueva clave una sola vez. No la ejecutes durante un tour casual. Para una rotación real:

1. Selecciona una sola aplicación y rota.
2. Guarda inmediatamente la clave en el `.env` del backend correspondiente.
3. Recrea solo ese backend.
4. Ejecuta una interacción real.
5. Nunca copies la clave a variables `VITE_*` o `NEXT_PUBLIC_*`.

## 11. Métricas y diagnóstico

Con sesión staff abre `/api/v1/admin/metrics/`. Verás usuarios FREE/PREMIUM, activos del día, interacciones por aplicación, rechazos y errores.

Comandos de operación:

```bash
docker compose -f compose.yaml logs --tail=200 web
docker compose -f compose.yaml logs --tail=100 postgres
docker compose -f compose.yaml exec postgres pg_isready -U accounts -d accounts
docker inspect carlosrevert-accounts-web-1 --format '{{.State.Health.Status}} {{.HostConfig.RestartPolicy.Name}}'
```

Los logs no deben contener contraseñas, cookies, claves de servicio, prompts, respuestas o audio.

## 12. Correo y recuperación de contraseña

Producción usa SMTP y nunca imprime enlaces de recuperación en logs. Configura en `.env`:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=SERVIDOR_SMTP
EMAIL_PORT=587
EMAIL_HOST_USER=USUARIO_SMTP
EMAIL_HOST_PASSWORD=CONTRASENA_SMTP
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=no-reply@carlosrevert.es
```

Después recrea solo web y prueba con una dirección controlada:

```bash
docker compose -f compose.yaml up -d --force-recreate web
docker compose -f compose.yaml exec web python manage.py shell
```

En el shell Django:

```python
from django.core.mail import send_mail
send_mail("Prueba Accounts", "SMTP operativo", None, ["TU_EMAIL_REAL"], fail_silently=False)
```

Sal con `exit()`. Después prueba `https://cuenta.carlosrevert.es/password-reset/`.

## 13. Backup

Crea backups fuera del repositorio y con permisos restringidos:

```bash
mkdir -p "$HOME/backups/carlosrevert-accounts"
docker compose -f compose.yaml exec -T postgres \
  pg_dump -U accounts -d accounts -Fc \
  > "$HOME/backups/carlosrevert-accounts/accounts-$(date +%F-%H%M).dump"
```

Comprueba que el fichero existe y no está vacío. Programa esta operación y copia los backups a otra máquina o almacenamiento cifrado. Prueba restauraciones periódicamente en una base separada; un backup no probado no garantiza recuperación.

## 14. Actualización y rollback

Antes de desplegar:

```bash
git status --short
docker compose -f compose.yaml exec web python manage.py check --deploy
```

Despliegue:

```bash
docker compose -f compose.yaml up -d --build
docker compose -f compose.yaml ps
curl -fsS https://cuenta.carlosrevert.es/health/
```

Si la nueva imagen falla, vuelve al commit conocido sin borrar `postgres_data` y recrea solo `web`. Consulta `docs/rollback.md`. No uses `docker compose down -v`, porque eliminaría PostgreSQL.

## 15. Checklist de aceptación personal

- [ ] `check --deploy` sin avisos.
- [ ] Web y PostgreSQL healthy.
- [ ] Superusuario entra en Admin.
- [ ] Registro crea usuario FREE.
- [ ] Cambio a PREMIUM queda auditado.
- [ ] Bloqueo impide IA.
- [ ] Cuenta muestra uso e historial.
- [ ] Sesión y logout se comparten entre cinco dominios.
- [ ] Quinta interacción FREE autorizada y sexta rechazada.
- [ ] Métricas staff visibles.
- [ ] SMTP y recuperación probados.
- [ ] Backup creado y restauración ensayada.
