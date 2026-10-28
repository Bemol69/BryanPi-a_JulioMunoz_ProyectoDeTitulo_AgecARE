# Diccionario de datos

Generado desde los modelos del proyecto. Cubre las **38 tablas** de las dos aplicaciones (25 de la Consola de Administración y 13 del sitio público). Las columnas con `PK` son clave primaria y las `FK` apuntan a la tabla indicada.

## Consola de Administración (`backend`)

| Tabla | Para qué sirve | Columnas |
|---|---|---|
| `admin_sessions` | Sesiones del staff (tokens de renovación guardados como hash). | 7 |
| `admin_users` | Cuentas del equipo de Wellq Co. que usan la Consola, con su rol. | 13 |
| `audit_log` | Registro de auditoría: qué hizo cada persona del staff y cuándo. | 12 |
| `content_items` | Contenidos de la curación de contenido (artículos y similares). | 14 |
| `feature_usage_window` | Uso de cada funcionalidad por rol y ventana de días. | 6 |
| `features` | Catálogo de funcionalidades de AgeCare. | 6 |
| `legal_versions` | Versiones de los textos legales (términos y privacidad). | 13 |
| `marketplace_caregiver_documents` | Documentos de la cuidadora (cédula, antecedentes, certificados) y su revisión. | 12 |
| `marketplace_caregiver_points_log` | Historial de puntos de fidelización otorgados a cada cuidadora. | 9 |
| `marketplace_caregiver_reviews` | Reseñas de las familias sobre las cuidadoras. | 7 |
| `marketplace_caregivers` | Perfiles de cuidadoras que revisa el staff (estado de aprobación, zona, especialidades). | 17 |
| `marketplace_products` | Artículos de apoyo del catálogo del marketplace. | 9 |
| `metrics_daily_users` | Usuarios, altas, bajas e ingresos por día (uso comercial). | 8 |
| `metrics_hourly_users` | Usuarios por hora del día actual. | 5 |
| `metrics_plan_snapshot` | Usuarios, precio e ingresos por plan. | 8 |
| `moderation_queue` | Cola de contenido reportado que el staff debe moderar. | 16 |
| `ops_component_state` | Último estado de cada componente del sistema (estado operativo). | 7 |
| `ops_critical_process_state` | Estado de los procesos críticos y sus tiempos de respuesta. | 7 |
| `ops_incidents` | Incidentes operativos registrados. | 13 |
| `ops_latency_window` | Latencias agregadas por ventana de tiempo. | 7 |
| `role_activity_window` | Actividad de los usuarios por perfil y ventana de días. | 9 |
| `role_weekly_active` | Usuarios activos por perfil y semana. | 5 |
| `support_ticket_replies` | Respuestas a los tickets de soporte. | 8 |
| `support_tickets` | Tickets de soporte de los usuarios. | 21 |
| `system_settings` | Configuración del sistema que se puede modificar desde la Consola. | 8 |

### `admin_sessions`

Sesiones del staff (tokens de renovación guardados como hash).

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `admin_id` | UUID | no | FK → `admin_users.id` |
| `refresh_hash` | VARCHAR(64) | no |  |
| `expires_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `revoked_at` | TIMESTAMP WITH TIME ZONE | sí |  |
| `rotated_to` | UUID | sí |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `admin_users`

Cuentas del equipo de Wellq Co. que usan la Consola, con su rol.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `full_name` | VARCHAR(120) | no |  |
| `email` | VARCHAR(254) | no |  |
| `password_hash` | VARCHAR(255) | sí |  |
| `role` | VARCHAR(20) | no |  |
| `is_active` | BOOLEAN | no |  |
| `mfa_enabled` | BOOLEAN | no |  |
| `mfa_secret` | VARCHAR(64) | sí |  |
| `failed_attempts` | INTEGER | no |  |
| `locked_until` | TIMESTAMP WITH TIME ZONE | sí |  |
| `invitation_expires_at` | TIMESTAMP WITH TIME ZONE | sí |  |
| `last_login_at` | TIMESTAMP WITH TIME ZONE | sí |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `audit_log`

Registro de auditoría: qué hizo cada persona del staff y cuándo.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `actor_id` | UUID | sí |  |
| `actor_name` | VARCHAR(120) | sí |  |
| `actor_role` | VARCHAR(20) | sí |  |
| `action` | VARCHAR(60) | no |  |
| `entity_type` | VARCHAR(40) | sí |  |
| `entity_id` | UUID | sí |  |
| `before` | JSONB | sí |  |
| `after` | JSONB | sí |  |
| `ip` | VARCHAR(45) | sí |  |
| `user_agent` | VARCHAR(300) | sí |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `content_items`

Contenidos de la curación de contenido (artículos y similares).

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `type` | VARCHAR(10) | no |  |
| `title` | VARCHAR(160) | no |  |
| `body` | TEXT | no |  |
| `tags` | JSONB | no |  |
| `status` | VARCHAR(12) | no |  |
| `tts_ready` | BOOLEAN | no |  |
| `publish_at` | TIMESTAMP WITH TIME ZONE | sí |  |
| `published_at` | TIMESTAMP WITH TIME ZONE | sí |  |
| `deleted_at` | TIMESTAMP WITH TIME ZONE | sí |  |
| `created_by` | UUID | sí |  |
| `created_by_name` | VARCHAR(120) | sí |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `feature_usage_window`

Uso de cada funcionalidad por rol y ventana de días.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `days_window` | INTEGER | no |  |
| `feature_key` | VARCHAR(50) | no | FK → `features.feature_key` |
| `role` | VARCHAR(12) | no |  |
| `users` | INTEGER | no |  |
| `computed_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `features`

