-- Issue 1: invitations.invited_by + accepted_by FKs
ALTER TABLE public.invitations
  ADD CONSTRAINT invitations_invited_by_fkey
  FOREIGN KEY (invited_by) REFERENCES auth.users(id) ON DELETE RESTRICT;

ALTER TABLE public.invitations
  ADD CONSTRAINT invitations_accepted_by_fkey
  FOREIGN KEY (accepted_by) REFERENCES auth.users(id) ON DELETE SET NULL;

-- Issue 2: system_config.updated_by FK
ALTER TABLE public.system_config
  ADD CONSTRAINT system_config_updated_by_fkey
  FOREIGN KEY (updated_by) REFERENCES auth.users(id) ON DELETE SET NULL;