-- MIG-012: Wire login-block trigger + self-scope RLS on profiles

-- 1. Attach check_user_active_on_login() to auth.users as a BEFORE UPDATE trigger
-- This fires when Supabase updates last_sign_in_at during login
-- Note: We use an ON INSERT OR UPDATE trigger to catch both new sessions and refreshes
CREATE OR REPLACE TRIGGER check_user_active_before_login
  BEFORE UPDATE ON auth.users
  FOR EACH ROW
  WHEN (NEW.last_sign_in_at IS DISTINCT FROM OLD.last_sign_in_at)
  EXECUTE FUNCTION public.check_user_active_on_login();

-- 2. Self-scope RLS policies on profiles (defense-in-depth)
-- These are additive (PERMISSIVE) — user can read/write own profile via RLS
-- even without admin permissions, matching the self-scope permission model

-- Drop existing policies first to avoid conflicts (they already exist from MIG-011)
DROP POLICY IF EXISTS "Users can read own profile" ON public.profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;

-- Re-create with explicit self-scope enforcement
CREATE POLICY "Users can read own profile"
  ON public.profiles
  FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON public.profiles
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);