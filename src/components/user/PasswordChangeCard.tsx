import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { KeyRound, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { ReauthDialog } from '@/components/auth/ReauthDialog';

const MIN_PASSWORD_LENGTH = 12;

export function PasswordChangeCard() {
  const { updatePassword } = useAuth();
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [verified, setVerified] = useState(false);
  const [showReauth, setShowReauth] = useState(false);

  const passwordsMatch = newPassword === confirmPassword;
  const meetsMinLength = newPassword.length >= MIN_PASSWORD_LENGTH;
  const canSubmit = newPassword && confirmPassword && passwordsMatch && meetsMinLength && !submitting;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    const { error } = await updatePassword(newPassword);
    setSubmitting(false);

    if (error) {
      toast.error('Password update failed', { description: error.message });
    } else {
      toast.success('Password updated successfully');
      setNewPassword('');
      setConfirmPassword('');
      setVerified(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <KeyRound className="h-4 w-4" />
          Change Password
        </CardTitle>
        <CardDescription>
          Update your account password
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!verified ? (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              For security, you must verify your identity before changing your password.
            </p>
            <Button size="sm" onClick={() => setShowReauth(true)}>
              Verify Identity
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4 max-w-sm">
            <div className="space-y-2">
              <Label htmlFor="new-password">New Password</Label>
              <Input
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                minLength={MIN_PASSWORD_LENGTH}
                placeholder="Minimum 12 characters"
                autoComplete="new-password"
                aria-describedby={newPassword && !meetsMinLength ? 'new-password-error' : undefined}
              />
              {newPassword && !meetsMinLength && (
                <p id="new-password-error" className="text-xs text-destructive" role="alert">
                  Password must be at least {MIN_PASSWORD_LENGTH} characters
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirm-password">Confirm Password</Label>
              <Input
                id="confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter new password"
                autoComplete="new-password"
                aria-describedby={confirmPassword && !passwordsMatch ? 'confirm-password-error' : undefined}
              />
              {confirmPassword && !passwordsMatch && (
                <p id="confirm-password-error" className="text-xs text-destructive" role="alert">
                  Passwords do not match
                </p>
              )}
            </div>

            <Button type="submit" size="sm" disabled={!canSubmit}>
              {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Update Password
            </Button>
          </form>
        )}
      </CardContent>

      <ReauthDialog
        open={showReauth}
        onOpenChange={setShowReauth}
        title="Verify Identity"
        description="Enter the verification code sent to your email to unlock password change."
        onVerified={() => setVerified(true)}
      />
    </Card>
  );
}
