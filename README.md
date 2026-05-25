# AML Check Enterprise

Plataforma full-stack para Compliance / AML / KYC Screening com backend Django + DRF e frontend Next.js + Tailwind.

## Módulos principais

- Autenticação JWT com sessões revogáveis por utilizador.
- Dashboard AML com métricas, alertas, screenings recentes e estado das integrações.
- Screening local com fuzzy matching, score de similaridade e motor de risco editável.
- Watchlists locais para OFAC, ONU, UE, FATF e INTERPOL, com jobs de sincronização.
- Auditoria, histórico, alertas operacionais e geração de relatório PDF profissional com QR.
- Estrutura pronta para MySQL/XAMPP, Redis, Celery e Docker.

## Estrutura

- `backend/`: Django, DRF, Celery, serviços AML e admin.
- `frontend/`: Next.js, Tailwind, i18n, dashboard e operações.
- `docker/`: Dockerfiles e init SQL.
- `docs/`: instalação, API, deploy e troubleshooting.
- `scripts/`: setup automático para Windows e Linux.

## Quick start

1. Copie `.env.example` para `.env`.
2. Instale dependências com `pip install -r requirements.txt`.
3. No frontend, execute `npm install` em `frontend/`.
4. Em `backend/`, rode `python manage.py migrate`.
5. Inicialize dados base com `python manage.py bootstrap_aml`.
6. Suba backend e frontend, ou use `docker-compose up --build`.

Detalhes completos em [docs/INSTALLATION.md](docs/INSTALLATION.md).
