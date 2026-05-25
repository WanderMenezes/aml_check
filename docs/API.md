# API REST

## Autenticação

- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `POST /api/auth/logout/`
- `GET /api/auth/me/`
- `POST /api/auth/password-reset/`
- `POST /api/auth/password-reset/confirm/`

## Screening

- `GET /api/screening/dashboard/`
- `GET /api/screening/clients/`
- `POST /api/screening/clients/`
- `GET /api/screening/requests/`
- `POST /api/screening/requests/run/`
- `POST /api/screening/requests/{id}/export_pdf/`
- `GET /api/screening/requests/{id}/export_csv/`
- `GET /api/screening/reports/`
- `GET /api/screening/alerts/`

## Inteligência / Sync

- `GET /api/intelligence/summary/`
- `GET /api/intelligence/sources/`
- `POST /api/intelligence/sources/{id}/sync_now/`
- `GET /api/intelligence/watchlist/`
- `GET /api/intelligence/country-risk/`
- `GET /api/intelligence/sync/`
- `GET|POST|PUT /api/intelligence/rules/`

## Auditoria

- `GET /api/audit/`
- `GET /api/audit/{id}/`

## Documentação OpenAPI

- Swagger: `/api/docs/`
- ReDoc: `/api/redoc/`
- Schema JSON: `/api/schema/`
