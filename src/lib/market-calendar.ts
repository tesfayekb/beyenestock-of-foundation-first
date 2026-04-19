/**
 * Market calendar utility — frontend mirror of backend/market_calendar.py.
 *
 * Keeps UI awareness of trading-day vs holiday vs early-close in sync
 * with the backend so the Health page does not raise false alarms
 * outside US stock-market hours.
 *
 * Update annually when CBOE publishes the next year's schedule.
 */

// 2026 market holidays — full close (YYYY-MM-DD strings for cheap comparison).
const MARKET_HOLIDAYS_2026 = new Set<string>([
    '2026-01-01', // New Year's Day
    '2026-01-19', // MLK Day
    '2026-02-16', // Presidents' Day
    '2026-04-03', // Good Friday
    '2026-05-25', // Memorial Day
    '2026-06-19', // Juneteenth
    '2026-07-03', // Independence Day (observed)
    '2026-09-07', // Labor Day
    '2026-11-26', // Thanksgiving
    '2026-12-25', // Christmas
]);

// 2026 early close days — market closes at 1:00 PM ET.
const EARLY_CLOSE_2026 = new Set<string>([
    '2026-07-02', // Day before Independence Day
    '2026-11-27', // Black Friday
    '2026-12-24', // Christmas Eve
]);

const MARKET_OPEN_MINUTES = 9 * 60 + 30; // 09:30 ET
const NORMAL_CLOSE_MINUTES = 16 * 60;    // 16:00 ET
const EARLY_CLOSE_MINUTES = 13 * 60;     // 13:00 ET

/**
 * Convert any Date into a synthetic Date whose `getFullYear/Month/Date/
 * Day/Hours/Minutes` fields read out the wall-clock time in America/
 * New_York. The resulting Date's underlying UTC instant is meaningless
 * — only call the local accessors on it.
 */
function toETWallClock(now: Date = new Date()): Date {
    // toLocaleString('en-US', { timeZone: 'America/New_York' }) renders
    // the ET wall clock as a string; re-parsing that string with
    // `new Date(...)` treats it as the user's local time, which means
    // the local accessors then return the ET components we want.
    return new Date(
        now.toLocaleString('en-US', { timeZone: 'America/New_York' }),
    );
}

function toDateString(d: Date): string {
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
}

export function isMarketDay(now: Date = new Date()): boolean {
    const et = toETWallClock(now);
    const dow = et.getDay(); // 0=Sun, 6=Sat
    if (dow === 0 || dow === 6) return false;
    return !MARKET_HOLIDAYS_2026.has(toDateString(et));
}

/** Hour at which the market closes today (16 normal, 13 early close). */
export function getMarketCloseHour(now: Date = new Date()): number {
    const et = toETWallClock(now);
    return EARLY_CLOSE_2026.has(toDateString(et)) ? 13 : 16;
}

/**
 * True only if RIGHT NOW the US stock market is open.
 *
 * Honors:
 *   - weekends (Sat/Sun) → false
 *   - holidays           → false
 *   - pre-market (< 09:30 ET) → false
 *   - post-close (≥ 16:00 ET, or ≥ 13:00 ET on early-close days) → false
 */
export function isMarketOpen(now: Date = new Date()): boolean {
    if (!isMarketDay(now)) return false;
    const et = toETWallClock(now);
    const minutes = et.getHours() * 60 + et.getMinutes();
    const closeMinutes = EARLY_CLOSE_2026.has(toDateString(et))
        ? EARLY_CLOSE_MINUTES
        : NORMAL_CLOSE_MINUTES;
    return minutes >= MARKET_OPEN_MINUTES && minutes < closeMinutes;
}

/**
 * Returns a one-word label for the current market state.
 * Prefers Weekend/Holiday over Closed when applicable so the UI
 * can explain why the market isn't open.
 */
export function getMarketStatusLabel(now: Date = new Date()): string {
    if (!isMarketDay(now)) {
        const et = toETWallClock(now);
        const dow = et.getDay();
        if (dow === 0 || dow === 6) return 'Weekend';
        return 'Holiday';
    }
    return isMarketOpen(now) ? 'Open' : 'Closed';
}
