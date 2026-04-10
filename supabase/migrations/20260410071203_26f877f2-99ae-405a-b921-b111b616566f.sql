-- Stage 3C: User Management Schema & Lifecycle
-- MIG-011: Add status column, admin RLS, seed user management permissions

-- 1. Add status column to profiles
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active';

-- 2. Add constraint for valid status values (using a validation trigger per project convention)
CREATE OR REPLACE FUNCTION public.validate_profile_status()
RETURNS trigger
LANGUAGE plpgsql
SET search_path TO 'public'
AS $$
BEGIN
  IF NEW.status NOT IN ('active', 'deactivated') THEN
    RAISE EXCEPTION 'Invalid profile status: %. Must be active or deactivated.', NEW.status;
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_profile_status
  BEFORE INSERT OR UPDATE ON public.profiles
  FOR EACH ROW
  EXECUTE FUNCTION public.validate_profile_status();

-- 3. Add admin RLS policies on profiles
CREATE POLICY "Admins can view all profiles"
  ON public.profiles
  FOR SELECT
  TO authenticated
  USING (public.has_permission(auth.uid(), 'users.view_all'));

CREATE POLICY "Admins can update any profile"
  ON public.profiles
  FOR UPDATE
  TO authenticated
  USING (public.has_permission(auth.uid(), 'users.edit_any'))
  WITH CHECK (public.has_permission(auth.uid(), 'users.edit_any'));

-- 4. Seed user management permissions
INSERT INTO public.permissions (key, description) VALUES
  ('users.view_self', 'View own profile data'),
  ('users.edit_self', 'Edit own profile data'),
  ('users.view_all', 'View all user profiles (admin)'),
  ('users.edit_any', 'Edit any user profile (admin)'),
  ('users.deactivate', 'Deactivate user accounts (admin)'),
  ('users.reactivate', 'Reactivate deactivated accounts (admin)')
ON CONFLICT (key) DO NOTHING;

-- 5. Assign self-scope permissions to 'user' role
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM public.roles r
CROSS JOIN public.permissions p
WHERE r.key = 'user'
  AND p.key IN ('users.view_self', 'users.edit_self')
ON CONFLICT DO NOTHING;

-- 6. Assign all user management permissions to 'admin' role
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM public.roles r
CROSS JOIN public.permissions p
WHERE r.key = 'admin'
  AND p.key IN ('users.view_self', 'users.edit_self', 'users.view_all', 'users.edit_any', 'users.deactivate', 'users.reactivate')
ON CONFLICT DO NOTHING;

-- 7. Create index on profiles.status for efficient filtering
CREATE INDEX IF NOT EXISTS idx_profiles_status ON public.profiles (status);

-- 8. Login-block function: prevent deactivated users from authenticating
-- This is a defense-in-depth hook; primary enforcement is in edge function code (Option A)
CREATE OR REPLACE FUNCTION public.check_user_active_on_login()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $$
DECLARE
  _status text;
BEGIN
  SELECT status INTO _status
  FROM public.profiles
  WHERE id = NEW.id;

  IF _status = 'deactivated' THEN
    RAISE EXCEPTION 'Account is deactivated. Please contact support.';
  END IF;

  RETURN NEW;
END;
$$;