Catálogo de funcionalidades de AgeCare.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `feature_key` | VARCHAR(50) | no | PK |
| `name` | VARCHAR(120) | no |  |
| `applicable_roles` | JSONB | no |  |
| `expected_low` | BOOLEAN | no |  |
| `note` | VARCHAR(300) | sí |  |
| `sort_order` | INTEGER | no |  |

### `legal_versions`

Versiones de los textos legales (términos y privacidad).

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `doc_type` | VARCHAR(10) | no |  |
| `semver` | VARCHAR(10) | no |  |
| `content_md` | TEXT | no |  |
| `changelog` | TEXT | no |  |
| `effective_date` | DATE | no |  |
| `requires_reacceptance` | BOOLEAN | no |  |
| `status` | VARCHAR(10) | no |  |
| `published_at` | TIMESTAMP WITH TIME ZONE | sí |  |
| `created_by` | UUID | sí |  |
| `created_by_name` | VARCHAR(120) | sí |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `marketplace_caregiver_documents`

Documentos de la cuidadora (cédula, antecedentes, certificados) y su revisión.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `caregiver_id` | UUID | no | FK → `marketplace_caregivers.id` |
| `doc_type` | VARCHAR(20) | no |  |
| `file_url` | VARCHAR(500) | no |  |
| `original_filename` | VARCHAR(255) | no |  |
| `status` | VARCHAR(16) | no |  |
| `pending_file_url` | VARCHAR(500) | sí |  |
| `pending_filename` | VARCHAR(255) | sí |  |
| `review_note` | TEXT | sí |  |
| `reviewed_at` | TIMESTAMP WITH TIME ZONE | sí |  |
| `reviewed_by_name` | VARCHAR(120) | sí |  |
| `uploaded_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `marketplace_caregiver_points_log`

Historial de puntos de fidelización otorgados a cada cuidadora.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `caregiver_id` | UUID | no | FK → `marketplace_caregivers.id` |
| `points` | INTEGER | no |  |
| `reason` | VARCHAR(20) | no |  |
| `note` | VARCHAR(300) | sí |  |
| `review_id` | UUID | sí |  |
| `awarded_by` | UUID | sí |  |
| `awarded_by_name` | VARCHAR(120) | sí |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `marketplace_caregiver_reviews`

Reseñas de las familias sobre las cuidadoras.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `caregiver_id` | UUID | no | FK → `marketplace_caregivers.id` |
| `family_name` | VARCHAR(120) | no |  |
| `rating` | INTEGER | no |  |
| `comment` | TEXT | sí |  |
| `job_reference` | VARCHAR(120) | sí |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `marketplace_caregivers`

Perfiles de cuidadoras que revisa el staff (estado de aprobación, zona, especialidades).

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `name` | VARCHAR(120) | no |  |
| `email` | VARCHAR(254) | no |  |
| `zone` | VARCHAR(80) | no |  |
| `specialties` | JSONB | no |  |
| `languages` | JSONB | no |  |
| `certifications_count` | INTEGER | no |  |
| `certifications_verified` | BOOLEAN | no |  |
| `rating_avg` | FLOAT | sí |  |
| `reviews_count` | INTEGER | no |  |
| `is_engaged` | BOOLEAN | no |  |
| `status` | VARCHAR(12) | no |  |
| `status_reason` | TEXT | sí |  |
| `internal_note` | TEXT | sí |  |
| `submitted_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `reviewed_by` | UUID | sí |  |
| `reviewed_by_name` | VARCHAR(120) | sí |  |

### `marketplace_products`

