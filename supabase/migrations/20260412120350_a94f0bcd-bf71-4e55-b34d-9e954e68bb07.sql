-- Drop dependent index first
DROP INDEX IF EXISTS public.idx_profiles_display_name_trgm;

-- Move pg_trgm to extensions schema
DROP EXTENSION IF EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA extensions;

-- Recreate the trigram index using extensions-qualified operator class
CREATE INDEX IF NOT EXISTS idx_profiles_display_name_trgm
  ON public.profiles USING GIN (display_name extensions.gin_trgm_ops);
