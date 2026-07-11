$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    uv run --project backend ruff check backend/src backend/tests
    uv run --project backend pytest backend/tests

    Push-Location frontend
    try {
        npm test -- --run
        npm run build
        npm run test:e2e
    }
    finally {
        Pop-Location
    }
}
finally {
    Pop-Location
}
