import { Link } from 'react-router-dom';
import { FileQuestion } from 'lucide-react';
import { Button } from '@/components/ui/button';

/**
 * In-shell 404 page. Renders inside the DashboardLayout so sidebar and header
 * remain visible — unlike the global NotFound which breaks out of the shell.
 * Uses relative navigation to parent route (always a safe in-app destination).
 */
export function DashboardNotFound() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 py-16">
      <div className="rounded-full bg-muted p-4">
        <FileQuestion className="h-8 w-8 text-muted-foreground" />
      </div>
      <div className="text-center">
        <h2 className="text-xl font-semibold">Page not found</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>
      </div>
      <Button variant="outline" asChild>
        <Link to=".." relative="path">Go back</Link>
      </Button>
    </div>
  );
}
