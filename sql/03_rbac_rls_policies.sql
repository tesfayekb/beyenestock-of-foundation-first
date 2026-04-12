-- =============================================================================
-- Phase 2 RBAC RLS Policies
-- APPLY ORDER: Run AFTER 02_rbac_security_helpers.sql
-- =============================================================================

CREATE POLICY "roles_select_policy"
  ON public.roles FOR SELECT TO authenticated
  USING (public.has_permission(auth.uid(), 'roles.view'));

CREATE POLICY "permissions_select_policy"
  ON public.permissions FOR SELECT TO authenticated
  USING (public.has_permission(auth.uid(), 'permissions.view'));

CREATE POLICY "user_roles_select_own"
  ON public.user_roles FOR SELECT TO authenticated
  USING (
    user_id = auth.uid()
    OR public.has_permission(auth.uid(), 'roles.view')
  );

CREATE POLICY "role_permissions_select_policy"
  ON public.role_permissions FOR SELECT TO authenticated
  USING (public.has_permission(auth.uid(), 'roles.view'));

CREATE POLICY "audit_logs_select_policy"
  ON public.audit_logs FOR SELECT TO authenticated
  USING (public.has_permission(auth.uid(), 'audit.view'));