Artículos de apoyo del catálogo del marketplace.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `name` | VARCHAR(160) | no |  |
| `category` | VARCHAR(60) | no |  |
| `vendor` | VARCHAR(120) | no |  |
| `price_clp` | INTEGER | sí |  |
| `external_url` | VARCHAR(500) | no |  |
| `image_url` | VARCHAR(500) | sí |  |
| `status` | VARCHAR(12) | no |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `metrics_daily_users`

Usuarios, altas, bajas e ingresos por día (uso comercial).

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `day` | DATE | no | PK |
| `signups` | INTEGER | no |  |
| `cancellations` | INTEGER | no |  |
| `downloads` | INTEGER | no |  |
| `active_users_eod` | INTEGER | no |  |
| `paying_users_eod` | INTEGER | no |  |
| `mrr_clp_eod` | INTEGER | no |  |
| `computed_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `metrics_hourly_users`

Usuarios por hora del día actual.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `ts_hour` | TIMESTAMP WITH TIME ZONE | no |  |
| `signups` | INTEGER | no |  |
| `cancellations` | INTEGER | no |  |
| `computed_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `metrics_plan_snapshot`

Usuarios, precio e ingresos por plan.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `as_of` | DATE | no |  |
| `plan_code` | VARCHAR(12) | no |  |
| `users` | INTEGER | no |  |
| `price_clp` | INTEGER | sí |  |
| `mrr_clp` | INTEGER | no |  |
| `monthly_churn` | FLOAT | no |  |
| `computed_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `moderation_queue`

Cola de contenido reportado que el staff debe moderar.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `type` | VARCHAR(20) | no |  |
| `content` | JSONB | no |  |
| `author_user_id` | UUID | sí |  |
| `author_name` | VARCHAR(120) | no |  |
| `author_role` | VARCHAR(12) | sí |  |
| `reported_by` | JSONB | sí |  |
| `report_reason` | VARCHAR(300) | sí |  |
| `is_safety` | BOOLEAN | no |  |
| `status` | VARCHAR(10) | no |  |
| `reject_reason_code` | VARCHAR(15) | sí |  |
| `decision_note` | TEXT | sí |  |
| `decided_by` | UUID | sí |  |
| `decided_by_name` | VARCHAR(120) | sí |  |
| `decided_at` | TIMESTAMP WITH TIME ZONE | sí |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `ops_component_state`

Último estado de cada componente del sistema (estado operativo).

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `key` | VARCHAR(30) | no | PK |
| `status` | VARCHAR(15) | no |  |
| `uptime_30d` | FLOAT | no |  |
| `latency_p50_ms` | INTEGER | sí |  |
| `latency_p95_ms` | INTEGER | sí |  |
| `note` | VARCHAR(200) | sí |  |
| `checked_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `ops_critical_process_state`

Estado de los procesos críticos y sus tiempos de respuesta.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `key` | VARCHAR(40) | no | PK |
| `name` | VARCHAR(120) | no |  |
| `chain` | VARCHAR(300) | no |  |
| `p95_seconds` | FLOAT | no |  |
| `success_24h` | FLOAT | no |  |
| `status` | VARCHAR(15) | no |  |
| `computed_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `ops_incidents`

Incidentes operativos registrados.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `title` | VARCHAR(160) | no |  |
| `component_key` | VARCHAR(30) | sí |  |
| `severity` | VARCHAR(15) | no |  |
| `status` | VARCHAR(15) | no |  |
| `description` | TEXT | no |  |
| `resolution` | TEXT | sí |  |
| `is_maintenance` | BOOLEAN | no |  |
| `started_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `resolved_at` | TIMESTAMP WITH TIME ZONE | sí |  |
| `created_by` | UUID | sí |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `ops_latency_window`

Latencias agregadas por ventana de tiempo.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `window` | VARCHAR(4) | no |  |
| `component_key` | VARCHAR(30) | no |  |
| `p50_ms` | INTEGER | no |  |
| `p95_ms` | INTEGER | no |  |
| `sample_count` | INTEGER | no |  |
| `computed_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `role_activity_window`

Actividad de los usuarios por perfil y ventana de días.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `days_window` | INTEGER | no |  |
| `role` | VARCHAR(12) | no |  |
| `active_users` | INTEGER | no |  |
| `growth_8w` | FLOAT | no |  |
| `sessions_per_week` | FLOAT | no |  |
| `avg_session_seconds` | INTEGER | no |  |
| `retention_30d` | FLOAT | no |  |
| `computed_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `role_weekly_active`

