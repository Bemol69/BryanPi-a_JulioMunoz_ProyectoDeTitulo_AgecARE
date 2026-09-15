# AgeCare — Marketing y Fidelización

Proyecto de Título (Duoc UC) para Wellq Co / Alloxentric. Este repositorio
contiene dos aplicaciones que corren de forma independiente:

```
backend/            API de la Consola de Administración (FastAPI + PostgreSQL)
frontend/           Consola de Administración (React + Vite + TypeScript)
backend-general/    API pública: registro, pacientes y marketplace de cuidadoras
webapp/             Sitio público (React + Vite + TypeScript)
```

La **Consola de Administración** es nuestro entregable de Fase 1: marketplace
de cuidadoras con reseñas, puntos de fidelización y ranking, dentro del panel
interno de Wellq Co. El **sitio público** es un desarrollo adicional que
simula la aplicación de cara a familias y cuidadoras (registro, búsqueda,
contacto), construido sobre la Especificación de Endpoints Backend v1.

## Requisitos

- Docker Desktop
- Node.js 20 o superior

## 1. Consola de Administración

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

## 2. Sitio público

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

Las dos aplicaciones usan bases de datos distintas. Cuando una cuidadora
publica su perfil en el sitio público, se envía automáticamente a la Consola
de Administración y queda pendiente de aprobación por el staff.

## Notas

- El estado "Degradado" en Estado Operativo es parte de los datos de prueba
  (simula latencia en el asistente de IA), no un error de la consola.
- En Uso Comercial, el periodo "Este mes" puede aparecer en cero porque los
  datos históricos del seed están anclados a agosto de 2026; usa "30 días"
  para ver la serie completa.
