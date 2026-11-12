# Informe de pruebas previo al lanzamiento (5 de noviembre de 2026)

Entorno: copia local del sistema con bases de datos nuevas y datos de demostración. No se crearon cuentas en producción.

## Resultado

| Prueba | Resultado |
|---|---|
| Pruebas automáticas de la Consola (`backend`) | 34 aprobadas |
| Pruebas automáticas del sitio (`backend-general`) | 30 aprobadas |
| Compilación de la Consola y del sitio | Sin errores |
| Recorrido de punta a punta con la interfaz (`e2e/run_e2e.py`) | 33 de 34 pasos correctos; el paso restante falló por una espera demasiado corta en la propia prueba y se corrigió |

## Qué cubre el recorrido de punta a punta

1. Registro de familia con una cuenta nueva, error por correo repetido, contraseña incorrecta y ruta protegida sin sesión.
2. Creación de un familiar con foto y alergia, y su ficha.
3. Registro de un cuidador, perfil completo, foto y documentos; rechazo de un archivo de formato inválido y de uno de más de 4 MB.
4. El cuidador no aparece en las búsquedas mientras el equipo no lo apruebe.
5. Aprobación de documentos y perfil desde la Consola; el cuidador aparece con su foto.
6. Solicitud de contratación, chat en ambos sentidos, aceptación, marca «Trabajando» y bloqueo para otra familia.
7. Cierre del trabajo, reseña, reseña visible para el cuidador y puntos en el ranking de la Consola.
8. Menú de la Consola sin Contenido ni Moderación, sin la etiqueta «NUEVO», con fotos de las cuidadoras, y un rol de editor que entra directo a Marketplace.
9. Todas las pantallas cargan sin errores en el navegador; cierre de sesión.

## Cambios hechos a partir de las pruebas

- Consola: se quitaron Contenido y Moderación y la etiqueta «NUEVO»; la Consola abre en Marketplace; se muestran las fotos de cuidadoras y cuidadores (listado, ranking y ficha).
- Sitio: botón de cámara para cambiar la foto desde el perfil; si una foto no carga se muestran las iniciales; las listas piden hasta 100 resultados en vez de quedarse en 20.
- Seguridad: se verifica que el archivo subido sea realmente una imagen o un PDF; los documentos tienen un nombre imposible de adivinar; en la web publicada ya no viene una cuenta precargada en el ingreso y las cuentas de ejemplo se pueden ocultar con `VITE_SHOW_DEMO_ACCESS=false`.
- Datos de ejemplo con fotos (ilustraciones) y dos cuidadores hombres.
- Integración continua en GitHub y correcciones de las dependencias de prueba.
- `lang="es"` y descripción en las páginas base.
- Eliminar familiares y cuentas: ver «Eliminación de datos» más abajo.

## Pendiente antes de recibir personas reales

- Recuperación de contraseña (necesita un servicio de correo).
- Términos de uso y política de privacidad con aceptación al registrarse (requiere texto legal).
- Documentos de identidad en un bucket privado con URLs firmadas.
- Decidir si el repositorio debe seguir público (incluye código del cliente y cuentas de demostración).
- Detalles en la lista de verificación de `DESPLIEGUE.md`.

## Eliminación de datos (agregada el 5 de noviembre de 2026)

- La familia puede eliminar el perfil de un familiar (desde la tarjeta o desde su ficha). Si tiene una cuidadora trabajando, se bloquea hasta cerrar ese trabajo.
- Cualquier persona puede eliminar su cuenta desde «Mi cuenta», confirmando con su contraseña. Se borran sus familiares, chats, solicitudes, reseñas y, en las cuidadoras, el perfil y los documentos. Con un trabajo en curso se bloquea.
- Desde la Consola, el equipo puede eliminar el perfil de una cuidadora, y con él su cuenta del sitio. Si el sitio no responde, no se borra nada, para no dejar ambos sistemas distintos.
- Cubierto con 7 pruebas nuevas del sitio y 3 de la Consola, y con una prueba en el navegador que recorre el flujo completo.

---

# Ronda de seguridad, carga y requisitos (12 de noviembre de 2026)

Entorno: copia local con **PostgreSQL 16 real** (Docker), las dos APIs y las dos webs; no se tocó producción.

## Resultado

