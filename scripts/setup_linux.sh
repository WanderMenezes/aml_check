#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@aml.local}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-ChangeMe123!}"

if [ ! -f ".env" ]; then
  cp .env.example .env
fi

$PYTHON_BIN -m pip install -r requirements.txt

if command -v npm >/dev/null 2>&1; then
  (cd frontend && npm install)
fi

cd backend
$PYTHON_BIN manage.py migrate
$PYTHON_BIN manage.py bootstrap_aml --admin-email "$ADMIN_EMAIL" --admin-password "$ADMIN_PASSWORD"
$PYTHON_BIN manage.py seed_demo_screenings

printf "Setup completed. Backend: http://127.0.0.1:8000 | Frontend: http://127.0.0.1:3000\n"
