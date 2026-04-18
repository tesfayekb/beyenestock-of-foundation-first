ALTER TABLE trading_sessions
DROP CONSTRAINT IF EXISTS trading_sessions_regime_check;

ALTER TABLE trading_sessions
ADD CONSTRAINT trading_sessions_regime_check
CHECK (regime = ANY (ARRAY[
    'quiet_bullish',
    'volatile_bullish',
    'quiet_bearish',
    'volatile_bearish',
    'crisis',
    'pin_range',
    'range',
    'trend',
    'panic',
    'event',
    'unknown'
]));
