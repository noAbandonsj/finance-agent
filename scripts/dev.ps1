$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot ".env"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install uv and retry."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm is required. Install Node.js and retry."
}
if (-not (Test-Path $envFile)) {
    Write-Warning ".env is missing. Copy .env.example to .env before enabling DeepSeek."
}

Push-Location $projectRoot
try {
    uv run --project backend alembic -c backend/alembic.ini upgrade head

    $backend = Start-Process `
        -FilePath "uv" `
        -ArgumentList @(
            "run", "--project", "backend", "uvicorn", "ai_finance.api.app:app",
            "--host", "127.0.0.1", "--port", "8000"
        ) `
        -PassThru `
        -WindowStyle Hidden

    try {
        Set-Location (Join-Path $projectRoot "frontend")
        npm run dev -- --host 127.0.0.1
    }
    finally {
        if ($backend -and -not $backend.HasExited) {
            Stop-Process -Id $backend.Id
        }
    }
}
finally {
    Pop-Location
}
