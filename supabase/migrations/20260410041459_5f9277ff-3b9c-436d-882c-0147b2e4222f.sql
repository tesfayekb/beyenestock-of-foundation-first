INSERT INTO public.user_roles (user_id, role_id)
SELECT '39977fdf-995a-41af-8be9-d89186131b1e', id FROM public.roles WHERE key = 'user'
ON CONFLICT (user_id, role_id) DO NOTHING;