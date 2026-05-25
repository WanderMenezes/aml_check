# Configurar Celery + Redis (local)

Passos rápidos para rodar o worker Celery e o broker Redis localmente (desenvolvimento):

1) Instale dependências (recomendo usar virtualenv/venv):

```bash
pip install -r requirements.txt
pip install celery[redis]  # se Celery não estiver instalado via requirements
# opcional: instalar aiohttp para fetch assíncrono
pip install aiohttp
```

2) Rode um broker Redis local (Docker):

```bash
docker run -d --name aml_redis -p 6379:6379 redis:7
```

ou via Windows install do Redis.

3) Configure variáveis de ambiente (em `.env` ou no ambiente):

- `CELERY_BROKER_URL=redis://localhost:6379/0`
- `CELERY_RESULT_BACKEND=redis://localhost:6379/1`

4) Rode o worker Celery (na raiz do projeto):

```bash
# dentro da venv
celery -A config.celery.app worker --loglevel=info -Q default
```

5) Teste manualmente

- Execute a aplicação Django normalmente (`python backend/manage.py runserver`) e dispare um screening pela UI.
- A triagem criará um `ScreeningRequest` rapidamente e enfileirará `screening.process_external_matches`.
- No terminal do worker Celery você verá tarefas sendo executadas e matches externos adicionados.

6) Configurações úteis (em `config/settings.py` — `SCREENING_SETTINGS`):

- `EXTERNAL_CACHE_TTL`: TTL do cache em segundos (padrão 300).
- `EXTERNAL_CONCURRENCY`: número de requisições concorrentes para buscar landing pages (padrão 6).

Observações
- Se você não quiser executar Celery, o código possui fallback que executa a tarefa síncrona (útil para desenvolvimento). Para produção, rode Celery e um broker (Redis/RabbitMQ).
- Para ambientes com firewall ou proxies, verifique se `landing_url` é acessível pelo worker.

