-- Fix handle_new_user
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
  INSERT INTO public.user_roles (user_id, role)
  VALUES (NEW.id, 'user');
  RETURN NEW;
END;
$$;

-- Fix handle_new_user_role
CREATE OR REPLACE FUNCTION public.handle_new_user_role()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  _user_role_id UUID;
BEGIN
  SELECT id INTO _user_role_id FROM public.roles WHERE key = 'user';
  IF _user_role_id IS NOT NULL THEN
    INSERT INTO public.user_roles (user_id, role_id)
    VALUES (NEW.id, _user_role_id)
    ON CONFLICT (user_id, role_id) DO NOTHING;
  END IF;
  RETURN NEW;
END;
$$;

-- Fix update_updated_at
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- Fix update_updated_at_column
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

-- Fix prevent_immutable_role_delete
CREATE OR REPLACE FUNCTION public.prevent_immutable_role_delete()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
  IF OLD.is_immutable = true THEN
    RAISE EXCEPTION 'Cannot delete immutable role: %', OLD.key;
  END IF;
  RETURN OLD;
END;
$$;

-- Fix prevent_immutable_role_update
CREATE OR REPLACE FUNCTION public.prevent_immutable_role_update()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public
AS $$
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
  END IF;
  RETURN NEW;
END;
$$;

-- Fix prevent_last_superadmin_delete
CREATE OR REPLACE FUNCTION public.prevent_last_superadmin_delete()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
  superadmin_role_id UUID;
  remaining_count INTEGER;
BEGIN
  SELECT id INTO superadmin_role_id FROM public.roles WHERE key = 'superadmin';
  IF OLD.role_id = superadmin_role_id THEN
    SELECT COUNT(*) INTO remaining_count
    FROM public.user_roles
    WHERE role_id = superadmin_role_id
      AND id != OLD.id;
    IF remaining_count < 1 THEN
      RAISE EXCEPTION 'Cannot remove the last superadmin assignment';
    END IF;
  END IF;
  RETURN OLD;
END;
$$;