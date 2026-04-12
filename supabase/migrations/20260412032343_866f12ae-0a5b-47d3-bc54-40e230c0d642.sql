-- Seed permissions.view
INSERT INTO public.permissions (key, description)
VALUES ('permissions.view', 'Allows viewing the permissions catalog independently of role management')
ON CONFLICT (key) DO NOTHING;

-- Assign permissions.view to admin
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM public.roles r, public.permissions p
WHERE r.key = 'admin' AND p.key = 'permissions.view'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Remove permissions.assign from admin (superadmin-only)
DELETE FROM public.role_permissions
WHERE role_id = (SELECT id FROM public.roles WHERE key = 'admin')
  AND permission_id = (SELECT id FROM public.permissions WHERE key = 'permissions.assign');

-- Remove permissions.revoke from admin (superadmin-only)
DELETE FROM public.role_permissions
WHERE role_id = (SELECT id FROM public.roles WHERE key = 'admin')
  AND permission_id = (SELECT id FROM public.permissions WHERE key = 'permissions.revoke');
