-- MIG-034: Add email column to profiles + sync trigger from auth.users
-- Purpose: Eliminate auth.admin.listUsers() from search path (DW-021)

-- Step 1: Add email column (idempotent)
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS email TEXT;

-- Step 2: Create btree index for search (ILIKE will seq-scan but on small datasets this is fine)
CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles (email);

-- Step 3: Sync trigger — copies email from auth.users on insert/update
CREATE OR REPLACE FUNCTION public.sync_profile_email()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  UPDATE public.profiles
  SET email = NEW.email, updated_at = now()
  WHERE id = NEW.id;
  RETURN NEW;
END;
$$;

-- Drop existing trigger if re-running
DROP TRIGGER IF EXISTS sync_email_to_profile ON auth.users;

-- Attach trigger to auth.users
CREATE TRIGGER sync_email_to_profile
AFTER INSERT OR UPDATE OF email ON auth.users
FOR EACH ROW
EXECUTE FUNCTION public.sync_profile_email();

-- Step 4: Backfill existing users
UPDATE public.profiles p
SET email = u.email, updated_at = now()
FROM auth.users u
WHERE p.id = u.id AND p.email IS DISTINCT FROM u.email;