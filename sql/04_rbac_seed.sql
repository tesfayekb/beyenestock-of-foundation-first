-- =============================================================================
-- Phase 2 RBAC Seed Data
-- APPLY ORDER: Run AFTER 03_rbac_rls_policies.sql
-- =============================================================================

-- ===================== BASE ROLES =====================

INSERT INTO public.roles (key, name, description, is_base, is_immutable) VALUES
  ('superadmin', 'Super Administrator', 'Full access to all current and future permissions via logical inheritance', true, true),
  ('admin', 'Administrator', 'Administrative access — provisioned as a seed role during initial setup', true, true),
  ('user', 'User', 'Default role with baseline self-scope access', true, true);

-- ===================== PERMISSIONS =====================

INSERT INTO public.permissions (key, description) VALUES
  ('roles.assign', 'Allows assigning roles to users within governance boundaries'),
  ('roles.revoke', 'Allows revoking roles from users'),
  ('roles.view', 'Allows viewing role assignments and role definitions'),
  ('roles.create', 'Allows creating new dynamic roles within the RBAC system'),
  ('roles.delete', 'Allows deleting dynamic roles'),
  ('roles.edit', 'Allows editing role name and description for non-immutable roles'),
  ('permissions.assign', 'Allows assigning permissions to roles via privileged server-side RPCs'),
  ('permissions.revoke', 'Allows revoking permissions from roles via privileged server-side RPCs'),
  ('permissions.view', 'Allows viewing the permissions catalog independently of role management'),
  ('users.view_all', 'Allows viewing all user profiles and account data'),
  ('users.edit_any', 'Allows editing any user profile data'),
  ('users.deactivate', 'Allows deactivating user accounts'),
  ('users.reactivate', 'Allows reactivating deactivated user accounts'),
  ('users.view_self', 'Allows a user to view their own profile data'),
  ('users.edit_self', 'Allows a user to edit their own profile data'),
  ('profile.self_manage', 'Allows a user to manage their own profile and settings'),
  ('mfa.self_manage', 'Allows a user to manage their own MFA settings'),
  ('session.self_manage', 'Allows a user to view and revoke their own active sessions'),
  ('admin.access', 'Gates access to the entire admin panel'),
  ('admin.config', 'Allows modifying governed system configuration via admin panel'),
  ('audit.view', 'Allows viewing audit log entries in the admin panel'),
  ('audit.export', 'Allows exporting audit log data'),
  ('monitoring.view', 'Allows viewing health dashboards and system status'),
  ('monitoring.configure', 'Allows configuring alert thresholds and monitoring parameters'),
  ('jobs.view', 'Allows viewing job status, history, and queue state'),
  ('jobs.trigger', 'Allows manually triggering job execution'),
  ('jobs.pause', 'Allows pausing scheduled job execution'),
  ('jobs.resume', 'Allows resuming paused job execution'),
  ('jobs.retry', 'Allows manually retrying failed jobs'),
  ('jobs.deadletter.manage', 'Allows managing dead-lettered jobs'),
  ('jobs.emergency', 'Allows activating the job kill switch');

-- ===================== ROLE-PERMISSION MAPPINGS =====================

-- admin: all permissions EXCEPT jobs.emergency, permissions.assign, permissions.revoke
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM public.roles r, public.permissions p
WHERE r.key = 'admin'
  AND p.key NOT IN ('jobs.emergency', 'permissions.assign', 'permissions.revoke');

-- user: self-scope permissions only
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM public.roles r, public.permissions p
WHERE r.key = 'user'
  AND p.key IN ('users.view_self','users.edit_self','profile.self_manage','mfa.self_manage','session.self_manage');

-- ===================== AUTO-ASSIGN TRIGGER =====================

CREATE OR REPLACE FUNCTION public.handle_new_user_role()
RETURNS TRIGGER
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

CREATE TRIGGER on_auth_user_created_assign_role
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user_role();
