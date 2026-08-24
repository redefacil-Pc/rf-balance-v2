<#
.SYNOPSIS
  Atalhos de desenvolvimento no Windows — equivalente ao Makefile, que exige `make`.

.EXAMPLE
  .\scripts\rfb.ps1 up
  .\scripts\rfb.ps1 migrate
  .\scripts\rfb.ps1 revision -Message "cria tabelas de identidade"
  .\scripts\rfb.ps1 logs -Service api
#>
param(
    [Parameter(Position = 0)]
    [ValidateSet('up', 'down', 'restart', 'build', 'logs', 'ps', 'shell', 'migrate', 'revision',
                 'downgrade', 'seed', 'seed-demo', 'sync-rbac', 'sync-rbac-purge',
                 'validate-golden',
                 'test', 'test-unit', 'test-integration', 'lint', 'format',
                 'typecheck', 'web-test', 'web-build', 'openapi', 'clean', 'help')]
    [string]$Command = 'help',

    [string]$Message = '',
    [string]$Service = ''
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

if (-not (Test-Path (Join-Path $repo '.env'))) {
    Write-Host "Arquivo .env ausente. Criando a partir de .env.example..." -ForegroundColor Yellow
    Copy-Item (Join-Path $repo '.env.example') (Join-Path $repo '.env')
    Write-Host "Revise o .env antes de subir o ambiente." -ForegroundColor Yellow
}

$compose = @('compose', '-f', 'infrastructure/compose/docker-compose.yml', '--env-file', '.env')

function Invoke-Compose { param([string[]]$CommandArgs) & docker @($compose + $CommandArgs) }
function Invoke-Api { param([string[]]$CommandArgs) Invoke-Compose (@('exec', '-T', 'api') + $CommandArgs) }
function Invoke-Web { param([string[]]$CommandArgs) Invoke-Compose (@('exec', '-T', 'web') + $CommandArgs) }

switch ($Command) {
    'up' {
        Invoke-Compose @('up', '-d')
        Write-Host ""
        Write-Host "api   -> http://localhost:8000/docs"
        Write-Host "web   -> http://localhost:5173"
        Write-Host "storage -> endpoint S3/Spaces configurado no .env"
    }
    'down'     { Invoke-Compose @('down') }
    'restart'  { Invoke-Compose @('restart', 'api', 'worker', 'scheduler') }
    'build'    { Invoke-Compose @('build') }
    'logs'     { if ($Service) { Invoke-Compose @('logs', '-f', $Service) } else { Invoke-Compose @('logs', '-f') } }
    'ps'       { Invoke-Compose @('ps') }
    'shell'    { Invoke-Compose @('exec', 'api', 'bash') }

    'migrate'   {
        Invoke-Api @('alembic', 'upgrade', 'head')
        Invoke-Api @('python', '-m', 'app.platform.db.sync_rbac')
    }
    'sync-rbac' { Invoke-Api @('python', '-m', 'app.platform.db.sync_rbac') }
    'sync-rbac-purge' { Invoke-Api @('python', '-m', 'app.platform.db.sync_rbac', '--purgar') }
    'downgrade' { Invoke-Api @('alembic', 'downgrade', '-1') }
    'revision'  {
        if (-not $Message) { throw "Use: .\scripts\rfb.ps1 revision -Message 'descricao'" }
        Invoke-Api @('alembic', 'revision', '--autogenerate', '-m', $Message)
    }
    'seed'      { Invoke-Api @('python', '-m', 'app.platform.db.seed') }
    'seed-demo' { Invoke-Api @('python', '-m', 'app.platform.db.seed_demo') }
    'validate-golden' { Invoke-Api @('python', '-m', 'app.platform.db.validate_golden_cases') }

    'test'             { Invoke-Api @('pytest', 'tests/unit'); Invoke-Web @('npm', 'run', 'test') }
    'test-unit'        { Invoke-Api @('pytest', 'tests/unit') }
    'test-integration' { Invoke-Api @('pytest', 'tests/integration', '-m', 'integration') }
    'lint'             { Invoke-Api @('ruff', 'check', 'app', 'worker', 'tests') }
    'format'           { Invoke-Api @('ruff', 'format', 'app', 'worker', 'tests') }
    'typecheck'        { Invoke-Api @('mypy', 'app') }
    'web-test'         { Invoke-Web @('npm', 'run', 'test') }
    'web-build'        { Invoke-Web @('npm', 'run', 'build') }

    'openapi' {
        Invoke-Api @('python', '-c',
            'import json;from app.main import criar_app;print(json.dumps(criar_app().openapi(),indent=2))'
        ) | Out-File -FilePath 'openapi.json' -Encoding utf8
        Write-Host "openapi.json atualizado."
    }

    'clean' {
        Write-Host "Isso apaga os volumes locais (banco, redis e MinIO opcional)." -ForegroundColor Red
        & docker @($compose + @('--profile', 'local-storage', 'down', '-v'))
    }

    default {
        Write-Host "Comandos: up, down, restart, build, logs, ps, shell, migrate, revision, downgrade,"
        Write-Host "          seed, test, test-unit, test-integration, lint, format, typecheck,"
        Write-Host "          web-test, web-build, openapi, clean"
    }
}
