ALTER TABLE trading_system_health
ADD COLUMN IF NOT EXISTS last_valid_trade_at timestamptz;
