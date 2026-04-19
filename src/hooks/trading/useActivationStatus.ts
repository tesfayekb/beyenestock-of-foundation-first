/**
 * useActivationStatus — fetches full activation state for DASH-A.
 *
 * Backs the Phase Activation Dashboard at /trading/activation.
 * Polls every 60 seconds so threshold transitions and new alerts
 * surface without a manual refresh.
 *
 * CSP-fix: queries Supabase directly (Lovable CSP blocks the Railway
 * API). The four payload fields are derived as follows:
 *   closed_trade_count → trading_positions count
 *   flags              → trading_feature_flags rows
 *   ab_gate            → ab_session_comparison + closed-trade count
 *   recent_alerts      → system_alerts last 50 unacknowledged
 */
import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';

const ACCOUNT_NOTIONAL = 100_000;
const TRADING_DAYS_PER_YEAR = 252;

export interface FeatureDefinition {
    key: string;
    label: string;
    description: string;
    category:
        | 'always_on'
        | 'signal'
        | 'strategy'
        | 'agent'
        | 'model'
        | 'platform';
    /** Trades required before this feature is safe to enable. */
    activationThreshold: number | null;
    thresholdType: 'trades' | 'days' | 'manual' | 'command' | null;
    /** True = system flips it on automatically; false = operator decides. */
    autoEnable: boolean;
    builtStatus: 'live' | 'dormant' | 'not_built';
}