Usuarios activos por perfil y semana.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `week_start` | DATE | no |  |
| `role` | VARCHAR(12) | no |  |
| `active_users` | INTEGER | no |  |
| `computed_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `support_ticket_replies`

Respuestas a los tickets de soporte.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `ticket_id` | UUID | no | FK → `support_tickets.id` |
| `author_type` | VARCHAR(10) | no |  |
| `author_id` | UUID | sí |  |
| `author_name` | VARCHAR(120) | no |  |
| `body` | TEXT | no |  |
| `internal` | BOOLEAN | no |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `support_tickets`

Tickets de soporte de los usuarios.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `number` | INTEGER | no |  |
| `subject` | VARCHAR(160) | no |  |
| `description` | TEXT | no |  |
| `requester_user_id` | UUID | sí |  |
| `requester_name` | VARCHAR(120) | no |  |
| `requester_email` | VARCHAR(254) | no |  |
| `requester_role` | VARCHAR(12) | sí |  |
| `requester_plan` | VARCHAR(12) | sí |  |
| `category` | VARCHAR(20) | no |  |
| `priority` | VARCHAR(10) | no |  |
| `status` | VARCHAR(15) | no |  |
| `channel` | VARCHAR(10) | no |  |
| `assigned_to` | UUID | sí | FK → `admin_users.id` |
| `first_response_at` | TIMESTAMP WITH TIME ZONE | sí |  |
| `resolved_at` | TIMESTAMP WITH TIME ZONE | sí |  |
| `csat_score` | INTEGER | sí |  |
| `csat_comment` | TEXT | sí |  |
| `requester_context` | JSONB | sí |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `system_settings`

Configuración del sistema que se puede modificar desde la Consola.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `key` | VARCHAR(80) | no | PK |
| `value` | JSONB | sí |  |
| `value_schema` | JSONB | no |  |
| `description` | VARCHAR(300) | no |  |
| `version` | INTEGER | no |  |
| `updated_by` | UUID | sí |  |
| `updated_by_name` | VARCHAR(120) | sí |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | sí |  |

## Sitio público (`backend-general`)

| Tabla | Para qué sirve | Columnas |
|---|---|---|
| `caregiver_documents` | Documentos de la cuidadora, su estado de revisión y los cambios pendientes. | 11 |
| `caregiver_engagements` | Trabajos activos o terminados entre una familia y una cuidadora. | 8 |
| `caregiver_profiles` | Perfil profesional de la cuidadora y su estado de aprobación. | 16 |
| `caregiver_reviews` | Reseñas que las familias dejan al terminar un trabajo. | 7 |
| `chat_conversations` | Conversaciones entre una familia y una cuidadora. | 5 |
| `chat_messages` | Mensajes del chat (se eliminan a los 7 días). | 5 |
| `contact_requests` | Mensajes de contacto de una familia a una cuidadora. | 5 |
| `hire_requests` | Solicitudes de contratación que la cuidadora acepta o rechaza. | 8 |
| `market_products` | Artículos de apoyo que se muestran a las familias. | 9 |
| `patient_members` | Qué usuario tiene acceso a qué adulto mayor y con qué rol. | 6 |
| `patients` | Adultos mayores registrados por las familias. | 10 |
| `refresh_sessions` | Sesiones del sitio público (tokens de renovación guardados como hash). | 7 |
| `users` | Cuentas del sitio público (familias y cuidadoras). | 11 |

### `caregiver_documents`

Documentos de la cuidadora, su estado de revisión y los cambios pendientes.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `caregiver_profile_id` | UUID | no | FK → `caregiver_profiles.id` |
| `doc_type` | VARCHAR(20) | no |  |
| `file_url` | VARCHAR(500) | no |  |
| `original_filename` | VARCHAR(255) | no |  |
| `status` | VARCHAR(16) | no |  |
| `pending_file_url` | VARCHAR(500) | sí |  |
| `pending_filename` | VARCHAR(255) | sí |  |
| `review_note` | TEXT | sí |  |
| `reviewed_at` | TIMESTAMP WITH TIME ZONE | sí |  |
| `uploaded_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `caregiver_engagements`