| Prueba | Resultado |
|---|---|
| Pruebas automáticas de la Consola (`backend`) | **73 aprobadas** (antes 34) |
| Pruebas automáticas del sitio (`backend-general`) | **80 aprobadas** (antes 30) |
| Migraciones de la Consola (Alembic 0001 → 0006) sobre PostgreSQL | Sin errores |
| Compilación de la Consola y del sitio | Sin errores |
| Interfaz de moderación de reseñas (archivar, restaurar, eliminar, puntos) con navegador real | 9 de 9 comprobaciones correctas |
| Recorrido de punta a punta (`e2e/run_e2e.py`) sobre base limpia | Mejor corrida 32 de 34. Con el equipo cargado el resultado varió entre 12 y 32 sin cambiar el código: los fallos eran esperas fijas de la propia prueba, que se cambiaron por esperas a la condición real. Conviene repetirla con el equipo libre antes de presentar |
| Carga: 100 / 300 usuarios simultáneos | **0 errores**; 500 satura una sola máquina (14 % de errores). Detalle en `pruebas/README.md` |

## 1. Seguridad (78 pruebas nuevas)

| Ataque o riesgo | Qué se probó | Resultado |
|---|---|---|
| Inyección SQL | 8 cargas típicas (`' OR '1'='1`, `'; DROP TABLE…`, `UNION SELECT…`, etc.) en el login, en filtros de búsqueda, en textos guardados y en identificadores | Nunca se entra; el texto se guarda como texto; las tablas siguen intactas |
| Scripts en textos (XSS) | 5 cargas | Se devuelven como JSON inerte, con `nosniff` |
| Tokens falsos | sin firma (`alg: none`), firmado con otra clave, vencido, sin vencimiento, de usuario inexistente, basura, otro algoritmo; y un analista que edita su token para ser admin | Todos rechazados |
| Rutas sin sesión | Se recorren **todas** las rutas del esquema OpenAPI sin sesión | Todas responden 401/403 |
| Claves internas | Todas las rutas internas sin clave, con clave inventada y vacía | Rechazadas |
| Datos de otras personas | Una familia intenta ver o borrar el familiar de otra; leer un chat ajeno; usar endpoints del otro tipo de cuenta | Bloqueado |
| Permisos por rol (Consola) | Analista y moderador intentan escribir | 403 |
| Fuerza bruta | 5 contraseñas incorrectas y luego la correcta | **Falla encontrada y corregida** (ver abajo) |
| Entradas hostiles | Cuerpos de 2 MB, JSON roto, tipos incorrectos, `../../etc/passwd` | 422 / 404, sin errores 500 |
| Cabeceras y CORS | Cabeceras de seguridad; origen ajeno | Cabeceras presentes; origen ajeno sin permiso |

**Falla grave encontrada:** en el sitio público el bloqueo de cuenta tras 5 contraseñas incorrectas no funcionaba: el contador de
intentos se guardaba y luego se revertía al responder el error 401, así que se podían probar contraseñas sin límite. Corregido;
ahora la cuenta se bloquea 15 minutos (la Consola ya lo hacía bien).

Otros hallazgos corregidos: faltaban cabeceras de seguridad (APIs y webs); el tiempo de respuesta del login permitía saber qué correos
tienen cuenta; y no había aviso si en Vercel quedaba un secreto de ejemplo.

## 2 y 4. Usuarios simultáneos y fluidez

Ver `pruebas/README.md` (tabla de resultados y de hallazgos). Lo más importante: las APIs corrían en Washington con la base en São
Paulo (~1 s extra por petición), el cálculo de contraseñas frenaba al servidor, la API respondía antes de guardar y el grupo de
conexiones se agotaba con carga.

## 3. Requisitos

Los requisitos del sistema se verifican con tres capas: las pruebas automáticas de cada API (reglas de negocio), el recorrido con
navegador (flujos de usuario) y las pruebas de seguridad. Requisitos nuevos de esta ronda:

| Requisito | Cómo se comprueba |
|---|---|
| Las malas calificaciones influyen en los puntos (4–5★ suma, 3★ neutra, 2★ resta 5, 1★ resta 15) | `backend/tests/test_review_moderation.py` (5 casos) + comprobación en la interfaz |
| Una cuidadora con malas reseñas baja en el ranking | `test_bad_reviews_push_a_caregiver_down_the_ranking` |
| La Consola muestra las calificaciones de cada cuidadora por separado | Interfaz: Fidelización (historial) y ficha en Marketplace |
| Se pueden archivar (reversible) o eliminar | Pruebas de la Consola y del sitio; archivar deshace el efecto en nota y puntos, restaurar lo devuelve |
| El sitio público refleja la moderación | `test_staff_can_archive_restore_and_delete_a_review_from_the_console` |
| Si el sitio no responde, no se cambia nada | `test_nothing_changes_if_the_site_cannot_be_told` |
| Solo quien puede escribir modera | `test_deleting_a_review_removes_it_and_its_points` (analista 403) |

## Fallas de la interfaz encontradas

- Consola: en la ficha de una cuidadora, los botones de revisar documentos se volvían a habilitar antes de recargar el detalle; un
  segundo clic rápido daba un error 409 confuso. Ahora esperan a la recarga.
