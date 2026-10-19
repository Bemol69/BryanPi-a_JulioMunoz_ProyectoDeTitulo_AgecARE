# AgeCare — Marketing y Fidelización

## Nombre del proyecto

AgeCare — Marketing y Fidelización

## Descripción

Proyecto de Título (Duoc UC, sede Alameda) desarrollado para el cliente **Wellq
Co / Alloxentric**. El equipo diseñó e implementó un módulo de **marketplace
de cuidadoras con reseñas, puntos de fidelización y ranking**, integrado a la
Consola de Administración interna de Wellq Co. Como desarrollo adicional, se
construyó también un sitio público que simula la aplicación de cara a
familias y cuidadoras (registro, búsqueda, contacto), sobre la Especificación
de Endpoints Backend v1 entregada por Alloxentric.

El repositorio contiene dos aplicaciones independientes, cada una con su
propio backend y frontend:

```
backend/            API de la Consola de Administración (FastAPI + PostgreSQL)
frontend/           Consola de Administración (React + Vite + TypeScript)
backend-general/    API pública: registro, pacientes y marketplace de cuidadoras
webapp/             Sitio público (React + Vite + TypeScript)
Fase 1/              Evidencias académicas de la Fase 1 (Duoc UC)
Fase 2/              Evidencias académicas de la Fase 2 (informe de avance, presentación, capturas)
Registro de cambios/ Cambios del sistema con fecha (JSON y PDF)
```

## Revisar el proyecto en línea

El proyecto está publicado y se puede probar sin instalar nada. Cada cambio en la rama `main` se
despliega automáticamente.

| Qué es | Enlace |
|---|---|
| **Sitio público** (familias y cuidadoras) | <https://bryan-pi-a-julio-munoz-proyecto-de-sigma.vercel.app/> |
| **Consola de Administración** (staff de Wellq Co) | <https://bryan-pi-a-julio-munoz-proyecto-de-omega.vercel.app/login> |
| Documentación de la API del sitio (Swagger) | <https://agecare-api-general.vercel.app/api/v1/docs> |
| Documentación de la API de la Consola (Swagger) | <https://bryan-pi-a-julio-munoz-proyecto-de.vercel.app/api/v1/admin/docs> |

**Cuentas de prueba** (son datos de demostración, no reales):

| Dónde | Correo | Contraseña | Perfil |
|---|---|---|---|
| Sitio público | familia@demo.cl | Familia123! | Familia, con un adulto mayor ya creado |
| Sitio público | maria@cuidado.cl | Cuidado123! | Cuidadora con perfil publicado |
| Consola | admin@wellq.co.uk | Admin123! | Administrador (acceso completo) |

Las demás cuentas de prueba están más abajo, en cada sección de ejecución local.

**Recorrido sugerido (5 minutos):**

1. En el sitio, entrar como **familia**, buscar cuidadoras y abrir el perfil de una: se puede enviar una
   solicitud de contratación y conversar por el chat.
2. Entrar como **cuidadora** (en otra ventana o en modo incógnito): en *Solicitudes* aparece la solicitud
   para aceptarla o rechazarla, y en su perfil se ven sus documentos y las reseñas que recibe.
3. Entrar a la **Consola** como administrador: en *Marketplace de cuidadoras* se revisan los documentos y se
   aprueba o suspende un perfil, y en *Fidelización y ranking* se registra una reseña y se ve cómo cambian
   los puntos y el ranking.

> Los servicios gratuitos se "duermen" cuando no se usan: la primera carga puede tardar unos segundos.

## Tecnologías utilizadas

- **Lenguajes:** Python 3.12, TypeScript
- **Backend:** FastAPI, SQLAlchemy 2 (async), Alembic (migraciones), Pydantic,
  JWT (PyJWT) + Argon2 para autenticación
- **Frontend:** React 19, Vite, React Router
- **Base de datos:** PostgreSQL 16
- **Contenedores:** Docker y Docker Compose (un stack independiente por cada
  backend)
- **Control de versiones:** Git / GitHub

## Instrucciones para ejecutar el proyecto localmente

**Requisitos:** Docker Desktop y Node.js 20 o superior.

### 1. Consola de Administración

```bash
cd backend
docker compose up -d
```

Levanta PostgreSQL, aplica la migración y siembra datos de prueba. La API
queda en `http://localhost:8000` (documentación interactiva en
`/api/v1/admin/docs`).

```bash
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173`.

**Cuentas de prueba:**

| Correo | Contraseña | Rol |
|---|---|---|
| admin@wellq.co.uk | Admin123! | Administrador (acceso completo) |
| soporte@wellq.co.uk | Soporte123! | Soporte |
| analista@wellq.co.uk | Analista123! | Analista |
| editora@wellq.co.uk | Editora123! | Editor de contenido |

El menú lateral cambia según el rol: cada cuenta solo ve los módulos para los
que tiene permiso.

Para restablecer los datos de prueba:

