# Prueba de carga · 500 usuarios simultáneos · uso normal (ya tienen cuenta) pool100
Fecha: 2026-11-12 15:34 · duración 119.1 s · 3903 peticiones · 33 peticiones/s · errores 555 (14.22 %)

| Acción | Peticiones | Errores | p50 ms | p95 ms | p99 ms | Máx ms |
|---|---:|---:|---:|---:|---:|---:|
| completar perfil | 70 | 7 | 59759 | 68006 | 68905 | 68905 |
| listar familiares | 399 | 208 | 33006 | 50355 | 52416 | 52709 |
| crear familiar | 399 | 33 | 14069 | 45316 | 50591 | 50969 |
| contactar (abre chat) | 314 | 6 | 9457 | 15660 | 19120 | 21215 |
| buscar cuidadoras | 399 | 85 | 9377 | 30799 | 43480 | 45363 |
| perfil de cuidadora | 314 | 13 | 9194 | 18556 | 21507 | 22080 |
| mis mensajes | 70 | 6 | 6736 | 16468 | 25327 | 25327 |
| mi perfil | 70 | 13 | 5807 | 32487 | 36938 | 36938 |
| mis reseñas | 70 | 14 | 5766 | 30286 | 48378 | 48378 |
| enviar mensaje | 616 | 3 | 5684 | 10610 | 12692 | 22173 |
| ficha del familiar | 366 | 163 | 5398 | 41432 | 47218 | 47811 |
| abrir chat | 308 | 0 | 3900 | 6725 | 8455 | 10250 |
| listar chats | 384 | 4 | 3640 | 8525 | 17248 | 23933 |
| login Consola | 31 | 0 | 3107 | 5021 | 5054 | 5054 |
| Consola: cuidadoras | 31 | 0 | 960 | 2488 | 2535 | 2535 |
| Consola: ranking | 31 | 0 | 603 | 2011 | 2350 | 2350 |
| Consola: métricas fidelización | 31 | 0 | 560 | 2173 | 2464 | 2464 |

**Todas las peticiones:** p50 7449 ms · p95 43155 ms · p99 59573 ms

Errores distintos:
- crear familiar: 500 {"error":{"code":"INTERNAL_ERROR","message":"Error interno. Revisa el request_id
- listar familiares: ECONNRESET
- listar familiares: 500 {"error":{"code":"INTERNAL_ERROR","message":"Error interno. Revisa el request_id
- completar perfil: 500 {"error":{"code":"INTERNAL_ERROR","message":"Error interno. Revisa el request_id
- mi perfil: ECONNRESET
- mi perfil: 500 {"error":{"code":"INTERNAL_ERROR","message":"Error interno. Revisa el request_id
- ficha del familiar: ECONNRESET
- ficha del familiar: 500 {"error":{"code":"INTERNAL_ERROR","message":"Error interno. Revisa el request_id
- mis reseñas: ECONNRESET
- mis reseñas: 500 {"error":{"code":"INTERNAL_ERROR","message":"Error interno. Revisa el request_id
- buscar cuidadoras: 500 {"error":{"code":"INTERNAL_ERROR","message":"Error interno. Revisa el request_id
- buscar cuidadoras: ECONNRESET
