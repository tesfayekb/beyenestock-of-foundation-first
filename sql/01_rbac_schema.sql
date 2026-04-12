-- =============================================================================
-- Phase 2 RBAC Schema Migration
-- Creates: roles, permissions, user_roles, role_permissions, audit_logs
-- Includes: DB-level immutability triggers, last-superadmin protection
--
-- APPLY ORDER: Run this file FIRST, then _02_helpers, _03_rls, _04_seed
-- =============================================================================

-- ===================== TABLES =====================

CREATE TABLE public.roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  is_base BOOLEAN NOT NULL DEFAULT false,
  is_immutable BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.permissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key TEXT UNIQUE NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.user_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role_id UUID NOT NULL REFERENCES public.roles(id) ON DELETE CASCADE,
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  assigned_by UUID REFERENCES auth.users(id),
  UNIQUE (user_id, role_id)
);

CREATE TABLE public.role_permissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  role_id UUID NOT NULL REFERENCES public.roles(id) ON DELETE CASCADE,
  permission_id UUID NOT NULL REFERENCES public.permissions(id) ON DELETE CASCADE,
  UNIQUE (role_id, permission_id)
);

CREATE TABLE public.audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id UUID REFERENCES auth.users(id),
  action TEXT NOT NULL,
  target_type TEXT,
  target_id UUID,
  metadata JSONB DEFAULT '{}'::jsonb,
  ip_address INET,
  user_agent TEXT,
  correlation_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===================== INDEXES =====================

CREATE INDEX idx_user_roles_user_id ON public.user_roles(user_id);
CREATE INDEX idx_user_roles_role_id ON public.user_roles(role_id);
CREATE INDEX idx_role_permissions_role_id ON public.role_permissions(role_id);
CREATE INDEX idx_role_permissions_permission_id ON public.role_permissions(permission_id);
CREATE INDEX idx_audit_logs_actor_id ON public.audit_logs(actor_id);
CREATE INDEX idx_audit_logs_action ON public.audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON public.audit_logs(created_at);
CREATE INDEX idx_audit_logs_target_id ON public.audit_logs(target_id);
CREATE INDEX idx_audit_logs_correlation_id ON public.audit_logs(correlation_id) WHERE correlation_id IS NOT NULL;

-- ===================== ENABLE RLS =====================

ALTER TABLE public.roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.role_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- ===================== UPDATED_AT TRIGGER =====================

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER trigger_roles_updated_at
  BEFORE UPDATE ON public.roles
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

-- ===================== IMMUTABILITY TRIGGERS =====================

CREATE OR REPLACE FUNCTION public.prevent_immutable_role_delete()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF OLD.is_immutable = true THEN
    RAISE EXCEPTION 'Cannot delete immutable role: %', OLD.key;
  END IF;
  RETURN OLD;
END;
$$;

CREATE TRIGGER trigger_prevent_immutable_role_delete
  BEFORE DELETE ON public.roles
  FOR EACH ROW
  EXECUTE FUNCTION public.prevent_immutable_role_delete();

CREATE OR REPLACE FUNCTION public.prevent_immutable_role_update()
RETURNS TRIGGER
LANGUAGE plpgsql
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

CREATE TRIGGER trigger_prevent_immutable_role_update
  BEFORE UPDATE ON public.roles
  FOR EACH ROW
  EXECUTE FUNCTION public.prevent_immutable_role_update();

CREATE OR REPLACE FUNCTION public.prevent_last_superadmin_delete()
RETURNS TRIGGER
LANGUAGE plpgsql
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

CREATE TRIGGER trigger_prevent_last_superadmin_delete
  BEFORE DELETE ON public.user_roles
  FOR EACH ROW
  EXECUTE FUNCTION public.prevent_last_superadmin_delete();
