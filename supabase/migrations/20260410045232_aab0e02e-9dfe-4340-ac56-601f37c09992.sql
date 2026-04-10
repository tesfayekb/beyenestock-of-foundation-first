-- ACT-021: Corrective migration for handle_new_user()
-- Migration 20260410041727 contained a broken INSERT INTO user_roles (user_id, role)
-- using a non-existent 'role' column (correct column is 'role_id').
-- Migration 20260410043317 partially fixed this but the fix was incomplete in that migration file.
-- This migration is the authoritative corrective record.
--
-- The correct behavior:
--   handle_new_user() → creates profile ONLY
--   handle_new_user_role() → assigns default 'user' role via role_id lookup
--
-- The DB is already in the correct state (20260410043317 applied the profile-only version),
-- but this migration serves as the formal corrective record per governance rules.

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, display_name, email_verified)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1)),
    COALESCE((NEW.raw_user_meta_data->>'email_verified')::boolean, FALSE)
  );
  RETURN NEW;
END;
$$;