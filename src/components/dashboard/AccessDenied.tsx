import { ShieldOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';

interface AccessDeniedProps {
  message?: string;
}

export function AccessDenied({
  message = "You don't have permission to access this page.",
}: AccessDeniedProps) {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="rounded-full bg-destructive/10 p-4 mb-4">
        <ShieldOff className="h-10 w-10 text-destructive" />
      </div>
      <h2 className="font-display text-xl font-bold">Access Denied</h2>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">{message}</p>
      <div className="mt-6 flex gap-2">
        <Button variant="outline" onClick={() => navigate(-1)}>
          Go Back
        </Button>
        <Button onClick={() => navigate('/')}>
          Home
        </Button>
      </div>
    </div>
  );
}
