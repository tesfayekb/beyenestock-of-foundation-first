-- ============================================================
-- PLAN-INVITE-001 Phase 1: User Onboarding & Invitations
-- ============================================================

-- 1. system_config table
CREATE TABLE public.system_config (
  key         TEXT PRIMARY KEY,
  value       JSONB NOT NULL,
  description TEXT,
  updated_by  UUID,
  updated_at  TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.system_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can read system config"
  ON public.system_config FOR SELECT TO authenticated USING (true);

-- Seed default onboarding mode: both enabled
INSERT INTO public.system_config (key, value, description) VALUES
  ('onboarding_mode', '{"signup_enabled": true, "invite_enabled": true}',
   'Controls user onboarding pathways. At least one must be true at all times.');

-- 2. invitations table
CREATE TABLE public.invitations (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email           TEXT NOT NULL,
  token_hash      TEXT NOT NULL UNIQUE,
  role_id         UUID REFERENCES public.roles(id) ON DELETE SET NULL,
  invited_by      UUID NOT NULL,
  status          TEXT NOT NULL DEFAULT 'pending',
  expires_at      TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '72 hours'),
  accepted_at     TIMESTAMPTZ,
  accepted_by     UUID,
  created_at      TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.invitations ENABLE ROW LEVEL SECURITY;

-- No direct client access policies — all operations via edge functions

-- Indexes
CREATE UNIQUE INDEX idx_invitations_email_pending
  ON public.invitations(email) WHERE status = 'pending';
CREATE INDEX idx_invitations_token_hash ON public.invitations(token_hash);
CREATE INDEX idx_invitations_status ON public.invitations(status);
CREATE INDEX idx_invitations_expires_at ON public.invitations(expires_at);

-- 3. Validation trigger for invitation status (not CHECK constraint)
CREATE OR REPLACE FUNCTION public.validate_invitation_status()
  RETURNS trigger LANGUAGE plpgsql SET search_path TO 'public' AS $$
BEGIN
  IF NEW.status NOT IN ('pending', 'accepted', 'expired', 'revoked') THEN
    RAISE EXCEPTION 'Invalid invitation status: %. Must be pending, accepted, expired, or revoked.', NEW.status;
  END IF;
  RETURN NEW;
END; $$;

CREATE TRIGGER validate_invitation_status_trigger
  BEFORE INSERT OR UPDATE ON public.invitations
  FOR EACH ROW EXECUTE FUNCTION public.validate_invitation_status();

-- 4. Update handle_new_user_role to consume invitation_id from metadata
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
  _invitation_id UUID;
  _invited_role_id UUID;
BEGIN
  -- Always assign the base 'user' role
  SELECT id INTO _user_role_id FROM public.roles WHERE key = 'user';
  IF _user_role_id IS NOT NULL THEN
    INSERT INTO public.user_roles (user_id, role_id)
    VALUES (NEW.id, _user_role_id)
    ON CONFLICT (user_id, role_id) DO NOTHING;
  END IF;

  -- Check for invitation_id in user metadata (set by inviteUserByEmail)
  _invitation_id := (NEW.raw_user_meta_data->>'invitation_id')::UUID;

  IF _invitation_id IS NOT NULL THEN
    -- Look up the invitation and get the role to assign
    SELECT role_id INTO _invited_role_id
    FROM public.invitations
    WHERE id = _invitation_id
      AND status = 'pending';

    IF _invited_role_id IS NOT NULL AND _invited_role_id != _user_role_id THEN
      -- Assign the invited role
      INSERT INTO public.user_roles (user_id, role_id)
      VALUES (NEW.id, _invited_role_id)
      ON CONFLICT (user_id, role_id) DO NOTHING;
    END IF;

    -- Mark invitation as accepted (atomically with user creation)
    UPDATE public.invitations
    SET status = 'accepted',
        accepted_at = now(),
        accepted_by = NEW.id
    WHERE id = _invitation_id
      AND status = 'pending';

    -- Audit: invitation accepted
    INSERT INTO public.audit_logs (action, actor_id, target_type, target_id, metadata)
    VALUES (
      'user.invitation_accepted',
      NEW.id,
      'invitations',
      _invitation_id,
      jsonb_build_object(
        'email', NEW.email,
        'invited_role_id', _invited_role_id
      )
    );
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

      -- Audit: system event
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

-- 5. Seed new permissions: users.invite and users.invite.manage
INSERT INTO public.permissions (key, description) VALUES
  ('users.invite', 'Send individual or bulk user invitations'),
  ('users.invite.manage', 'View, revoke, and resend existing invitations')
ON CONFLICT (key) DO NOTHING;

-- 6. Assign new permissions to the admin role
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM public.roles r
CROSS JOIN public.permissions p
WHERE r.key = 'admin'
  AND p.key IN ('users.invite', 'users.invite.manage')
ON CONFLICT (role_id, permission_id) DO NOTHING;