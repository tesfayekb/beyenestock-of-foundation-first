import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { EmptyState } from './EmptyState';
import { ReactNode } from 'react';

export interface DataTableColumn<T> {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  data: T[];
  /** Total count for server-side pagination */
  total?: number;
  page?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
  onRowClick?: (row: T) => void;
  emptyTitle?: string;
  emptyDescription?: string;
}

export function DataTable<T>({
  columns,
  data,
  total,
  page = 1,
  pageSize = 50,
  onPageChange,
  onRowClick,
  emptyTitle = 'No data',
  emptyDescription = 'No records found.',
}: DataTableProps<T>) {
  const totalPages = total != null ? Math.ceil(total / pageSize) : 1;
  const showPagination = total != null && totalPages > 1;

  if (data.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <div className="rounded-lg border border-border">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/50 hover:bg-muted/50">
            {columns.map((col) => (
              <TableHead
                key={col.key}
                className={`text-xs font-medium uppercase tracking-wider text-muted-foreground ${col.className ?? ''}`}
              >
                {col.header}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((row, index) => (
            <TableRow
              key={index}
              className={onRowClick ? 'cursor-pointer hover:bg-muted/50' : 'hover:bg-muted/50'}
              onClick={() => onRowClick?.(row)}
            >
              {columns.map((col) => (
                <TableCell key={col.key} className={`px-4 py-3 ${col.className ?? ''}`}>
                  {col.cell(row)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {showPagination && (
        <div className="flex items-center justify-between border-t px-4 py-3">
          <p className="text-xs text-muted-foreground">
            {((page - 1) * pageSize) + 1}–{Math.min(page * pageSize, total!)} of {total}
          </p>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              disabled={page <= 1}
              onClick={() => onPageChange?.(page - 1)}
              aria-label="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              disabled={page >= totalPages}
              onClick={() => onPageChange?.(page + 1)}
              aria-label="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
