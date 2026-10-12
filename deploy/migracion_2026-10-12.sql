-- AgeCare · Migración 2026-10-12: revisión de perfiles y documentos, reseñas por trabajo y chat.
-- Ejecutar en Supabase → SQL Editor del proyecto "agecare". Es idempotente (se puede correr más de una vez).
-- Las APIs también aplican estos cambios solas al arrancar; correrlo a mano deja todo listo antes del deploy.

-- ============ Sitio público ============
-- Estado de revisión del perfil (lo decide el staff en la Consola): solo "approved" aparece en el marketplace.
ALTER TABLE caregiver_profiles    ADD COLUMN IF NOT EXISTS admin_status      VARCHAR(12) NOT NULL DEFAULT 'pending';

-- Documentos: estado de revisión y cambio pendiente de aprobación.
ALTER TABLE caregiver_documents   ADD COLUMN IF NOT EXISTS status            VARCHAR(16) NOT NULL DEFAULT 'pending';
ALTER TABLE caregiver_documents   ADD COLUMN IF NOT EXISTS pending_file_url  VARCHAR(500);
ALTER TABLE caregiver_documents   ADD COLUMN IF NOT EXISTS pending_filename  VARCHAR(255);
ALTER TABLE caregiver_documents   ADD COLUMN IF NOT EXISTS review_note       TEXT;
ALTER TABLE caregiver_documents   ADD COLUMN IF NOT EXISTS reviewed_at       TIMESTAMP WITH TIME ZONE;

-- Reseñas solo al terminar un trabajo: cada trabajo se puede reseñar una vez.
ALTER TABLE caregiver_engagements ADD COLUMN IF NOT EXISTS review_id         UUID;

-- Chat dentro de la aplicación (los mensajes se borran solos a los 7 días).
CREATE TABLE IF NOT EXISTS chat_conversations (
    id                    UUID PRIMARY KEY,
    caregiver_profile_id  UUID NOT NULL REFERENCES caregiver_profiles(id),
    family_user_id        UUID NOT NULL REFERENCES users(id),
    created_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    last_message_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_chat_pair UNIQUE (caregiver_profile_id, family_user_id)
);
CREATE INDEX IF NOT EXISTS ix_chat_conversations_caregiver_profile_id ON chat_conversations (caregiver_profile_id);
CREATE INDEX IF NOT EXISTS ix_chat_conversations_family_user_id       ON chat_conversations (family_user_id);
CREATE INDEX IF NOT EXISTS ix_chat_conversations_last_message_at      ON chat_conversations (last_message_at);

CREATE TABLE IF NOT EXISTS chat_messages (
    id               UUID PRIMARY KEY,
    conversation_id  UUID NOT NULL REFERENCES chat_conversations(id),
    sender_user_id   UUID NOT NULL REFERENCES users(id),
    body             VARCHAR(1000) NOT NULL,
    created_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_chat_messages_conversation_id ON chat_messages (conversation_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_created_at      ON chat_messages (created_at);

-- Seguridad: las tablas nuevas quedan cerradas a la API pública de Supabase.
ALTER TABLE chat_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages      ENABLE ROW LEVEL SECURITY;

-- Las cuidadoras de demostración que la Consola ya tiene aprobadas siguen visibles.
-- (Fernanda queda pendiente: aparece de nuevo cuando el staff apruebe sus documentos y su perfil.)
UPDATE caregiver_profiles SET admin_status = 'approved'
WHERE admin_status = 'pending'
  AND user_id IN (SELECT id FROM users WHERE lower(email) IN
      ('maria@cuidado.cl', 'javiera@cuidado.cl', 'rocio@cuidado.cl'));

-- ============ Consola de administración ============
ALTER TABLE marketplace_caregiver_documents ADD COLUMN IF NOT EXISTS status            VARCHAR(16) NOT NULL DEFAULT 'pending';
ALTER TABLE marketplace_caregiver_documents ADD COLUMN IF NOT EXISTS pending_file_url  VARCHAR(500);
ALTER TABLE marketplace_caregiver_documents ADD COLUMN IF NOT EXISTS pending_filename  VARCHAR(255);
ALTER TABLE marketplace_caregiver_documents ADD COLUMN IF NOT EXISTS review_note       TEXT;
ALTER TABLE marketplace_caregiver_documents ADD COLUMN IF NOT EXISTS reviewed_at       TIMESTAMP WITH TIME ZONE;
ALTER TABLE marketplace_caregiver_documents ADD COLUMN IF NOT EXISTS reviewed_by_name  VARCHAR(120);
