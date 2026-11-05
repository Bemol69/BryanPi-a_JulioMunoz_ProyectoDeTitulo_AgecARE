-- Fotos de las cuidadoras en la Consola.
--
-- La Consola ahora muestra la foto de cada cuidadora. Las cuidadoras nuevas la envían solas al subirla;
-- este script completa las que ya existían (cuentas reales con foto y cuentas de demostración).
-- Como las dos aplicaciones comparten la misma base de datos en Supabase, se hace en un solo paso.
-- Se puede ejecutar más de una vez: solo completa las fotos que estén vacías.
--
-- Cómo usarlo: Supabase → SQL Editor → pegar todo → Run.

-- 1) La columna nueva de la Consola (la API la agrega sola al arrancar; esta línea la crea antes si hace falta).
ALTER TABLE marketplace_caregivers ADD COLUMN IF NOT EXISTS photo_url VARCHAR(500);

-- 2) Fotos de demostración (ilustraciones alojadas en el sitio público) para las cuentas de ejemplo sin foto.
UPDATE users SET avatar_url = 'https://bryan-pi-a-julio-munoz-proyecto-de-sigma.vercel.app/demo/avatars/maria.svg'
 WHERE lower(email) = 'maria@cuidado.cl' AND avatar_url IS NULL;
UPDATE users SET avatar_url = 'https://bryan-pi-a-julio-munoz-proyecto-de-sigma.vercel.app/demo/avatars/javiera.svg'
 WHERE lower(email) = 'javiera@cuidado.cl' AND avatar_url IS NULL;
UPDATE users SET avatar_url = 'https://bryan-pi-a-julio-munoz-proyecto-de-sigma.vercel.app/demo/avatars/rocio.svg'
 WHERE lower(email) = 'rocio@cuidado.cl' AND avatar_url IS NULL;
UPDATE users SET avatar_url = 'https://bryan-pi-a-julio-munoz-proyecto-de-sigma.vercel.app/demo/avatars/fernanda.svg'
 WHERE lower(email) = 'fernanda@cuidado.cl' AND avatar_url IS NULL;

-- 3) Copia a la Consola la foto que cada cuidadora tiene en el sitio (cuentas reales y de demostración).
UPDATE marketplace_caregivers m
   SET photo_url = u.avatar_url
  FROM users u
 WHERE lower(u.email) = lower(m.email)
   AND u.avatar_url IS NOT NULL
   AND m.photo_url IS NULL;
