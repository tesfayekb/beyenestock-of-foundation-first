-- Phase 1A: First-signup superadmin bootstrap with advisory lock + audit
CREATE OR REPLACE FUNCTION public.handle_new_user_role()
  RETURNS trigger
  LANGUAGE plpgsql
  SECURITY DEFINER
  SET search_path TO 'public'
AS $function$
DECLARE
  _user_role_id UUID;
  _superadmin_role_id UUID;
  _superadmin_count INTEGER;
BEGIN
  -- Always assign the base 'user' role
  SELECT id INTO _user_role_id FROM public.roles WHERE key = 'user';
  IF _user_role_id IS NOT NULL THEN
    INSERT INTO public.user_roles (user_id, role_id)
    VALUES (NEW.id, _user_role_id)
    ON CONFLICT (user_id, role_id) DO NOTHING;
  END IF;

  -- Serialise concurrent first-signup checks
  PERFORM pg_advisory_xact_lock(42);

  -- If no superadmin exists yet, this is the founding user
  SELECT COUNT(*) INTO _superadmin_count
    FROM public.user_roles ur
    JOIN public.roles r ON r.id = ur.role_id
    WHERE r.key = 'superadmin';

  IF _superadmin_count = 0 THEN
    SELECT id INTO _superadmin_role_id FROM public.roles WHERE key = 'superadmin';
    IF _superadmin_role_id IS NOT NULL THEN
      INSERT INTO public.user_roles (user_id, role_id)
      VALUES (NEW.id, _superadmin_role_id)
      ON CONFLICT (user_id, role_id) DO NOTHING;

      -- Audit: system event (ip_address and user_agent are NULL — acceptable for trigger)
      INSERT INTO public.audit_logs (action, actor_id, target_type, target_id, metadata)
      VALUES (
        'rbac.first_superadmin_bootstrapped',
        NEW.id,
        'user_roles',
        NEW.id,
        jsonb_build_object(
          'role_key', 'superadmin',
          'bootstrap_reason', 'First user signup — no existing superadmin'
        )
      );
    END IF;
  END IF;

  RETURN NEW;
END;
$function$;

-- Phase 1B: Add is_permission_locked column to roles
ALTER TABLE public.roles
  ADD COLUMN IF NOT EXISTS is_permission_locked boolean NOT NULL DEFAULT false;

-- Set is_permission_locked explicitly for all base roles
UPDATE public.roles SET is_permission_locked = true WHERE key = 'user';
UPDATE public.roles SET is_permission_locked = false WHERE key = 'admin';
UPDATE public.roles SET is_permission_locked = false WHERE key = 'superadmin';

-- Update immutability trigger to also protect is_permission_locked on immutable roles
CREATE OR REPLACE FUNCTION public.prevent_immutable_role_update()
  RETURNS trigger
  LANGUAGE plpgsql
  SET search_path TO 'public'
AS $function$
BEGIN
  IF OLD.is_immutable = true THEN
    IF NEW.key IS DISTINCT FROM OLD.key THEN
      RAISE EXCEPTION 'Cannot modify key of immutable role: %', OLD.key;
    END IF;
    IF NEW.is_base IS DISTINCT FROM OLD.is_base THEN
      RAISE EXCEPTION 'Cannot modify is_base of immutable role: %', OLD.key;
    END IF;
    IF NEW.is_immutable IS DISTINCT FROM OLD.is_immutable THEN
      RAISE EXCEPTION 'Cannot modify is_immutable of immutable role: %', OLD.key;
    END IF;
    IF NEW.is_permission_locked IS DISTINCT FROM OLD.is_permission_locked THEN
      RAISE EXCEPTION 'Cannot modify is_permission_locked of immutable role: %', OLD.key;
    END IF;
  END IF;
  RETURN NEW;
END;
$function$;

-- Phase 4A (seed): Remove roles.create and roles.delete from admin role
DELETE FROM public.role_permissions
WHERE role_id = (SELECT id FROM public.roles WHERE key = 'admin')
  AND permission_id IN (
    SELECT id FROM public.permissions WHERE key IN ('roles.create', 'roles.delete')
  );