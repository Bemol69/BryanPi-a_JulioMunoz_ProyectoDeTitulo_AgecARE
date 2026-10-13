-- AgeCare · Migración 2026-10-12: solicitudes de contratación (la cuidadora acepta o rechaza).
-- Ejecutar en Supabase → SQL Editor del proyecto "agecare". Es idempotente (se puede correr más de una vez).
-- La API del sitio también crea esta tabla sola al arrancar; correrlo a mano la deja lista antes del deploy.

CREATE TABLE IF NOT EXISTS hire_requests (
    id                    UUID PRIMARY KEY,
    caregiver_profile_id  UUID NOT NULL REFERENCES caregiver_profiles(id),
    family_user_id        UUID NOT NULL REFERENCES users(id),
    patient_id            UUID REFERENCES patients(id),
    message               VARCHAR(500),
    status                VARCHAR(12) NOT NULL DEFAULT 'pending',
    created_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    responded_at          TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS ix_hire_requests_caregiver_profile_id ON hire_requests (caregiver_profile_id);
CREATE INDEX IF NOT EXISTS ix_hire_requests_family_user_id       ON hire_requests (family_user_id);
CREATE INDEX IF NOT EXISTS ix_hire_requests_status               ON hire_requests (status);

-- Seguridad: la tabla queda cerrada a la API pública de Supabase.
ALTER TABLE hire_requests ENABLE ROW LEVEL SECURITY;
