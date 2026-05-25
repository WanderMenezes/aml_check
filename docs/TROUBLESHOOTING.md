# Troubleshooting

## `Invalid credentials`

- Verifique se o utilizador foi criado via `bootstrap_aml`.
- Confirme o hash da senha no admin do Django.

## Frontend sem conectar ao backend

- Confirme `NEXT_PUBLIC_API_BASE_URL`.
- Verifique `DJANGO_CSRF_TRUSTED_ORIGINS`.
- Certifique-se de que a API responde em `/health/`.

## Sync de listas falha

- Verifique conectividade externa do servidor.
- Revalide URLs oficiais das fontes.
- Consulte `SyncJobLog` e `AuditEvent`.

## Redis / Celery indisponível

- O sistema mantém cache local e tasks síncronas degradadas.
- Para produção, mantenha Redis ativo para rate limiting e job queue.
