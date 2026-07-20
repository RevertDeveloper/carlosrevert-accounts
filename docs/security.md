# Seguridad

Producción usa `DEBUG=False`, hosts explícitos, HTTPS, HSTS, cookies Secure/HttpOnly/Lax y CORS con lista de orígenes. Nunca se usa `CORS_ALLOW_ALL_ORIGINS`. Django conserva CSRF para mutaciones basadas en sesión y django-axes limita intentos de autenticación.

No se guarda contraseña, token, prompt o respuesta completa en los logs/eventos. Las credenciales internas se verifican por aplicación mediante hashes; no se acepta una IP como autenticación. `INTERNAL_SERVICE_SECRET` permite un canal de emergencia rotado por entorno.

La baja desactiva la cuenta para proteger la integridad de auditoría. Los eventos se retienen `USAGE_EVENT_RETENTION_DAYS` días; se debe programar su purga conforme a la política de privacidad aplicable.
