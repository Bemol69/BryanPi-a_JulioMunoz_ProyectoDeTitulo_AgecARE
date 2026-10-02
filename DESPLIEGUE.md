# Despliegue de AgeCare en Vercel + Supabase

Objetivo: que todo lo que se suba a GitHub (`main`) se vea reflejado solo en las dos webs.

```
GitHub (este repo)
   │  cada push a main = deploy automático
   ▼
Vercel — 4 proyectos del mismo repo
   ├─ AgeCare Consola      (frontend/)         → web de AgeCare Administración
   ├─ AgeCare Sitio        (webapp/)           → web de familias y cuidadoras
   ├─ AgeCare API Admin    (backend/)          → FastAPI de la consola
   └─ AgeCare API General  (backend-general/)  → FastAPI del sitio público
   ▼
Supabase — 1 proyecto
   ├─ Postgres  (las tablas de las dos APIs; no tienen nombres repetidos)
   └─ Storage   (fotos de perfil, fotos de adultos mayores y documentos)
```

Un solo proyecto de Supabase alcanza: las tablas de la consola (`admin_*`, `marketplace_*`,
`metrics_*`…) y las del sitio (`users`, `patients`, `caregiver_*`…) no se pisan.

> **Antes de empezar.** Todo se hace desde los paneles de Supabase y Vercel con tu cuenta.
> Las contraseñas y llaves se pegan solo ahí (y en tu terminal), nunca en el repo ni en el chat.

---

## Paso 1 · Crear el proyecto en Supabase

1. <https://supabase.com/dashboard> → **New project**.
2. Nombre `agecare`, región **South America (São Paulo)**, y una **contraseña de base de datos**
   (usa solo letras y números, sin símbolos; guárdala).
3. Cuando termine de crearse, abre **Connect** (botón arriba) y copia dos cadenas de conexión:
   - **Session pooler** (puerto `5432`) → la usarás desde tu PC para crear tablas (**URL-SESION**).
   - **Transaction pooler** (puerto `6543`) → la usarás en Vercel (**URL-VERCEL**).

   Ambas tienen la forma `postgresql://postgres.xxxx:[TU-PASSWORD]@aws-0-sa-east-1.pooler.supabase.com:PUERTO/postgres`.
   Reemplaza `[TU-PASSWORD]` por tu contraseña. No hace falta cambiar el prefijo ni agregar parámetros:
   la API lo adapta sola.
4. En **Project Settings → API** anota la **Project URL** (`https://xxxx.supabase.co`) y la llave
   **`service_role`** (o *secret key*). Esa llave es secreta: va solo en Vercel.

## Paso 2 · Crear las tablas y los datos de demostración

> **Si reutilizas un proyecto de Supabase que ya tiene otras tablas** (p. ej. `pymeclic-dashboard`): antes de
> seguir, en **SQL Editor** corre `select tablename from pg_tables where schemaname = 'public';`. Si aparece
> alguna tabla con el mismo nombre que las de AgeCare (`users`, `patients`, `features`, `system_settings`,
> `market_products`, `alembic_version`…), **no continúes**: `create_all` la saltaría y el seed borraría sus
> datos. Con el proyecto vacío no hay problema.

Desde tu PC, con Docker Desktop abierto, en PowerShell, parado en la carpeta del repo:

```powershell
.\deploy\crear_tablas_supabase.ps1
```

El script te pide la cadena **Session pooler** (puerto `5432`) con entrada oculta, crea las tablas de
la consola y del sitio y carga los datos de demostración. No guarda la cadena en ningún archivo.

Luego, en Supabase → **SQL Editor**, pega y ejecuta el contenido de
[`deploy/supabase_seguridad.sql`](deploy/supabase_seguridad.sql). Activa la seguridad por filas
en todas las tablas para que nadie las pueda leer por la API pública de Supabase.

> ⚠️ Los scripts `seed` **borran y recargan** los datos de demostración. Córrelos solo esta primera
> vez (o cuando quieras reiniciar la demo), no en cada despliegue.

## Paso 3 · Crear los 4 proyectos en Vercel

Para cada uno: <https://vercel.com/new> → **Import** el repositorio
`Bemol69/BryanPi-a_JulioMunoz_ProyectoDeTitulo_AgecARE` → en **Root Directory** pulsa *Edit* y elige
la carpeta → agrega las variables → **Deploy**. Respeta este orden, porque cada uno necesita la URL del anterior.

Genera los secretos así (uno distinto para cada API, mínimo 32 caracteres):

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 3.1 · AgeCare API Admin — Root Directory `backend`

| Variable | Valor |
|---|---|
| `ADMIN_DATABASE_URL` | URL-VERCEL (puerto 6543) |
| `ADMIN_JWT_SECRET` | secreto generado |
| `ADMIN_ENVIRONMENT` | `prod` |
| `ADMIN_INTERNAL_SYNC_KEY` | otro secreto generado (se repite en 3.2) |

Al terminar, abre `https://<url-del-proyecto>/api/v1/admin/docs`: debe mostrar la documentación de la API.
Anota la URL → **URL-ADMIN**.

### 3.2 · AgeCare API General — Root Directory `backend-general`