Trabajos activos o terminados entre una familia y una cuidadora.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `caregiver_profile_id` | UUID | no | FK → `caregiver_profiles.id` |
| `family_user_id` | UUID | no | FK → `users.id` |
| `patient_id` | UUID | sí | FK → `patients.id` |
| `status` | VARCHAR(10) | no |  |
| `started_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `ended_at` | TIMESTAMP WITH TIME ZONE | sí |  |
| `review_id` | UUID | sí |  |

### `caregiver_profiles`

Perfil profesional de la cuidadora y su estado de aprobación.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `user_id` | UUID | no | FK → `users.id` |
| `headline` | VARCHAR(160) | sí |  |
| `bio` | TEXT | sí |  |
| `years_experience` | INTEGER | sí |  |
| `specialties` | JSONB | no |  |
| `languages` | JSONB | no |  |
| `zones` | JSONB | no |  |
| `certifications` | JSONB | no |  |
| `rating_avg` | FLOAT | sí |  |
| `reviews_count` | INTEGER | no |  |
| `is_listed` | BOOLEAN | no |  |
| `is_featured` | BOOLEAN | no |  |
| `admin_status` | VARCHAR(12) | no |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `caregiver_reviews`

Reseñas que las familias dejan al terminar un trabajo.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `caregiver_profile_id` | UUID | no | FK → `caregiver_profiles.id` |
| `author_user_id` | UUID | no | FK → `users.id` |
| `author_name` | VARCHAR(120) | no |  |
| `rating` | INTEGER | no |  |
| `comment` | TEXT | sí |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `chat_conversations`

Conversaciones entre una familia y una cuidadora.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `caregiver_profile_id` | UUID | no | FK → `caregiver_profiles.id` |
| `family_user_id` | UUID | no | FK → `users.id` |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `last_message_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `chat_messages`

Mensajes del chat (se eliminan a los 7 días).

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `conversation_id` | UUID | no | FK → `chat_conversations.id` |
| `sender_user_id` | UUID | no | FK → `users.id` |
| `body` | VARCHAR(1000) | no |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `contact_requests`

Mensajes de contacto de una familia a una cuidadora.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `caregiver_profile_id` | UUID | no | FK → `caregiver_profiles.id` |
| `family_user_id` | UUID | no | FK → `users.id` |
| `message` | VARCHAR(500) | sí |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `hire_requests`

Solicitudes de contratación que la cuidadora acepta o rechaza.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `caregiver_profile_id` | UUID | no | FK → `caregiver_profiles.id` |
| `family_user_id` | UUID | no | FK → `users.id` |
| `patient_id` | UUID | sí | FK → `patients.id` |
| `message` | VARCHAR(500) | sí |  |
| `status` | VARCHAR(12) | no |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `responded_at` | TIMESTAMP WITH TIME ZONE | sí |  |

### `market_products`

Artículos de apoyo que se muestran a las familias.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `name` | VARCHAR(160) | no |  |
| `category` | VARCHAR(20) | no |  |
| `description` | TEXT | no |  |
| `thumbnail_url` | VARCHAR(500) | sí |  |
| `photos` | JSONB | no |  |
| `price_range` | VARCHAR(60) | no |  |
| `external_url` | VARCHAR(500) | sí |  |
| `contact_info` | VARCHAR(200) | sí |  |

### `patient_members`

Qué usuario tiene acceso a qué adulto mayor y con qué rol.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `patient_id` | UUID | no | FK → `patients.id` |
| `user_id` | UUID | no | FK → `users.id` |
| `role` | VARCHAR(12) | no |  |
| `is_owner` | BOOLEAN | no |  |
| `joined_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `patients`

Adultos mayores registrados por las familias.

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `full_name` | VARCHAR(120) | no |  |
| `birth_date` | DATE | no |  |
| `sex` | VARCHAR(10) | sí |  |
| `photo_url` | VARCHAR(500) | sí |  |
| `conditions` | JSONB | no |  |
| `medication_allergies` | JSONB | no |  |
| `food_allergies` | JSONB | no |  |
| `notes` | TEXT | sí |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `refresh_sessions`

Sesiones del sitio público (tokens de renovación guardados como hash).

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `user_id` | UUID | no | FK → `users.id` |
| `refresh_hash` | VARCHAR(64) | no |  |
| `expires_at` | TIMESTAMP WITH TIME ZONE | no |  |
| `revoked_at` | TIMESTAMP WITH TIME ZONE | sí |  |
| `rotated_to` | UUID | sí |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |

### `users`

Cuentas del sitio público (familias y cuidadoras).

| Columna | Tipo | ¿Acepta vacío? | Clave / relación |
|---|---|---|---|
| `id` | UUID | no | PK |
| `full_name` | VARCHAR(120) | no |  |
| `email` | VARCHAR(254) | no |  |
| `password_hash` | VARCHAR(255) | no |  |
| `phone` | VARCHAR(30) | sí |  |
| `avatar_url` | VARCHAR(500) | sí |  |
| `locale` | VARCHAR(5) | no |  |
| `account_type` | VARCHAR(12) | no |  |
| `failed_attempts` | INTEGER | no |  |
| `locked_until` | TIMESTAMP WITH TIME ZONE | sí |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | no |  |