// Single source of truth for the feature registry. Keep this list in
// sync with FLAG_DEFINITIONS in useFeatureFlags.ts when adding new
// strategy/agent flags. The page imports ALL_FEATURES — never
// duplicate this array elsewhere.
export const ALL_FEATURES: FeatureDefinition[] = [
    // ── Always-on core engine ─────────────────────────────────────────
    {
        key: 'core:iron_condor',
        label: 'Iron Condor',
        category: 'always_on',
        description:
            'Default strategy — always active, no flag required.',
        activationThreshold: null,
        thresholdType: null,
        autoEnable: true,
        builtStatus: 'live',
    },
    {
        key: 'core:kelly_sizing',
        label: 'Kelly Sizing',
        category: 'always_on',
        description:
            'Auto-activates when 20+ closed trades exist.',
        activationThreshold: 20,
        thresholdType: 'trades',
        autoEnable: true,
        builtStatus: 'live',
    },
    {
        key: 'core:loop1_feedback',
        label: 'Loop 1 Feedback (Claude)',
        category: 'always_on',
        description:
            'Claude learns from trade outcomes. Auto-activates at 10 trades.',
        activationThreshold: 10,
        thresholdType: 'trades',
        autoEnable: true,
        builtStatus: 'live',
    },

    // ── Signal enhancements (default ON when built) ───────────────────
    {
        key: 'signal:vix_term_filter:enabled',
        label: 'VIX Term Structure Filter',
        category: 'signal',
        description:
            'Reduces size or skips when the VIX term structure inverts (VIX9D/VIX > 1.10).',
        activationThreshold: null,
        thresholdType: null,
        autoEnable: false,
        builtStatus: 'live',
    },
    {
        key: 'signal:entry_time_gate:enabled',
        label: 'Time-of-Day Entry Gate',
        category: 'signal',
        description:
            'Tightens floor to 9:45 AM ET; 25% size reduction during 9:45-10:00 AM opening volatility window.',
        activationThreshold: null,
        thresholdType: null,
        autoEnable: false,
        builtStatus: 'live',
    },
    {
        key: 'signal:gex_directional_bias:enabled',
        label: 'GEX Directional Bias',
        category: 'signal',
        description:
            'Reduces condor size when GEX is strongly negative (trending); slight boost when strongly positive (mean-reverting).',
        activationThreshold: null,
        thresholdType: null,
        autoEnable: false,
        builtStatus: 'live',
    },
    {
        key: 'signal:market_breadth:enabled',
        label: 'Market Breadth Filter',
        category: 'signal',
        description:
            'Reduces condor size when VIX z-score is elevated (broad market anxiety); slight boost when below recent norm.',
        activationThreshold: null,
        thresholdType: null,
        autoEnable: false,
        builtStatus: 'live',
    },
    {
        key: 'signal:earnings_proximity:enabled',
        label: 'Earnings Proximity Guard',
        category: 'signal',
        description:
            'Cuts short-gamma size 25% on days when a major SPX-mover reports earnings (reads economic calendar).',
        activationThreshold: null,
        thresholdType: null,
        autoEnable: false,
        builtStatus: 'live',
    },
    {
        key: 'signal:iv_rank_filter:enabled',
        label: 'IV Rank Entry Filter',
        category: 'signal',
        description:
            'Skips trade when premium is very thin; reduces size on thin premium; slight boost on relatively rich premium.',
        activationThreshold: null,
        thresholdType: null,
        autoEnable: false,
        builtStatus: 'live',
    },

    // ── Strategies (manual enable after threshold) ────────────────────
    {
        key: 'strategy:iron_butterfly:enabled',
        label: 'Iron Butterfly',
        category: 'strategy',
        description:
            'Fires on gamma pin days — SPX within 0.3% of GEX wall.',
        activationThreshold: 5,
        thresholdType: 'trades',
        autoEnable: false,
        builtStatus: 'dormant',
    },
    {
        key: 'strategy:long_straddle:enabled',
        label: 'Long Straddle',
        category: 'strategy',
        description:
            'Pre-catalyst (FOMC/CPI/NFP). Exits 30 min before announcement.',
        activationThreshold: 20,
        thresholdType: 'trades',
        autoEnable: false,
        builtStatus: 'dormant',
    },
    {
        key: 'strategy:calendar_spread:enabled',
        label: 'Calendar Spread',
        category: 'strategy',
        description:
            'Post-catalyst IV crush. Sell 0DTE ATM / buy next-Friday ATM.',
        activationThreshold: 20,
        thresholdType: 'trades',
        autoEnable: false,
        builtStatus: 'dormant',
    },
    {
        key: 'strategy:ai_hint_override:enabled',
        label: 'AI Strategy Override',
        category: 'strategy',
        description:
            'AI confidence ≥ 65% overrides regime-based strategy selection.',
        activationThreshold: 40,
        thresholdType: 'trades',
        autoEnable: false,
        builtStatus: 'dormant',
    },
    {
        key: 'strategy:earnings_straddle:enabled',
        label: 'Earnings Volatility Straddle',
        category: 'strategy',
        description:
            'Phase 5A — buys ATM straddles on NVDA/AAPL/META/TSLA/AMZN/GOOGL 2-3 trading days before earnings. Isolated alpha stream in backend_earnings/.',
        activationThreshold: null,
        thresholdType: 'manual',
        autoEnable: false,
        builtStatus: 'live',
    },

    // ── AI agents ─────────────────────────────────────────────────────
    {
        key: 'agents:ai_synthesis:enabled',
        label: 'AI Synthesis (Claude)',
        category: 'agent',
        description:
            'Claude produces a structured trade recommendation each morning.',
        activationThreshold: null,
        thresholdType: 'manual',
        autoEnable: false,
        builtStatus: 'dormant',
    },
    {
        key: 'agents:flow_agent:enabled',
        label: 'Flow Agent',
        category: 'agent',
        description:
            'Unusual Whales + Polygon P/C ratio options flow intelligence.',
        activationThreshold: 20,
        thresholdType: 'trades',
        autoEnable: false,
        builtStatus: 'dormant',
    },
    {
        key: 'agents:sentiment_agent:enabled',
        label: 'Sentiment Agent',
        category: 'agent',
        description:
            'NewsAPI headlines + Fear/Greed + overnight gap scoring.',
        activationThreshold: 20,
        thresholdType: 'trades',
        autoEnable: false,
        builtStatus: 'dormant',
    },

    // ── Learning models ───────────────────────────────────────────────
    {
        key: 'feedback:counterfactual:enabled',
        label: 'Counterfactual Tracking',
        category: 'model',
        description:
            'Learns from no-trade days — were they correct skips?',
        activationThreshold: 30,
        thresholdType: 'trades',
        autoEnable: true,
        builtStatus: 'not_built',
    },
    {
        key: 'model:meta_label:enabled',
        label: 'Meta-Label Model (Loop 2)',
        category: 'model',
        description:
            'LightGBM filters low-quality setups. Run training script first.',
        activationThreshold: 100,
        thresholdType: 'command',
        autoEnable: false,
        builtStatus: 'not_built',
    },
    {
        key: 'model:signal_calibration:enabled',
        label: 'Signal Calibration (Loop 3)',
        category: 'model',
        description:
            'Dynamic signal weighting based on 200-trade accuracy history.',
        activationThreshold: 200,
        thresholdType: 'trades',
        autoEnable: true,
        builtStatus: 'not_built',
    },
];

