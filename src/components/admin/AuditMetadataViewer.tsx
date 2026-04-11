import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface AuditMetadataViewerProps {
  metadata: Record<string, unknown> | null;
}

/**
 * Expandable JSON viewer for audit log metadata.
 * Collapsed by default; shows a preview snippet when collapsed.
 */
export function AuditMetadataViewer({ metadata }: AuditMetadataViewerProps) {
  const [expanded, setExpanded] = useState(false);

  if (!metadata || Object.keys(metadata).length === 0) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }

  const preview = Object.keys(metadata).slice(0, 3).join(', ');
  const keyCount = Object.keys(metadata).length;

  return (
    <div className="max-w-md">
      <Button
        variant="ghost"
        size="sm"
        className="h-auto px-1 py-0.5 text-xs text-muted-foreground hover:text-foreground"
        onClick={(e) => {
          e.stopPropagation();
          setExpanded(!expanded);
        }}
      >
        {expanded ? (
          <ChevronDown className="mr-1 h-3 w-3" />
        ) : (
          <ChevronRight className="mr-1 h-3 w-3" />
        )}
        {expanded ? 'Collapse' : `{${preview}${keyCount > 3 ? ', …' : ''}}`}
      </Button>
      {expanded && (
        <pre className="mt-1 max-h-48 overflow-auto rounded border border-border bg-muted/50 p-2 text-xs font-mono text-foreground">
          {JSON.stringify(metadata, null, 2)}
        </pre>
      )}
    </div>
  );
}
