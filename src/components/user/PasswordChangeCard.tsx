import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { isRecentlyAuthenticated } from '@/lib/auth-guards';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { KeyRound, AlertTriangle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const MIN_PASSWORD_LENGTH = 12;

export function PasswordChangeCard() {
  const { user, updatePassword } = useAuth();
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const needsReauth = !isRecentlyAuthenticated(user);
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
        {needsReauth ? (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              For security, you must sign in again before changing your password.
              Please sign out and sign back in, then return here.
            </AlertDescription>
          </Alert>
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
              />
              {newPassword && !meetsMinLength && (
                <p className="text-xs text-destructive">
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
              />
              {confirmPassword && !passwordsMatch && (
                <p className="text-xs text-destructive">
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
    </Card>
  );
}
