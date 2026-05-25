param(
  [string]$Python = "python",
  [string]$AdminEmail = "admin@aml.local",
  [string]$AdminPassword = "ChangeMe123!"
)

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

& $Python -m pip install -r requirements.txt
if (Get-Command npm -ErrorAction SilentlyContinue) {
  Push-Location frontend
  npm install
  Pop-Location
}

Push-Location backend
& $Python manage.py migrate
& $Python manage.py bootstrap_aml --admin-email $AdminEmail --admin-password $AdminPassword
& $Python manage.py seed_demo_screenings
Pop-Location

Write-Host "Setup concluído. Backend: http://127.0.0.1:8000 | Frontend: http://127.0.0.1:3000"
