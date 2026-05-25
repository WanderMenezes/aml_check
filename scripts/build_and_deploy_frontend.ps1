<#
Build and deploy frontend to Django static folder (Windows PowerShell)

Usage:
  .\build_and_deploy_frontend.ps1 [-FrontendDir '../frontend'] [-BackendDir '../backend']

What it does:
  - Runs `npm install`, `npm run build` and `npm run export` in the frontend folder
  - Copies the generated `out/` files to the backend static folder
  - Runs `python manage.py collectstatic --noinput` in the backend

Adjust `FrontendDir` / `BackendDir` if your layout is different.
#>

param(
    [string]$FrontendDir = "../frontend",
    [string]$BackendDir = "../backend"
)

function ExitWithError([string]$msg, [int]$code = 1) {
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit $code
}

Push-Location $PSScriptRoot

$frontendPath = Resolve-Path -Path $FrontendDir -ErrorAction SilentlyContinue
if (-not $frontendPath) { ExitWithError "Frontend folder '$FrontendDir' not found." }
$frontend = $frontendPath.ProviderPath

$backendPath = Resolve-Path -Path $BackendDir -ErrorAction SilentlyContinue
if (-not $backendPath) { ExitWithError "Backend folder '$BackendDir' not found." }
$backend = $backendPath.ProviderPath

Write-Host "Frontend: $frontend"
Write-Host "Backend: $backend"

# check npm
$npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npm) { ExitWithError "npm not found in PATH. Install Node.js and npm first." }

# check python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) { ExitWithError "Python not found in PATH. Install Python 3.x and ensure 'python' or 'py' is available." }

try {
    Push-Location $frontend
    Write-Host "Running npm install..." -ForegroundColor Cyan
    npm install

    Write-Host "Building Next.js (production)..." -ForegroundColor Cyan
    npm run build

    Write-Host "Exporting static site (next export)..." -ForegroundColor Cyan
    npm run export

    $outDir = Join-Path $frontend "out"
    if (-not (Test-Path $outDir)) { ExitWithError "Export failed: '$outDir' not found." }

    $targetStatic = Join-Path $backend "static"
    if (-not (Test-Path $targetStatic)) {
        Write-Host "Creating backend static folder: $targetStatic" -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $targetStatic -Force | Out-Null
    }

    Write-Host "Copying exported files to backend static folder..." -ForegroundColor Cyan
    # remove existing contents (except keep .gitignore)
    Get-ChildItem -Path $targetStatic -Force | Where-Object { $_.Name -ne ".git" } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Copy-Item -Path (Join-Path $outDir "*") -Destination $targetStatic -Recurse -Force

} catch {
    ExitWithError "Frontend build/export failed: $_"
} finally {
    Pop-Location
}

try {
    Push-Location $backend
    Write-Host "Running collectstatic..." -ForegroundColor Cyan
    & $python.Path -ArgumentList "manage.py", "collectstatic", "--noinput"
    Pop-Location
} catch {
    ExitWithError "collectstatic failed: $_"
}

Write-Host "Build and deploy finished successfully." -ForegroundColor Green
exit 0
