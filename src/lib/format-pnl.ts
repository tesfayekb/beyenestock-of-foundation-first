/**
 * Shared P&L formatter for the trading console.
 *
 * Returns { text, className } so the caller can render with explicit
 * sign and color. Uses theme tokens (text-success / text-destructive /
 * text-muted-foreground) rather than raw Tailwind palette colors so the
 * output matches the rest of the console (Badges, status indicators,
 * trend arrows) and respects dark-mode theming.
 *
 *   positive → `+$1,234.56`   text-success    font-medium
 *   negative → `-$1,234.56`   text-destructive font-medium
 *   zero     → `$0.00`         text-muted-foreground
 *   null     → `—`             text-muted-foreground
 *
 * Usage:
 *   const pnl = formatPnl(position.current_pnl);
 *   <span className={pnl.className}>{pnl.text}</span>
 */
export function formatPnl(value: number | null | undefined): {
    text: string;
    className: string;
} {
    if (value === null || value === undefined) {
        return { text: '—', className: 'text-muted-foreground' };
    }
    const formatted = Math.abs(value).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
    if (value > 0) {
        return {
            text: `+$${formatted}`,
            className: 'text-success font-medium',
        };
    }
    if (value < 0) {
        return {
            text: `-$${formatted}`,
            className: 'text-destructive font-medium',
        };
    }
    return { text: `$${formatted}`, className: 'text-muted-foreground' };
}
