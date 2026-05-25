# Deploy

## Docker

```bash
docker-compose up --build
```

Serviços provisionados:

- `backend`
- `frontend`
- `mysql`
- `redis`
- `celery`

## Produção

- Ative `DJANGO_DEBUG=False`
- Defina `DJANGO_SECRET_KEY` seguro
- Use `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` corretos
- Aponte o frontend para `NEXT_PUBLIC_API_BASE_URL`
- Execute `celery -A config worker -l info`
- Configure backups do MySQL e retenção de relatórios PDF
