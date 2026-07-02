# reset_and_seed.ps1 - Xoa sach database, tao lai schema moi nhat, seed du lieu.
# Chay tu thu muc backend/ voi venv da activate:
#   .\scripts\reset_and_seed.ps1
$ErrorActionPreference = "Stop"

# Doc cau hinh DB tu .env
if (-not (Test-Path .env)) { Write-Error "Khong thay .env - hay chay tu thu muc backend/" }
$envFile = Get-Content .env -Raw
if ($envFile -match 'DATABASE_URL=postgresql\+asyncpg://([^:]+):([^@]+)@localhost:(\d+)/(\w+)') {
    $dbUser = $Matches[1]; $dbPass = $Matches[2]; $dbPort = $Matches[3]; $dbName = $Matches[4]
} else {
    Write-Error "Khong doc duoc DATABASE_URL trong .env (can dang postgresql+asyncpg://user:pass@localhost:port/dbname)"
}
Write-Host "DB: $dbName tren cong $dbPort" -ForegroundColor Cyan

Write-Host ""
Write-Host "[1/5] Reset PostgreSQL container + volume..." -ForegroundColor Yellow
docker rm -f vocab-pg 2>$null | Out-Null
docker volume rm vocab_pgdata 2>$null | Out-Null
docker run -d --name vocab-pg -p "${dbPort}:5432" `
    -e POSTGRES_DB=$dbName -e POSTGRES_USER=$dbUser -e POSTGRES_PASSWORD=$dbPass `
    -v vocab_pgdata:/var/lib/postgresql/data postgres:16-alpine | Out-Null

Write-Host "[2/5] Cho PostgreSQL san sang..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    docker exec vocab-pg pg_isready -U $dbUser -d $dbName 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
}
if (-not $ready) { Write-Error "PostgreSQL khong khoi dong duoc - xem: docker logs vocab-pg" }

Write-Host "[3/5] Tao lai schema (migration moi nhat tu models)..." -ForegroundColor Yellow
Remove-Item alembic\versions\*.py -ErrorAction SilentlyContinue
alembic revision --autogenerate -m "initial schema" | Out-Null
alembic upgrade head

Write-Host "[4/5] Kiem tra API server..." -ForegroundColor Yellow
$serverProc = $null
$apiUrl = "http://localhost:8000/api"
$apiUp = $false

# Neu server 8000 dang chay san thi dung luon
try {
    $r = Invoke-RestMethod "$apiUrl/health" -TimeoutSec 2
    if ($r.status -eq "ok") { $apiUp = $true; Write-Host "  API dang chay san tren cong 8000 - dung luon." }
} catch {}

# Chua chay -> bat server tam tren cong 8001, log ra file de xem loi
if (-not $apiUp) {
    $apiUrl = "http://localhost:8001/api"
    $outLog = "scripts\uvicorn_seed.log"
    $errLog = "scripts\uvicorn_seed.err"
    Write-Host "  API chua chay - khoi dong tam tren cong 8001 (log: $errLog)..."
    $serverProc = Start-Process -PassThru -WindowStyle Hidden python `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "8001" `
        -RedirectStandardOutput $outLog -RedirectStandardError $errLog
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        if ($serverProc.HasExited) { break }
        try {
            $r = Invoke-RestMethod "$apiUrl/health" -TimeoutSec 2
            if ($r.status -eq "ok") { $apiUp = $true; break }
        } catch {}
    }
    if (-not $apiUp) {
        Write-Host ""
        Write-Host "API khong khoi dong duoc. Loi tu uvicorn:" -ForegroundColor Red
        if (Test-Path $errLog) { Get-Content $errLog -Tail 20 | Write-Host }
        if (Test-Path $outLog) { Get-Content $outLog -Tail 5 | Write-Host }
        if ($serverProc -and -not $serverProc.HasExited) { Stop-Process -Id $serverProc.Id -Force }
        Write-Error "Xem loi o tren, hoac chay thu cong: python -m uvicorn app.main:app --port 8001"
    }
}

Write-Host "[5/5] Seed du lieu..." -ForegroundColor Yellow
try {
    $env:API_URL = $apiUrl
    python scripts\seed.py
} finally {
    Remove-Item Env:\API_URL -ErrorAction SilentlyContinue
    if ($serverProc -and -not $serverProc.HasExited) {
        Stop-Process -Id $serverProc.Id -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "=== HOAN TAT ===" -ForegroundColor Green
Write-Host "Chay server de dung app:"
Write-Host "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor Cyan
