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
```

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
- La carpeta `Fase 1/` contiene las evidencias académicas solicitadas por
  Duoc UC para la entrega de Fase 1. Los archivos marcados como pendientes en
  `PENDIENTE.md` deben completarse antes de la fecha de entrega.
