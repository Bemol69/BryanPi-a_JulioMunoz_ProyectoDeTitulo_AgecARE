# Pruebas de carga y rendimiento

`carga.mjs` simula usuarios reales usando el sitio y la Consola a la vez (necesita Node 18 o superior, no instala nada):

| Tipo de usuario | Peso | Recorrido |
|---|---|---|
| Familia | 80 % | se registra → crea un familiar → busca cuidadoras → abre un perfil → contacta (abre un chat) → manda 2 mensajes → revisa sus chats |
| Cuidadora | 15 % | se registra → completa su perfil → revisa su perfil, reseñas, mensajes y chats |
| Staff | 5 % | entra a la Consola → lista cuidadoras → ranking → métricas de fidelización |

```bash
# con las dos APIs levantadas (puertos 8000 y 8001)
node pruebas/carga.mjs --usuarios 300 --modo uso        # uso normal: ya tienen cuenta
node pruebas/carga.mjs --usuarios 100 --modo registro   # peor caso: todos crean su cuenta a la vez
```

Imprime una tabla por acción (p50 / p95 / p99 en milisegundos, errores) y la guarda en `pruebas/resultados/`.
**Crea cuentas de prueba: úsalo solo contra un ambiente de pruebas, nunca contra producción.**

## Resultados del 12 de noviembre de 2026

Entorno: un PC de escritorio (4 núcleos / 8 hilos, 14 GB) que a la vez ejecutaba el generador de carga, las dos APIs
(2 procesos cada una), PostgreSQL 16 en Docker, Chrome y otros programas. Es un entorno **más débil y más ruidoso que
producción**: en Vercel cada petición corre en su propia función y se reparte sola; aquí todo comparte una sola máquina.
Sirve para encontrar fallas y comparar antes/después, no para prometer tiempos exactos.

| Escenario | Peticiones | Errores | p50 | p95 | Rendimiento |
|---|---:|---:|---:|---:|---:|
| 100 usuarios simultáneos, uso normal | 904 | **0** | 0,6 s | 5,8 s | 50 peticiones/s |
| 300 usuarios simultáneos, uso normal | 2 779 | **0** | 4,4 s | 16,8 s | 43 peticiones/s |
| 500 usuarios simultáneos, uso normal | 3 903 | 555 (14 %) | 7,4 s | 43 s | 33 peticiones/s |
| 100 usuarios creando cuenta a la vez | 937 | **0** | 1,4 s | 9,6 s | 22 peticiones/s |

- **Hasta 300 usuarios simultáneos no hay errores**: todos terminan su recorrido, aunque más lento (las peticiones hacen fila).
- **Con 500 en una sola máquina se satura** (errores 500 por agotarse las conexiones a la base mientras las peticiones esperan
  turno). Para esa escala se agregan procesos o instancias (en Vercel ocurre solo) y se sube `DB_POOL_SIZE` /
  `DB_MAX_OVERFLOW` junto con `max_connections` de PostgreSQL.
- Sin carga, una consulta típica responde en 25 a 40 ms y un login en ~80 ms.

### Qué se encontró y se corrigió gracias a estas pruebas

| Hallazgo | Efecto | Solución |
|---|---|---|
| Las funciones de Vercel corrían en Washington y la base está en São Paulo | ~1 s extra por petición (un login de correo inexistente, con una sola consulta, tardaba 1,3 s) | `"regions": ["gru1"]` en `backend/vercel.json` y `backend-general/vercel.json` |
| El cálculo de contraseñas (Argon2) se ejecutaba en el hilo principal | Mientras un usuario entraba, todos los demás esperaban (~150 ms de CPU cada vez) | Se calcula en hilos aparte, con un tope, y con la configuración mínima de OWASP (19 MiB, 2 pasadas, 1 hilo): ~4× más inicios de sesión por segundo |
| La API respondía «creado» y guardaba **después** | La petición siguiente podía recibir 403/404 al azar (más probable con carga o con la base lejos) | La sesión de base de datos se declara con `scope="function"` |
| Se agotaba el grupo de conexiones (5 + 10 por proceso) | Errores 500 con cientos de usuarios | Grupo configurable (20 + 20 por defecto); las conexiones se liberan antes de esperar a la otra API o al cálculo de contraseña |
| 3 consultas `DELETE` de limpieza de chats en cada visita al chat | La mitad de las consultas del chat eran de limpieza | Se limpia como máximo una vez cada 5 minutos |
| El listado de reseñas hacía una consulta por reseña | Lento con muchas reseñas | Una sola consulta |
| El generador en Python (httpx) gastaba más CPU que el propio servidor | Las mediciones eran falsas | Se reescribió en Node (`carga.mjs`) |

## Otras pruebas del repositorio

| Qué | Dónde | Cómo |
|---|---|---|
| Pruebas automáticas de la Consola (73) | `backend/tests` | `cd backend && python -m pytest -q` |
| Pruebas automáticas del sitio (80) | `backend-general/tests` | `cd backend-general && python -m pytest -q` |
| Seguridad (78 de las anteriores) | `test_security.py` en cada carpeta | ídem |
| Recorrido completo con navegador | `e2e/run_e2e.py` | ver `e2e/README.md` |
