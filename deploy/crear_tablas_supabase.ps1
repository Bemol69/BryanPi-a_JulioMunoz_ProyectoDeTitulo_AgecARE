# AgeCare · Crea las tablas y los datos de demostración en Supabase (paso 2 de DESPLIEGUE.md).
# Uso (PowerShell, con Docker Desktop abierto):   .\deploy\crear_tablas_supabase.ps1
# La cadena de conexión se pide por pantalla (entrada oculta) y no se guarda en ningún archivo.
$ErrorActionPreference = "Stop"

$secure = Read-Host "Pega la cadena del Session pooler de Supabase (postgresql://...:5432/postgres)" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$url = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)

if ($url -notmatch "supabase\.") { Write-Error "Esa cadena no parece de Supabase."; exit 1 }
if ($url -notmatch ":5432/") { Write-Error "Usa la cadena del Session pooler (puerto 5432), no la del puerto 6543."; exit 1 }
if ($url -match "\[YOUR-PASSWORD\]|\[TU-PASSWORD\]") { Write-Error "Reemplaza [YOUR-PASSWORD] por tu contraseña de base de datos."; exit 1 }

$repo = Split-Path $PSScriptRoot -Parent

Write-Host "`n1/2 · Consola de administración (migraciones + datos demo)..." -ForegroundColor Cyan
Push-Location (Join-Path $repo "backend")
docker compose run --rm --no-deps -e "ADMIN_DATABASE_URL=$url" api sh -c "alembic upgrade head && python -m scripts.seed"
if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Error "Falló la consola."; exit 1 }
Pop-Location

Write-Host "`n2/2 · Sitio público (tablas + datos demo)..." -ForegroundColor Cyan
Push-Location (Join-Path $repo "backend-general")
docker compose run --rm --no-deps -e "GENERAL_DATABASE_URL=$url" api python -m scripts.seed
if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Error "Falló el sitio público."; exit 1 }
Pop-Location

Write-Host "`nListo. Ahora ejecuta deploy/supabase_seguridad.sql en Supabase > SQL Editor." -ForegroundColor Green