export interface ActivationStatus {
    closed_trade_count: number;
    flags: Record<string, boolean>;
    ab_gate: {
        built: boolean;
        days_elapsed: number | null;
        days_required: number;
        trades_count: number;
        trades_required: number;
        portfolio_b_lead_pct: number | null;
        gate_passed: boolean;
    };
    recent_alerts: Array<{
        fired_at: string;
        level: string;
        event: string;
        detail: string;
        acknowledged: boolean;
    }>;
}

interface FlagRow {
    flag_key: string;
    enabled: boolean;
}

interface AbDailyRow {
    a_synthetic_pnl: number | null;
    b_session_pnl: number | null;
    session_date: string;
}

interface AlertRow {
    fired_at: string;
    level: string;
    event: string;
    detail: string | null;
    acknowledged: boolean | null;
}

async function fetchActivationStatus(): Promise<ActivationStatus> {
    const [tradesResult, flagsResult, abRowsResult, alertsResult] =
        await Promise.all([
            supabase
                .from('trading_positions')
                .select('id', { count: 'exact', head: true })
                .eq('status', 'closed')
                .eq('position_mode', 'virtual'),
            supabase
                .from('trading_feature_flags' as never)
                .select('flag_key, enabled'),
            supabase
                .from('ab_session_comparison' as never)
                .select('session_date, a_synthetic_pnl, b_session_pnl')
                .order('session_date', { ascending: true })
                .limit(90),
            supabase
                .from('system_alerts' as never)
                .select('fired_at, level, event, detail, acknowledged')
                .order('fired_at', { ascending: false })
                .limit(50),
        ]);

    const closed_trade_count = tradesResult.count ?? 0;

    const flags: Record<string, boolean> = {};
    for (const row of (flagsResult.data ?? []) as FlagRow[]) {
        flags[row.flag_key] = row.enabled;
    }

    // ab_gate: mirror shadow_engine.get_ab_gate_status() math so the
    // dashboard renders the same numbers whether read from API or DB.
    const abRows = (abRowsResult.data ?? []) as AbDailyRow[];
    const firstDate = abRows[0]?.session_date;
    const daysElapsed = firstDate
        ? Math.floor(
              (Date.now() - new Date(firstDate).getTime()) / 86_400_000,
          )
        : 0;
    const tradingDays = abRows.length;
    const aTotal = abRows.reduce(
        (s, r) => s + (r.a_synthetic_pnl ?? 0),
        0,
    );
    const bTotal = abRows.reduce(
        (s, r) => s + (r.b_session_pnl ?? 0),
        0,
    );
    const aAnn =
        tradingDays > 0
            ? ((aTotal / ACCOUNT_NOTIONAL) / tradingDays) *
              TRADING_DAYS_PER_YEAR *
              100
            : 0;
    const bAnn =
        tradingDays > 0
            ? ((bTotal / ACCOUNT_NOTIONAL) / tradingDays) *
              TRADING_DAYS_PER_YEAR *
              100
            : 0;
    const bLead = bAnn - aAnn;

    const ab_gate: ActivationStatus['ab_gate'] = {
        built: tradingDays > 0,
        days_elapsed: tradingDays > 0 ? daysElapsed : null,
        days_required: 90,
        trades_count: closed_trade_count,
        trades_required: 100,
        portfolio_b_lead_pct:
            tradingDays > 0 ? Math.round(bLead * 100) / 100 : null,
        gate_passed:
            daysElapsed >= 90 && closed_trade_count >= 100 && bLead >= 8,
    };

    const recent_alerts = ((alertsResult.data ?? []) as AlertRow[]).map(
        (a) => ({
            fired_at: a.fired_at,
            level: a.level,
            event: a.event,
            detail: a.detail ?? '',
            acknowledged: Boolean(a.acknowledged),
        }),
    );

    return { closed_trade_count, flags, ab_gate, recent_alerts };
}

export function useActivationStatus() {
    return useQuery({
        queryKey: ['activation-status'],
        queryFn: fetchActivationStatus,
        refetchInterval: 60_000,
        staleTime: 30_000,
        retry: 2,
    });
}
