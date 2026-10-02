-- AgeCare · Seguridad en Supabase
-- Ejecutar UNA VEZ en Supabase → SQL Editor, después de crear las tablas (migración + seed).
--
-- Supabase expone el esquema "public" por su API REST pública. Las APIs de AgeCare se conectan
-- directo a Postgres (rol postgres, que ignora RLS), así que activamos RLS en todas las tablas
-- SIN políticas: nadie puede leerlas por la API REST con la llave anónima.
do $$
declare t record;
begin
  for t in select tablename from pg_tables where schemaname = 'public' loop
    execute format('alter table public.%I enable row level security', t.tablename);
  end loop;
end $$;
