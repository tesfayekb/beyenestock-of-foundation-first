-- Inline is_superadmin check into has_permission for single-query execution
CREATE OR REPLACE FUNCTION public.has_permission(_user_id uuid, _permission_key text)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $$
  SELECT CASE
    WHEN _user_id IS NULL OR _permission_key IS NULL THEN false
    ELSE EXISTS (
      SELECT 1
      FROM public.user_roles ur
      JOIN public.roles r ON r.id = ur.role_id
      WHERE ur.user_id = _user_id
        AND (
          r.key = 'superadmin'
          OR EXISTS (
            SELECT 1
            FROM public.role_permissions rp
            JOIN public.permissions p ON p.id = rp.permission_id
            WHERE rp.role_id = ur.role_id
              AND p.key = _permission_key
          )
        )
    )
  END
$$;

-- Index for default user list sort order
CREATE INDEX IF NOT EXISTS idx_profiles_created_at
  ON public.profiles (created_at DESC);
