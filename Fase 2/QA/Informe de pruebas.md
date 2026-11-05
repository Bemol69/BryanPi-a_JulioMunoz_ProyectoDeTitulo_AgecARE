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
