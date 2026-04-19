/**
 * useActivationStatus — fetches full activation state for DASH-A.
 *
 * Backs the Phase Activation Dashboard at /trading/activation.
 * Polls every 60 seconds so threshold transitions and new alerts
 * surface without a manual refresh.
 *
 * BACKEND_URL default mirrors useFeatureFlags.ts so both hooks work
 * identically when VITE_BACKEND_URL is unset (Lovable preview).
 */
import { useQuery } from '@tanstack/react-query';

const BACKEND_URL =
    import.meta.env.VITE_BACKEND_URL ??
    'https://diplomatic-mercy-production-7e61.up.railway.app';

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
            'Breadth divergence warning when index direction is narrow.',
        activationThreshold: 10,
        thresholdType: 'trades',
        autoEnable: true,
        builtStatus: 'not_built',
    },
    {
        key: 'signal:earnings_proximity:enabled',
        label: 'Earnings Proximity Guard',
        category: 'signal',
        description:
            'Widens condor strikes when major earnings are 1-2 days away.',
        activationThreshold: null,
        thresholdType: null,
        autoEnable: false,
        builtStatus: 'not_built',
    },
    {
        key: 'signal:iv_rank_filter:enabled',
        label: 'IV Rank Entry Filter',
        category: 'signal',
        description:
            'Sizes up when IV rank > 50%, down when < 30%.',
        activationThreshold: null,
        thresholdType: null,
        autoEnable: false,
        builtStatus: 'not_built',
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

async function fetchActivationStatus(): Promise<ActivationStatus> {
    const res = await fetch(`${BACKEND_URL}/admin/activation/status`);
    if (!res.ok) throw new Error('Failed to fetch activation status');
    return res.json();
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