```bash
docker compose exec api python -m scripts.seed
```

### 2. Sitio público

```bash
cd backend-general
docker compose up --build -d
```

API en `http://localhost:8001` (documentación en `/api/v1/docs`).

```bash
cd webapp
npm install
npm run dev -- --port 5174
```

Abre `http://localhost:5174`.

**Cuentas de prueba:**

| Correo | Contraseña | Tipo de cuenta |
|---|---|---|
| familia@demo.cl | Familia123! | Familia (con un paciente ya creado) |
| maria@cuidado.cl | Cuidado123! | Cuidadora (perfil ya publicado) |
| javiera@cuidado.cl / rocio@cuidado.cl / fernanda@cuidado.cl | Cuidado123! | Cuidadoras adicionales |

Para restablecer los datos de prueba:

```bash
docker compose exec api python -m scripts.seed
```

## Integrantes del equipo con sus roles

| Integrante | Rol |
|---|---|
| Bryan Piña Frías | Desarrollo full-stack y liderazgo técnico del proyecto |
| Julio Muñoz | Desarrollo backend y funcionalidades del sitio público |

## Metodología de trabajo del equipo

El equipo trabajó bajo **Scrum**, organizando el desarrollo en sprints con
entregas incrementales sobre el marketplace de cuidadoras (perfiles, mensajes,
reseñas, fidelización y ranking). El trabajo se coordinó mediante commits
frecuentes en GitHub, con revisión conjunta de cada funcionalidad antes de
integrarla a `main`.

## Arquitectura de la solución

La solución se compone de **dos sistemas independientes que se comunican
entre sí**:

- La **Consola de Administración** (`backend` + `frontend`) es el panel
  interno de Wellq Co, con su propia base de datos PostgreSQL. Ahí el staff
  aprueba o suspende perfiles de cuidadoras, gestiona el catálogo de
  artículos, y revisa el ranking de fidelización.
- El **sitio público** (`backend-general` + `webapp`) es la aplicación de
  cara a familias y cuidadoras, con su propia base de datos PostgreSQL
  independiente.
- Ambos backends se sincronizan mediante llamadas servidor-a-servidor
  autenticadas con una clave interna compartida: cuando una cuidadora publica
  su perfil o recibe una reseña en el sitio público, se reenvía
  automáticamente a la Consola para su revisión y para actualizar los puntos
  de fidelización y el ranking.

```
Familia / Cuidadora                 Staff Wellq Co
      │                                   │
      ▼                                   ▼
  webapp (5174)                     frontend (5173)
      │                                   │
      ▼                                   ▼
 backend-general (8001)  ──sync──►   backend (8000)
      │                                   │
      ▼                                   ▼
 PostgreSQL (sitio público)        PostgreSQL (consola)
```

## Despliegue en Vercel + Supabase

Las dos webs (consola y sitio público) y las dos APIs se despliegan como **cuatro proyectos de Vercel**
desde este mismo repositorio, con la base de datos y el almacenamiento de archivos en **Supabase**.
Cada push a `main` actualiza las webs automáticamente.

| Proyecto en Vercel | Root Directory |
|--------------------|----------------|
| AgeCare Consola (web de administración) | `frontend` |
| AgeCare Sitio (familias y cuidadoras)   | `webapp` |
| AgeCare API Admin                       | `backend` |
| AgeCare API General                     | `backend-general` |

Guía completa paso a paso, variables de entorno y solución de problemas: **[DESPLIEGUE.md](DESPLIEGUE.md)**.

## Qué probar

**Consola de Administración**
- Marketplace de cuidadoras: aprobar o suspender un perfil pendiente.
- Fidelización y ranking: registrar una reseña y ver cómo se actualizan los
  puntos y el orden del ranking en el momento.
- Dashboard de métricas de marketing.

**Sitio público**
- Registrarse como familia, crear el perfil de un adulto mayor.
- Registrarse como cuidadora, completar y publicar el perfil profesional.
- Buscar cuidadoras, contactar y dejar una reseña.
- Revisar los mensajes recibidos desde el panel de la cuidadora.

## Notas

- El estado "Degradado" en Estado Operativo es parte de los datos de prueba
  (simula latencia en el asistente de IA), no un error de la consola.
- En Uso Comercial, el periodo "Este mes" puede aparecer en cero porque los
  datos históricos del seed están anclados a agosto de 2026; usa "30 días"
  para ver la serie completa.
- Las carpetas `Fase 1/` y `Fase 2/` contienen las evidencias académicas
  solicitadas por Duoc UC. En `Fase 2/` están el informe de avance, la guía de
  desarrollo, la presentación, las capturas del sistema y el archivo
  `Aporte del equipo.md`, que muestra el aporte de cada integrante a partir
  del historial de Git. Los archivos marcados como pendientes en
  `PENDIENTE.md` de la Fase 1 deben completarse antes de la fecha de entrega.
- Los cambios del sistema, con su fecha, están en `Registro de cambios/`.
