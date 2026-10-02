-- AgeCare · Seguridad en Supabase
-- Ejecutar UNA VEZ en Supabase → SQL Editor, después de crear las tablas (migración + seed).
--
-- Supabase expone el esquema "public" por su API REST pública. Las APIs de AgeCare se conectan
-- directo a Postgres (rol postgres, que ignora RLS), así que activamos RLS en las tablas de AgeCare
-- SIN políticas: nadie puede leerlas por la API REST con la llave anónima.
-- Solo toca las tablas listadas abajo; no modifica otras tablas del proyecto.
do $$
declare t text;
begin
  foreach t in array array[
    'admin_users',
    'admin_sessions',
    'audit_log',
    'metrics_daily_users',
    'metrics_hourly_users',
    'metrics_plan_snapshot',
    'role_activity_window',
    'role_weekly_active',
    'features',
    'feature_usage_window',
    'ops_component_state',
    'ops_latency_window',
    'ops_critical_process_state',
    'ops_incidents',
    'support_tickets',
    'support_ticket_replies',
    'content_items',
    'marketplace_caregivers',
    'marketplace_caregiver_documents',
    'marketplace_caregiver_reviews',
    'marketplace_caregiver_points_log',
    'marketplace_products',
    'moderation_queue',
    'system_settings',
    'legal_versions',
    'users',
    'refresh_sessions',
    'patients',
    'patient_members',
    'caregiver_profiles',
    'caregiver_documents',
    'caregiver_reviews',
    'contact_requests',
    'caregiver_engagements',
    'market_products',
    'alembic_version'
  ] loop
    if to_regclass('public.' || quote_ident(t)) is not null then
      execute format('alter table public.%I enable row level security', t);
    end if;
  end loop;
end $$;
