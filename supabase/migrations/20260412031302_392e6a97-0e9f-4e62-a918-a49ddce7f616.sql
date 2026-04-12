-- Seed roles.edit permission
INSERT INTO public.permissions (key, description)
VALUES ('roles.edit', 'Allows editing role name and description for non-immutable roles')
ON CONFLICT (key) DO NOTHING;

-- Assign roles.edit to the admin role
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM public.roles r, public.permissions p
WHERE r.key = 'admin' AND p.key = 'roles.edit'
ON CONFLICT (role_id, permission_id) DO NOTHING;
