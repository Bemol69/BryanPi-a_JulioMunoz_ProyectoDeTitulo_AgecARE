# Prueba de punta a punta

`run_e2e.py` maneja el navegador como lo haría una persona y recorre el sistema completo:

1. Una familia se registra, se prueban los errores de acceso y crea el perfil de un adulto mayor con foto.
2. Un cuidador se registra, completa su perfil, sube foto y documentos (incluye un archivo de formato inválido y
   uno de más de 4 MB) y comprueba que **no** aparece en las búsquedas mientras no esté aprobado.
3. El equipo, desde la Consola, aprueba sus documentos y su perfil.
4. La familia lo encuentra, envía una solicitud de contratación y conversa por el chat; el cuidador la acepta.
5. Se comprueba la marca «Trabajando», que otra familia no puede solicitarlo, el cierre del trabajo, la reseña y que
   la Consola refleje los puntos y las fotos.
6. Se revisa el menú de la Consola por rol y que ninguna pantalla muestre errores en el navegador.

## Cómo correrla

```bash
pip install playwright                 # y tener Google Chrome instalado
# con las APIs y las dos webs en marcha (ver README principal):
python e2e/run_e2e.py
```

Al terminar deja capturas de cada etapa y `resultados.json` en `e2e/resultados/` (carpeta que Git ignora).
Cada ejecución crea cuentas con un correo distinto, así que se puede repetir sin limpiar la base de datos.
**No la apuntes a un entorno con datos reales.**
