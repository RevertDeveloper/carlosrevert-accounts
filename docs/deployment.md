# Despliegue

1. Copia `.env.example` a `.env` y configura secretos fuertes, host y orígenes reales.
2. Arranca `docker compose up -d --build`.
3. En Nginx Proxy Manager, crea `cuenta.carlosrevert.es` hacia la IP privada y puerto `10401` con certificado TLS.
4. Activa `DJANGO_SETTINGS_MODULE=config.settings.production` y ejecuta `python manage.py check --deploy`.
5. Crea el superusuario y ejecuta los comandos de seed si el contenedor no lo ha hecho.

PostgreSQL queda ligado a `127.0.0.1:10410`; no debe exponerse públicamente. Antes de habilitar HSTS confirma que todo el dominio usa HTTPS.
