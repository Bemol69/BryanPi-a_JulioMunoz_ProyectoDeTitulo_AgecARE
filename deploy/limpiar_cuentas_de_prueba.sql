-- Limpieza de las cuentas y datos de prueba (por ejemplo «bryan», «abuela coco», etc.).
--
-- Deja solo las cuentas de demostración y borra todo lo demás: usuarios, perfiles de cuidadoras, documentos,
-- reseñas, chats, solicitudes, trabajos y familiares, tanto del sitio como de la Consola (comparten base de datos).
--
-- CÓMO USARLO (Supabase → SQL Editor):
--   1. Ejecuta el PASO 1 (solo lectura) y revisa qué hay. Si quieres conservar alguna cuenta o familiar más,
--      agrégalo a las listas del PASO 2.
--   2. Ejecuta el PASO 2. Termina en ROLLBACK, es decir, NO borra nada y solo te muestra qué pasaría.
--      Cuando el resumen te cuadre, cambia la última línea «ROLLBACK;» por «COMMIT;» y ejecútalo de nuevo.
--   3. Las fotos y documentos subidos quedan en Storage aunque se borre la cuenta: usa la lista del PASO 1b
--      para borrarlos a mano en Supabase → Storage → agecare-uploads (opcional).
-- No toca las cuentas del equipo de la Consola (admin_users).

-- =====================================================================================
-- PASO 1 · Ver qué hay (solo lectura)
-- =====================================================================================
SELECT u.account_type AS tipo, u.full_name AS nombre, u.email AS correo, u.created_at AS creada
  FROM users u ORDER BY u.created_at;

SELECT p.full_name AS familiar, string_agg(u.email, ', ') AS cuentas_con_acceso
  FROM patients p
  LEFT JOIN patient_members pm ON pm.patient_id = p.id
  LEFT JOIN users u ON u.id = pm.user_id
 GROUP BY p.id, p.full_name ORDER BY p.full_name;

SELECT name AS cuidadora_en_la_consola, email, status FROM marketplace_caregivers ORDER BY submitted_at;

-- PASO 1b · Archivos de Storage que quedarían huérfanos (bucket agecare-uploads)
SELECT 'avatars/' || u.id AS carpeta_o_prefijo, u.email AS de
  FROM users u WHERE u.avatar_url IS NOT NULL
UNION ALL
SELECT 'documents/' || cp.id, u.email
  FROM caregiver_profiles cp JOIN users u ON u.id = cp.user_id
UNION ALL
SELECT 'patients/' || p.id, p.full_name FROM patients p WHERE p.photo_url IS NOT NULL;

-- =====================================================================================
-- PASO 2 · Borrar (termina en ROLLBACK: cámbialo por COMMIT cuando estés conforme)
-- =====================================================================================
BEGIN;

-- Cuentas que SE CONSERVAN (correos en minúscula). Todo lo demás se borra.
CREATE TEMP TABLE conservar_cuentas (email text PRIMARY KEY) ON COMMIT DROP;
INSERT INTO conservar_cuentas VALUES
  ('familia@demo.cl'),
  ('maria@cuidado.cl'),
  ('javiera@cuidado.cl'),
  ('rocio@cuidado.cl'),
  ('fernanda@cuidado.cl'),
  ('paula@cuidado.cl');

-- Familiares que SE CONSERVAN (por nombre exacto). Todos los demás se borran, estén en la cuenta que estén.
CREATE TEMP TABLE conservar_familiares (nombre text PRIMARY KEY) ON COMMIT DROP;
INSERT INTO conservar_familiares VALUES ('Elena Muñoz');

CREATE TEMP TABLE u_borrar ON COMMIT DROP AS
  SELECT id FROM users WHERE lower(email) NOT IN (SELECT email FROM conservar_cuentas);
CREATE TEMP TABLE cp_borrar ON COMMIT DROP AS
  SELECT id FROM caregiver_profiles WHERE user_id IN (SELECT id FROM u_borrar);
CREATE TEMP TABLE pa_borrar ON COMMIT DROP AS
  SELECT id FROM patients WHERE full_name NOT IN (SELECT nombre FROM conservar_familiares);

