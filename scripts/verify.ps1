param(
    [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Push-Location (Join-Path $repoRoot 'backend')
try {
    $env:PYTHONPATH = '.'
    $env:DATABASE_URL = 'sqlite:///:memory:'
    Invoke-Step 'Backend tests (api + core)' {
        python -m pytest tests/api tests/core -q
    }
}
finally {
    Pop-Location
}

Push-Location (Join-Path $repoRoot 'frontend')
try {
    Invoke-Step 'Frontend lint' { npm run lint }
    Invoke-Step 'Frontend typecheck' { npm run typecheck }
    Invoke-Step 'Frontend tests' { npm run test:run }
    if (-not $SkipBuild) {
        Invoke-Step 'Frontend build' { npm run build }
    }
}
finally {
    Pop-Location
}

Write-Host "All checks passed." -ForegroundColor Green
