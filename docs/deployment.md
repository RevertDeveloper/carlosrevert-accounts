# Despliegue

1. Copia `.env.example` a `.env` y configura secretos fuertes, host y orígenes reales.
2. Arranca producción con `docker compose -f compose.yaml up -d --build`. Es obligatorio indicar el fichero: `compose.override.yaml` está reservado al desarrollo local.
3. En Nginx Proxy Manager, crea `cuenta.carlosrevert.es` hacia la IP privada y puerto `10401` con certificado TLS.
4. Activa `DJANGO_SETTINGS_MODULE=config.settings.production` y ejecuta `python manage.py check --deploy`.
5. Crea el superusuario y ejecuta los comandos de seed si el contenedor no lo ha hecho.

PostgreSQL queda ligado a `127.0.0.1:10410`; no debe exponerse públicamente. Antes de habilitar HSTS confirma que todo el dominio usa HTTPS.

Nginx Proxy Manager debe reenviar `X-Forwarded-Proto: https`; Django lo usa mediante `SECURE_PROXY_SSL_HEADER` para aplicar HTTPS sin romper el healthcheck interno.


## Comandos de validación

`manage.py` carga `.env` antes de seleccionar settings, por lo que `python manage.py check --deploy` desde el host y el mismo comando dentro del contenedor deben usar producción y terminar sin avisos. El arranque crea de forma idempotente `accounts_cache`, usada para compartir rate limits entre workers.

Configura `TRUSTED_PROXY_IPS` con las IP reales del proxy inverso. Producción usa SMTP; no dejes `EMAIL_HOST` vacío si se ofrece recuperación de contraseña. Sigue el [tour de producción](production-tour.md) para superusuario, comprobación funcional, backup y rollback.
