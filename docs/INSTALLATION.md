# Instalação

## Requisitos

- Python 3.12+
- Node.js 20+
- MySQL 8 ou XAMPP MySQL
- Redis 7+

## Ambiente local com XAMPP

1. Copie `.env.example` para `.env`.
2. Ajuste:
   - `DB_HOST=127.0.0.1`
   - `DB_PORT=3306`
   - `DB_USER=root`
   - `DB_PASSWORD=` ou a senha configurada no XAMPP
3. Crie a base `aml_check` no MySQL se ela ainda não existir.
4. Instale o driver MySQL Python (`PyMySQL` já está em `requirements.txt`).

## Backend

```bash
pip install -r requirements.txt
cd backend
python manage.py migrate
python manage.py bootstrap_aml --admin-email admin@aml.local --admin-password ChangeMe123!
python manage.py seed_demo_screenings
python manage.py runserver
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

## Setup automático

- Windows: `powershell -ExecutionPolicy Bypass -File scripts/setup_windows.ps1`
- Linux: `bash scripts/setup_linux.sh`