| Variable | Valor |
|---|---|
| `GENERAL_DATABASE_URL` | URL-VERCEL (puerto 6543) |
| `GENERAL_JWT_SECRET` | secreto generado (distinto al anterior) |
| `GENERAL_ENVIRONMENT` | `prod` |
| `GENERAL_ADMIN_SYNC_URL` | `https://<URL-ADMIN>/api/v1/admin` |
| `GENERAL_ADMIN_SYNC_KEY` | el mismo valor de `ADMIN_INTERNAL_SYNC_KEY` |
| `GENERAL_SUPABASE_URL` | Project URL del paso 1.4 |
| `GENERAL_SUPABASE_SERVICE_KEY` | llave `service_role` del paso 1.4 |

Prueba `https://<url-del-proyecto>/api/v1/docs`. Anota la URL → **URL-GENERAL**.
El bucket de archivos (`agecare-uploads`) se crea solo con la primera foto que se suba.

### 3.3 · AgeCare Consola — Root Directory `frontend`

| Variable | Valor |
|---|---|
| `VITE_API_BASE_URL` | `https://<URL-ADMIN>/api/v1/admin` |

### 3.4 · AgeCare Sitio — Root Directory `webapp`

| Variable | Valor |
|---|---|
| `VITE_API_BASE_URL` | `https://<URL-GENERAL>/api/v1` |

### 3.5 · Permitir que las webs llamen a las APIs (CORS)

Con las URLs de 3.3 (**URL-CONSOLA**) y 3.4 (**URL-SITIO**) ya creadas, agrega en cada API una variable más
y haz **Redeploy** (Deployments → ⋯ → Redeploy):

| Proyecto | Variable | Valor |
|---|---|---|
| API Admin | `CORS_ORIGINS` | `https://<URL-CONSOLA>` |
| API General | `CORS_ORIGINS` | `https://<URL-SITIO>` |

(Sin barra final. Si usas dominio propio, sepáralos con comas.)

## Paso 4 · Probar

1. Abre URL-SITIO → **Iniciar sesión** con `familia@demo.cl` / `Familia123!`.
2. Abre URL-CONSOLA → `admin@wellq.co.uk` / `Admin123!`.
3. En el sitio entra como cuidadora (`maria@cuidado.cl` / `Cuidado123!`), sube una foto: debe quedar en
   Supabase → **Storage → agecare-uploads**.

Las cuentas de demostración están en el README.

## Día a día: GitHub → Vercel

- Cada **push a `main`** despliega solo los proyectos cuya carpeta cambió (Vercel lo hace por defecto
  en repos con *Root Directory*).
- Cada **rama o Pull Request** genera una URL de vista previa para revisar antes de mezclar.
- Cambios de **base de datos**:
  - Consola: crea la migración Alembic en `backend/alembic/versions/`, haz push y aplícala con
    `docker compose run --rm --no-deps -e ADMIN_DATABASE_URL="URL-SESION" api alembic upgrade head`
    (desde `backend/`).
  - Sitio público: hoy las tablas se crean con `create_all`, que **no modifica tablas existentes**. Si se
    agrega una columna a un modelo, hay que aplicarla a mano en el *SQL Editor* de Supabase
    (`alter table ... add column ...`). Pendiente de equipo: pasar `backend-general` a Alembic.

## Límites y puntos a tener en cuenta

- **Archivos:** Vercel acepta peticiones de hasta 4,5 MB, por eso fotos y documentos se limitaron a 4 MB.
- **Privacidad:** el bucket `agecare-uploads` es público (la URL de cada archivo es larga y no se puede
  adivinar, pero quien la tenga la ve). Sirve para la demo con datos de prueba; antes de recibir cédulas o
  antecedentes reales hay que pasar los documentos a un bucket privado con URLs firmadas.
- **Primera carga lenta:** las funciones de Vercel se "duermen"; la primera petición tras un rato sin uso puede demorar unos segundos.
- **Plan Hobby de Vercel:** es para uso personal/no comercial; sirve para el proyecto académico.

## Si algo falla

| Síntoma | Qué revisar |
|---|---|
| El login muestra error de red / CORS en la consola del navegador | `CORS_ORIGINS` de la API correspondiente (paso 3.5) y que `VITE_API_BASE_URL` termine en `/api/v1` o `/api/v1/admin`. Tras cambiar una variable hay que hacer **Redeploy**. |
| La API responde 500 | Vercel → el proyecto → **Logs**. Casi siempre es `DATABASE_URL` mal copiada (contraseña) o tablas sin crear (paso 2). |
| Error `prepared statement ... already exists` | La URL de Vercel debe ser la del **Transaction pooler** (puerto `6543`). |
| Falla el paso 2 con error de conexión | Usa la cadena del **Session pooler** (`5432`), no la conexión directa. |
| La foto no se sube (502 `STORAGE_ERROR`) | `GENERAL_SUPABASE_URL` y `GENERAL_SUPABASE_SERVICE_KEY` en la API General. |
| Las rutas del sitio dan 404 al recargar | Que el proyecto tenga el `vercel.json` de su carpeta y el Root Directory correcto. |
| Las cuidadoras nuevas no aparecen en la consola | `GENERAL_ADMIN_SYNC_URL` / `GENERAL_ADMIN_SYNC_KEY` y que coincida con `ADMIN_INTERNAL_SYNC_KEY`. |
