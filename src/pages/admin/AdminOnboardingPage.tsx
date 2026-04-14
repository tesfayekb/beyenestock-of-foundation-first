/**
 * AdminOnboardingPage — Manages onboarding modes and invitations.
 *
 * Route: /admin/onboarding
 * Permission: users.invite (page-level gate in App.tsx)
 *
 * Sub-permissions:
 * - admin.config: onboarding mode switches (superadmin only)
 * - users.invite: send invitations (invite buttons)
 * - users.invite.manage: revoke/resend actions (table actions, gated in InvitationsTable)
 *
 * Owner: user-onboarding module
 */
import { useState } from 'react';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { OnboardingModeCard } from '@/components/admin/OnboardingModeCard';
import { InviteUserDialog } from '@/components/admin/InviteUserDialog';
import { BulkInviteDialog } from '@/components/admin/BulkInviteDialog';
import { InvitationsTable } from '@/components/admin/InvitationsTable';
import { RequirePermission } from '@/components/auth/RequirePermission';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { UserPlus, Users } from 'lucide-react';

export default function AdminOnboardingPage() {
  const [inviteOpen, setInviteOpen] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Invitations"
        subtitle="Manage user onboarding and send invitations"
        actions={
          <RequirePermission permission="users.invite" fallback={null}>
            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={() => setBulkOpen(true)}>
                <Users className="mr-2 h-4 w-4" />
                Bulk Invite
              </Button>
              <Button onClick={() => setInviteOpen(true)}>
                <UserPlus className="mr-2 h-4 w-4" />
                Invite User
              </Button>
            </div>
          </RequirePermission>
        }
      />

      {/* Onboarding mode — only visible to users with admin.config (superadmins) */}
      <RequirePermission permission="admin.config" fallback={null}>
        <OnboardingModeCard />
      </RequirePermission>

      <Separator />

      {/* Invitations table — visible to anyone with users.invite.
          Manage actions (revoke/resend) gated internally by users.invite.manage */}
      <InvitationsTable />

      <InviteUserDialog open={inviteOpen} onOpenChange={setInviteOpen} />
      <BulkInviteDialog open={bulkOpen} onOpenChange={setBulkOpen} />
    </div>
  );
}