-- Sitio público
DELETE FROM chat_messages
 WHERE sender_user_id IN (SELECT id FROM u_borrar)
    OR conversation_id IN (SELECT id FROM chat_conversations
                            WHERE family_user_id IN (SELECT id FROM u_borrar)
                               OR caregiver_profile_id IN (SELECT id FROM cp_borrar));
DELETE FROM chat_conversations
 WHERE family_user_id IN (SELECT id FROM u_borrar) OR caregiver_profile_id IN (SELECT id FROM cp_borrar);
DELETE FROM hire_requests
 WHERE family_user_id IN (SELECT id FROM u_borrar) OR caregiver_profile_id IN (SELECT id FROM cp_borrar)
    OR patient_id IN (SELECT id FROM pa_borrar);
DELETE FROM caregiver_engagements
 WHERE family_user_id IN (SELECT id FROM u_borrar) OR caregiver_profile_id IN (SELECT id FROM cp_borrar)
    OR patient_id IN (SELECT id FROM pa_borrar);
DELETE FROM contact_requests
 WHERE family_user_id IN (SELECT id FROM u_borrar) OR caregiver_profile_id IN (SELECT id FROM cp_borrar);
DELETE FROM caregiver_reviews
 WHERE author_user_id IN (SELECT id FROM u_borrar) OR caregiver_profile_id IN (SELECT id FROM cp_borrar);
DELETE FROM caregiver_documents WHERE caregiver_profile_id IN (SELECT id FROM cp_borrar);
DELETE FROM caregiver_profiles WHERE id IN (SELECT id FROM cp_borrar);
DELETE FROM patient_members WHERE patient_id IN (SELECT id FROM pa_borrar) OR user_id IN (SELECT id FROM u_borrar);
DELETE FROM patients WHERE id IN (SELECT id FROM pa_borrar);
DELETE FROM refresh_sessions WHERE user_id IN (SELECT id FROM u_borrar);
DELETE FROM users WHERE id IN (SELECT id FROM u_borrar);

-- Recalcula la valoración de las cuidadoras que se conservan (por si perdieron reseñas de cuentas borradas)
UPDATE caregiver_profiles p
   SET reviews_count = r.n, rating_avg = r.promedio
  FROM (SELECT caregiver_profile_id, count(*) AS n, round(avg(rating)::numeric, 2) AS promedio
          FROM caregiver_reviews GROUP BY caregiver_profile_id) r
 WHERE r.caregiver_profile_id = p.id;
UPDATE caregiver_profiles SET reviews_count = 0, rating_avg = NULL
 WHERE id NOT IN (SELECT caregiver_profile_id FROM caregiver_reviews);

-- Consola
CREATE TEMP TABLE mc_borrar ON COMMIT DROP AS
  SELECT id FROM marketplace_caregivers WHERE lower(email) NOT IN (SELECT email FROM conservar_cuentas);
DELETE FROM marketplace_caregiver_documents WHERE caregiver_id IN (SELECT id FROM mc_borrar);
DELETE FROM marketplace_caregiver_points_log WHERE caregiver_id IN (SELECT id FROM mc_borrar);
DELETE FROM marketplace_caregiver_reviews WHERE caregiver_id IN (SELECT id FROM mc_borrar);
DELETE FROM marketplace_caregivers WHERE id IN (SELECT id FROM mc_borrar);

-- Resumen de lo que queda (si no cuadra, no hagas COMMIT)
SELECT 'usuarios' AS tabla, count(*) AS quedan FROM users
UNION ALL SELECT 'familiares', count(*) FROM patients
UNION ALL SELECT 'perfiles de cuidadoras (sitio)', count(*) FROM caregiver_profiles
UNION ALL SELECT 'cuidadoras en la Consola', count(*) FROM marketplace_caregivers
UNION ALL SELECT 'conversaciones', count(*) FROM chat_conversations
UNION ALL SELECT 'solicitudes de contratación', count(*) FROM hire_requests
UNION ALL SELECT 'trabajos', count(*) FROM caregiver_engagements;

ROLLBACK;  -- ← cámbialo por COMMIT; cuando estés conforme con el resumen
