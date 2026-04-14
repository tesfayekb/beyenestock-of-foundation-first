
-- Fix: Don't accept invitation on user creation. Accept it when email is confirmed.

-- 1. Update handle_new_user_role to SKIP invitation acceptance on INSERT
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
  SELECT id INTO _user_role_id FROM public.roles WHERE key = 'user';
  IF _user_role_id IS NOT NULL THEN
    INSERT INTO public.user_roles (user_id, role_id)
    VALUES (NEW.id, _user_role_id)
    ON CONFLICT (user_id, role_id) DO NOTHING;
  END IF;

  PERFORM pg_advisory_xact_lock(42);

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

-- 2. Create trigger function that accepts invitation only when user confirms email
CREATE OR REPLACE FUNCTION public.accept_invitation_on_confirm()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
DECLARE
  _invitation_id UUID;
  _invited_role_id UUID;
  _user_role_id UUID;
BEGIN
  IF OLD.email_confirmed_at IS NOT NULL THEN
    RETURN NEW;
  END IF;
  IF NEW.email_confirmed_at IS NULL THEN
    RETURN NEW;
  END IF;

  _invitation_id := (NEW.raw_user_meta_data->>'invitation_id')::UUID;
  IF _invitation_id IS NULL THEN
    RETURN NEW;
  END IF;

  SELECT role_id INTO _invited_role_id
  FROM public.invitations
  WHERE id = _invitation_id AND status = 'pending';

  IF NOT FOUND THEN
    RETURN NEW;
  END IF;

  SELECT id INTO _user_role_id FROM public.roles WHERE key = 'user';

  IF _invited_role_id IS NOT NULL AND _invited_role_id IS DISTINCT FROM _user_role_id THEN
    INSERT INTO public.user_roles (user_id, role_id)
    VALUES (NEW.id, _invited_role_id)
    ON CONFLICT (user_id, role_id) DO NOTHING;
  END IF;

  UPDATE public.invitations
  SET status = 'accepted', accepted_at = now(), accepted_by = NEW.id
  WHERE id = _invitation_id AND status = 'pending';

  INSERT INTO public.audit_logs (action, actor_id, target_type, target_id, metadata)
  VALUES (
    'user.invitation_accepted', NEW.id, 'invitations', _invitation_id,
    jsonb_build_object('email', NEW.email, 'invited_role_id', _invited_role_id)
  );

  RETURN NEW;
END;
$function$;

-- 3. Create UPDATE trigger on auth.users for email confirmation
CREATE TRIGGER on_user_email_confirmed
  AFTER UPDATE ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.accept_invitation_on_confirm();
