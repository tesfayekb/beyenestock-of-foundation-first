-- Phase 5A: Earnings Volatility System tables
-- Separate from trading_positions — different instrument, different edge,
-- different tax treatment (NOT Section 1256).

CREATE TABLE earnings_positions (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker                TEXT NOT NULL,
  earnings_date         DATE NOT NULL,
  announce_time         TEXT CHECK (announce_time IN ('pre','post','unknown')),
  position_mode         TEXT NOT NULL DEFAULT 'virtual'
                          CHECK (position_mode IN ('virtual','live')),
  strategy_type         TEXT NOT NULL DEFAULT 'earnings_straddle',
  entry_date            DATE NOT NULL,
  call_strike           NUMERIC(10,2),
  put_strike            NUMERIC(10,2),
  stock_price_at_entry  NUMERIC(10,2),
  call_premium          NUMERIC(8,4),  -- per share
  put_premium           NUMERIC(8,4),  -- per share
  total_debit           NUMERIC(10,4), -- (call + put) × 100 × contracts
  contracts             INTEGER DEFAULT 1,
  account_allocation_pct NUMERIC(5,3),
  expiry_date           DATE NOT NULL,
  implied_move_pct      NUMERIC(8,4),  -- ATM straddle / stock price at entry
  historical_edge_score NUMERIC(5,3),  -- 0-1, based on historical beat rate
  status                TEXT NOT NULL DEFAULT 'open'
                          CHECK (status IN ('open','closed','expired')),
  exit_date             DATE,
  exit_value            NUMERIC(10,4), -- (call_exit + put_exit) × 100 × contracts
  exit_reason           TEXT CHECK (exit_reason IN (
    'post_announcement_30min',
    'doubled_take_profit',
    'stopped_out_75pct_loss',
    'manual_close',
    'expired_worthless',
    'time_stop_eod'
  )),
  actual_move_pct       NUMERIC(8,4),  -- filled after announcement
  net_pnl               NUMERIC(10,4), -- exit_value - total_debit
  net_pnl_pct           NUMERIC(8,4),  -- net_pnl / total_debit
  notes                 TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ep_ticker_date    ON earnings_positions(ticker, earnings_date DESC);
CREATE INDEX idx_ep_status         ON earnings_positions(status, entry_date DESC);
CREATE INDEX idx_ep_position_mode  ON earnings_positions(position_mode, status);

ALTER TABLE earnings_positions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_full" ON earnings_positions
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "authenticated_read" ON earnings_positions
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM user_roles ur
      JOIN role_permissions rp ON rp.role_id = ur.role_id
      JOIN permissions p ON p.id = rp.permission_id
      WHERE ur.user_id = auth.uid() AND p.key = 'trading.view'
    )
  );

-- Earnings calendar tracking
CREATE TABLE earnings_calendar (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticker            TEXT NOT NULL,
  earnings_date     DATE NOT NULL,
  fiscal_quarter    TEXT,
  announce_time     TEXT CHECK (announce_time IN ('pre','post','unknown')),
  estimated_eps     NUMERIC(8,4),
  actual_eps        NUMERIC(8,4),
  implied_move_pct  NUMERIC(8,4),  -- at time of entry decision
  actual_move_pct   NUMERIC(8,4),  -- filled after announcement
  straddle_opened   BOOLEAN DEFAULT false,
  straddle_pnl      NUMERIC(10,4),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(ticker, earnings_date)
);

CREATE INDEX idx_ec_date   ON earnings_calendar(earnings_date DESC);
CREATE INDEX idx_ec_ticker ON earnings_calendar(ticker, earnings_date DESC);

ALTER TABLE earnings_calendar ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_full" ON earnings_calendar
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "authenticated_read" ON earnings_calendar
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM user_roles ur
      JOIN role_permissions rp ON rp.role_id = ur.role_id
      JOIN permissions p ON p.id = rp.permission_id
      WHERE ur.user_id = auth.uid() AND p.key = 'trading.view'
    )
  );
