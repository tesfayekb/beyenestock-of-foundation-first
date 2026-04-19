export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      ab_session_comparison: {
        Row: {
          a_confidence: number | null
          a_direction: string | null
          a_no_trade: boolean | null
          a_regime: string | null
          a_synthetic_pnl: number | null
          a_would_have_traded: boolean | null
          b_no_trade: boolean | null
          b_session_pnl: number | null
          b_trades_count: number | null
          computed_at: string | null
          id: string
          move_pct: number | null
          session_date: string
          spx_close: number | null
          spx_open: number | null
        }
        Insert: {
          a_confidence?: number | null
          a_direction?: string | null
          a_no_trade?: boolean | null
          a_regime?: string | null
          a_synthetic_pnl?: number | null
          a_would_have_traded?: boolean | null
          b_no_trade?: boolean | null
          b_session_pnl?: number | null
          b_trades_count?: number | null
          computed_at?: string | null
          id?: string
          move_pct?: number | null
          session_date: string
          spx_close?: number | null
          spx_open?: number | null
        }
        Update: {
          a_confidence?: number | null
          a_direction?: string | null
          a_no_trade?: boolean | null
          a_regime?: string | null
          a_synthetic_pnl?: number | null
          a_would_have_traded?: boolean | null
          b_no_trade?: boolean | null
          b_session_pnl?: number | null
          b_trades_count?: number | null
          computed_at?: string | null
          id?: string
          move_pct?: number | null
          session_date?: string
          spx_close?: number | null
          spx_open?: number | null
        }
        Relationships: []
      }
      alert_configs: {
        Row: {
          comparison: string
          cooldown_seconds: number
          created_at: string
          created_by: string
          enabled: boolean
          id: string
          metric_key: string
          severity: string
          threshold_value: number
          updated_at: string
        }
        Insert: {
          comparison: string
          cooldown_seconds?: number
          created_at?: string
          created_by: string
          enabled?: boolean
          id?: string
          metric_key: string
          severity: string
          threshold_value: number
          updated_at?: string
        }
        Update: {
          comparison?: string
          cooldown_seconds?: number
          created_at?: string
          created_by?: string
          enabled?: boolean
          id?: string
          metric_key?: string
          severity?: string
          threshold_value?: number
          updated_at?: string
        }
        Relationships: []
      }
      alert_history: {
        Row: {
          alert_config_id: string
          created_at: string
          id: string
          metric_key: string
          metric_value: number
          resolved_at: string | null
          severity: string
          threshold_value: number
        }
        Insert: {
          alert_config_id: string
          created_at?: string
          id?: string
          metric_key: string
          metric_value: number
          resolved_at?: string | null
          severity: string
          threshold_value: number
        }
        Update: {
          alert_config_id?: string
          created_at?: string
          id?: string
          metric_key?: string
          metric_value?: number
          resolved_at?: string | null
          severity?: string
          threshold_value?: number
        }
        Relationships: [
          {
            foreignKeyName: "alert_history_alert_config_id_fkey"
            columns: ["alert_config_id"]
            isOneToOne: false
            referencedRelation: "alert_configs"
            referencedColumns: ["id"]
          },
        ]
      }
      audit_logs: {
        Row: {
          action: string
          actor_id: string | null
          correlation_id: string | null
          created_at: string
          id: string
          ip_address: unknown
          metadata: Json | null
          target_id: string | null
          target_type: string | null
          user_agent: string | null
        }
        Insert: {
          action: string
          actor_id?: string | null
          correlation_id?: string | null
          created_at?: string
          id?: string
          ip_address?: unknown
          metadata?: Json | null
          target_id?: string | null
          target_type?: string | null
          user_agent?: string | null
        }
        Update: {
          action?: string
          actor_id?: string | null
          correlation_id?: string | null
          created_at?: string
          id?: string
          ip_address?: unknown
          metadata?: Json | null
          target_id?: string | null
          target_type?: string | null
          user_agent?: string | null
        }
        Relationships: []
      }
      earnings_calendar: {
        Row: {
          actual_eps: number | null
          actual_move_pct: number | null
          announce_time: string | null
          created_at: string
          earnings_date: string
          estimated_eps: number | null
          fiscal_quarter: string | null
          id: string
          implied_move_pct: number | null
          straddle_opened: boolean | null
          straddle_pnl: number | null
          ticker: string
        }
        Insert: {
          actual_eps?: number | null
          actual_move_pct?: number | null
          announce_time?: string | null
          created_at?: string
          earnings_date: string
          estimated_eps?: number | null
          fiscal_quarter?: string | null
          id?: string
          implied_move_pct?: number | null
          straddle_opened?: boolean | null
          straddle_pnl?: number | null
          ticker: string
        }
        Update: {
          actual_eps?: number | null
          actual_move_pct?: number | null
          announce_time?: string | null
          created_at?: string
          earnings_date?: string
          estimated_eps?: number | null
          fiscal_quarter?: string | null
          id?: string
          implied_move_pct?: number | null
          straddle_opened?: boolean | null
          straddle_pnl?: number | null
          ticker?: string
        }
        Relationships: []
      }
      earnings_positions: {
        Row: {
          account_allocation_pct: number | null
          actual_move_pct: number | null
          announce_time: string | null
          call_premium: number | null
          call_strike: number | null
          contracts: number | null
          created_at: string
          earnings_date: string
          entry_date: string
          exit_date: string | null
          exit_reason: string | null
          exit_value: number | null
          expiry_date: string
          historical_edge_score: number | null
          id: string
          implied_move_pct: number | null
          net_pnl: number | null
          net_pnl_pct: number | null
          notes: string | null
          position_mode: string
          put_premium: number | null
          put_strike: number | null
          status: string
          stock_price_at_entry: number | null
          strategy_type: string
          ticker: string
          total_debit: number | null
          updated_at: string | null
        }
        Insert: {
          account_allocation_pct?: number | null
          actual_move_pct?: number | null
          announce_time?: string | null
          call_premium?: number | null
          call_strike?: number | null
          contracts?: number | null
          created_at?: string
          earnings_date: string
          entry_date: string
          exit_date?: string | null
          exit_reason?: string | null
          exit_value?: number | null
          expiry_date: string
          historical_edge_score?: number | null
          id?: string
          implied_move_pct?: number | null
          net_pnl?: number | null
          net_pnl_pct?: number | null
          notes?: string | null
          position_mode?: string
          put_premium?: number | null
          put_strike?: number | null
          status?: string
          stock_price_at_entry?: number | null
          strategy_type?: string
          ticker: string
          total_debit?: number | null
          updated_at?: string | null
        }
        Update: {
          account_allocation_pct?: number | null
          actual_move_pct?: number | null
          announce_time?: string | null
          call_premium?: number | null
          call_strike?: number | null
          contracts?: number | null
          created_at?: string
          earnings_date?: string
          entry_date?: string
          exit_date?: string | null
          exit_reason?: string | null
          exit_value?: number | null
          expiry_date?: string
          historical_edge_score?: number | null
          id?: string
          implied_move_pct?: number | null
          net_pnl?: number | null
          net_pnl_pct?: number | null
          notes?: string | null
          position_mode?: string
          put_premium?: number | null
          put_strike?: number | null
          status?: string
          stock_price_at_entry?: number | null
          strategy_type?: string
          ticker?: string
          total_debit?: number | null
          updated_at?: string | null
        }
        Relationships: []
      }
      earnings_upcoming_scan: {
        Row: {
          payload: Json
          scan_id: number
          scanned_at: string
        }
        Insert: {
          payload: Json
          scan_id?: number
          scanned_at?: string
        }
        Update: {
          payload?: Json
          scan_id?: number
          scanned_at?: string
        }
        Relationships: []
      }
      invitations: {
        Row: {
          accepted_at: string | null
          accepted_by: string | null
          created_at: string | null
          email: string
          expires_at: string
          id: string
          invited_by: string
          role_id: string | null
          status: string
          token_hash: string
        }
        Insert: {
          accepted_at?: string | null
          accepted_by?: string | null
          created_at?: string | null
          email: string
          expires_at?: string
          id?: string
          invited_by: string
          role_id?: string | null
          status?: string
          token_hash: string
        }
        Update: {
          accepted_at?: string | null
          accepted_by?: string | null
          created_at?: string | null
          email?: string
          expires_at?: string
          id?: string
          invited_by?: string
          role_id?: string | null
          status?: string
          token_hash?: string
        }
        Relationships: [
          {
            foreignKeyName: "invitations_role_id_fkey"
            columns: ["role_id"]
            isOneToOne: false
            referencedRelation: "roles"
            referencedColumns: ["id"]
          },
        ]
      }
      job_executions: {
        Row: {
          affected_records: number | null
          attempt: number
          completed_at: string | null
          correlation_id: string | null
          created_at: string
          duration_ms: number | null
          error: Json | null
          execution_id: string
          failure_type: string | null
          id: string
          job_id: string
          job_version: string
          metadata: Json | null
          parent_execution_id: string | null
          queue_delay_ms: number | null
          resource_usage: Json | null
          root_execution_id: string | null
          schedule_window_id: string | null
          scheduled_time: string | null
          started_at: string | null
          state: string
        }
        Insert: {
          affected_records?: number | null
          attempt?: number
          completed_at?: string | null
          correlation_id?: string | null
          created_at?: string
          duration_ms?: number | null
          error?: Json | null
          execution_id?: string
          failure_type?: string | null
          id?: string
          job_id: string
          job_version?: string
          metadata?: Json | null
          parent_execution_id?: string | null
          queue_delay_ms?: number | null
          resource_usage?: Json | null
          root_execution_id?: string | null
          schedule_window_id?: string | null
          scheduled_time?: string | null
          started_at?: string | null
          state?: string
        }
        Update: {
          affected_records?: number | null
          attempt?: number
          completed_at?: string | null
          correlation_id?: string | null
          created_at?: string
          duration_ms?: number | null
          error?: Json | null
          execution_id?: string
          failure_type?: string | null
          id?: string
          job_id?: string
          job_version?: string
          metadata?: Json | null
          parent_execution_id?: string | null
          queue_delay_ms?: number | null
          resource_usage?: Json | null
          root_execution_id?: string | null
          schedule_window_id?: string | null
          scheduled_time?: string | null
          started_at?: string | null
          state?: string
        }
        Relationships: [
          {
            foreignKeyName: "job_executions_job_id_fkey"
            columns: ["job_id"]
            isOneToOne: false
            referencedRelation: "job_registry"
            referencedColumns: ["id"]
          },
        ]
      }
      job_idempotency_keys: {
        Row: {
          created_at: string
          execution_id: string
          expires_at: string
          id: string
          idempotency_key: string
          job_id: string
          result_hash: string | null
        }
        Insert: {
          created_at?: string
          execution_id: string
          expires_at?: string
          id?: string
          idempotency_key: string
          job_id: string
          result_hash?: string | null
        }
        Update: {
          created_at?: string
          execution_id?: string
          expires_at?: string
          id?: string
          idempotency_key?: string
          job_id?: string
          result_hash?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "job_idempotency_keys_execution_id_fkey"
            columns: ["execution_id"]
            isOneToOne: false
            referencedRelation: "job_executions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "job_idempotency_keys_job_id_fkey"
            columns: ["job_id"]
            isOneToOne: false
            referencedRelation: "job_registry"
            referencedColumns: ["id"]
          },
        ]
      }
      job_registry: {
        Row: {
          circuit_breaker_threshold: number | null
          class: string
          concurrency_policy: string
          created_at: string
          description: string | null
          enabled: boolean
          execution_guarantee: string
          id: string
          max_retries: number
          owner_module: string
          priority: string
          replay_safe: boolean
          retry_policy: string
          schedule: string
          status: string
          timeout_seconds: number
          trigger_type: string
          updated_at: string
          version: string
        }
        Insert: {
          circuit_breaker_threshold?: number | null
          class?: string
          concurrency_policy?: string
          created_at?: string
          description?: string | null
          enabled?: boolean
          execution_guarantee?: string
          id: string
          max_retries?: number
          owner_module: string
          priority?: string
          replay_safe?: boolean
          retry_policy?: string
          schedule?: string
          status?: string
          timeout_seconds?: number
          trigger_type?: string
          updated_at?: string
          version?: string
        }
        Update: {
          circuit_breaker_threshold?: number | null
          class?: string
          concurrency_policy?: string
          created_at?: string
          description?: string | null
          enabled?: boolean
          execution_guarantee?: string
          id?: string
          max_retries?: number
          owner_module?: string
          priority?: string
          replay_safe?: boolean
          retry_policy?: string
          schedule?: string
          status?: string
          timeout_seconds?: number
          trigger_type?: string
          updated_at?: string
          version?: string
        }
        Relationships: []
      }
      mfa_recovery_attempts: {
        Row: {
          failed_count: number
          last_attempt_at: string
          locked_until: string | null
          user_id: string
        }
        Insert: {
          failed_count?: number
          last_attempt_at?: string
          locked_until?: string | null
          user_id: string
        }
        Update: {
          failed_count?: number
          last_attempt_at?: string
          locked_until?: string | null
          user_id?: string
        }
        Relationships: []
      }
      mfa_recovery_codes: {
        Row: {
          code_hash: string
          created_at: string
          id: string
          used_at: string | null
          user_id: string
        }
        Insert: {
          code_hash: string
          created_at?: string
          id?: string
          used_at?: string | null
          user_id: string
        }
        Update: {
          code_hash?: string
          created_at?: string
          id?: string
          used_at?: string | null
          user_id?: string
        }
        Relationships: []
      }
      paper_phase_criteria: {
        Row: {
          created_at: string
          criterion_id: string
          criterion_name: string
          current_value_numeric: number | null
          current_value_text: string | null
          id: string
          is_manual: boolean | null
          last_evaluated_at: string | null
          notes: string | null
          observations_count: number | null
          status: string
          target_description: string
          target_numeric: number | null
          updated_at: string
        }
        Insert: {
          created_at?: string
          criterion_id: string
          criterion_name: string
          current_value_numeric?: number | null
          current_value_text?: string | null
          id?: string
          is_manual?: boolean | null
          last_evaluated_at?: string | null
          notes?: string | null
          observations_count?: number | null
          status?: string
          target_description: string
          target_numeric?: number | null
          updated_at?: string
        }
        Update: {
          created_at?: string
          criterion_id?: string
          criterion_name?: string
          current_value_numeric?: number | null
          current_value_text?: string | null
          id?: string
          is_manual?: boolean | null
          last_evaluated_at?: string | null
          notes?: string | null
          observations_count?: number | null
          status?: string
          target_description?: string
          target_numeric?: number | null
          updated_at?: string
        }
        Relationships: []
      }
      permissions: {
        Row: {
          created_at: string
          description: string | null
          id: string
          key: string
        }
        Insert: {
          created_at?: string
          description?: string | null
          id?: string
          key: string
        }
        Update: {
          created_at?: string
          description?: string | null
          id?: string
          key?: string
        }
        Relationships: []
      }
      profiles: {
        Row: {
          avatar_url: string | null
          created_at: string
          display_name: string | null
          email: string | null
          email_verified: boolean | null
          id: string
          last_name: string | null
          status: string
          tradier_account_id: string | null
          tradier_connected: boolean | null
          trading_tier: string | null
          updated_at: string
        }
        Insert: {
          avatar_url?: string | null
          created_at?: string
          display_name?: string | null
          email?: string | null
          email_verified?: boolean | null
          id: string
          last_name?: string | null
          status?: string
          tradier_account_id?: string | null
          tradier_connected?: boolean | null
          trading_tier?: string | null
          updated_at?: string
        }
        Update: {
          avatar_url?: string | null
          created_at?: string
          display_name?: string | null
          email?: string | null
          email_verified?: boolean | null
          id?: string
          last_name?: string | null
          status?: string
          tradier_account_id?: string | null
          tradier_connected?: boolean | null
          trading_tier?: string | null
          updated_at?: string
        }
        Relationships: []
      }
      role_permissions: {
        Row: {
          id: string
          permission_id: string
          role_id: string
        }
        Insert: {
          id?: string
          permission_id: string
          role_id: string
        }
        Update: {
          id?: string
          permission_id?: string
          role_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "role_permissions_permission_id_fkey"
            columns: ["permission_id"]
            isOneToOne: false
            referencedRelation: "permissions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "role_permissions_role_id_fkey"
            columns: ["role_id"]
            isOneToOne: false
            referencedRelation: "roles"
            referencedColumns: ["id"]
          },
        ]
      }
      roles: {
        Row: {
          created_at: string
          description: string | null
          id: string
          is_base: boolean
          is_immutable: boolean
          is_permission_locked: boolean
          key: string
          name: string
          updated_at: string
        }
        Insert: {
          created_at?: string
          description?: string | null
          id?: string
          is_base?: boolean
          is_immutable?: boolean
          is_permission_locked?: boolean
          key: string
          name: string
          updated_at?: string
        }
        Update: {
          created_at?: string
          description?: string | null
          id?: string
          is_base?: boolean
          is_immutable?: boolean
          is_permission_locked?: boolean
          key?: string
          name?: string
          updated_at?: string
        }
        Relationships: []
      }
      shadow_predictions: {
        Row: {
          confidence: number | null
          direction: string | null
          gex_net: number | null
          id: string
          no_trade_reason: string | null
          no_trade_signal: boolean | null
          predicted_at: string
          rcs: number | null
          regime: string | null
          session_id: string | null
          spx_price: number | null
          vix: number | null
          vvix_z_score: number | null
        }
        Insert: {
          confidence?: number | null
          direction?: string | null
          gex_net?: number | null
          id?: string
          no_trade_reason?: string | null
          no_trade_signal?: boolean | null
          predicted_at?: string
          rcs?: number | null
          regime?: string | null
          session_id?: string | null
          spx_price?: number | null
          vix?: number | null
          vvix_z_score?: number | null
        }
        Update: {
          confidence?: number | null
          direction?: string | null
          gex_net?: number | null
          id?: string
          no_trade_reason?: string | null
          no_trade_signal?: boolean | null
          predicted_at?: string
          rcs?: number | null
          regime?: string | null
          session_id?: string | null
          spx_price?: number | null
          vix?: number | null
          vvix_z_score?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "shadow_predictions_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "trading_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      system_alerts: {
        Row: {
          ack_at: string | null
          acknowledged: boolean | null
          detail: string | null
          event: string
          fired_at: string
          id: string
          level: string
        }
        Insert: {
          ack_at?: string | null
          acknowledged?: boolean | null
          detail?: string | null
          event: string
          fired_at?: string
          id?: string
          level: string
        }
        Update: {
          ack_at?: string | null
          acknowledged?: boolean | null
          detail?: string | null
          event?: string
          fired_at?: string
          id?: string
          level?: string
        }
        Relationships: []
      }
      system_config: {
        Row: {
          description: string | null
          key: string
          updated_at: string | null
          updated_by: string | null
          value: Json
        }
        Insert: {
          description?: string | null
          key: string
          updated_at?: string | null
          updated_by?: string | null
          value: Json
        }
        Update: {
          description?: string | null
          key?: string
          updated_at?: string | null
          updated_by?: string | null
          value?: Json
        }
        Relationships: []
      }
      system_health_snapshots: {
        Row: {
          checks: Json
          created_at: string
          id: string
          status: string
        }
        Insert: {
          checks?: Json
          created_at?: string
          id?: string
          status: string
        }
        Update: {
          checks?: Json
          created_at?: string
          id?: string
          status?: string
        }
        Relationships: []
      }
      system_metrics: {
        Row: {
          id: string
          metadata: Json | null
          metric_key: string
          recorded_at: string
          value: number
        }
        Insert: {
          id?: string
          metadata?: Json | null
          metric_key: string
          recorded_at?: string
          value: number
        }
        Update: {
          id?: string
          metadata?: Json | null
          metric_key?: string
          recorded_at?: string
          value?: number
        }
        Relationships: []
      }
      trading_ai_briefs: {
        Row: {
          brief_kind: string
          generated_at: string
          payload: Json
        }
        Insert: {
          brief_kind: string
          generated_at?: string
          payload: Json
        }
        Update: {
          brief_kind?: string
          generated_at?: string
          payload?: Json
        }
        Relationships: []
      }
      trading_calibration_log: {
        Row: {
          actual_slippage: number | null
          call_touched_by_exit: boolean | null
          charm_velocity: number | null
          created_at: string | null
          cv_stress_score: number | null
          exit_reason: string | null
          exit_triggered: boolean | null
          fn_flag: boolean | null
          forward_pnl_20m: number | null
          fp_flag: boolean | null
          id: string
          pct_max_profit: number | null
          position_id: string | null
          position_state: number | null
          predicted_slippage: number | null
          put_touched_by_exit: boolean | null
          regime: string | null
          sigma_effective: number | null
          sigma_implied: number | null
          sigma_realized: number | null
          signal_type: string | null
          slippage_delta: number | null
          spx_price: number | null
          strategy_type: string | null
          t_years_to_exit: number | null
          touch_prob_call: number | null
          touch_prob_max: number | null
          touch_prob_put: number | null
          ts: string
          unrealized_pnl: number | null
          vanna_velocity: number | null
          vix: number | null
          vvix: number | null
          was_correct_exit: boolean | null
          z_charm: number | null
          z_vanna: number | null
        }
        Insert: {
          actual_slippage?: number | null
          call_touched_by_exit?: boolean | null
          charm_velocity?: number | null
          created_at?: string | null
          cv_stress_score?: number | null
          exit_reason?: string | null
          exit_triggered?: boolean | null
          fn_flag?: boolean | null
          forward_pnl_20m?: number | null
          fp_flag?: boolean | null
          id?: string
          pct_max_profit?: number | null
          position_id?: string | null
          position_state?: number | null
          predicted_slippage?: number | null
          put_touched_by_exit?: boolean | null
          regime?: string | null
          sigma_effective?: number | null
          sigma_implied?: number | null
          sigma_realized?: number | null
          signal_type?: string | null
          slippage_delta?: number | null
          spx_price?: number | null
          strategy_type?: string | null
          t_years_to_exit?: number | null
          touch_prob_call?: number | null
          touch_prob_max?: number | null
          touch_prob_put?: number | null
          ts?: string
          unrealized_pnl?: number | null
          vanna_velocity?: number | null
          vix?: number | null
          vvix?: number | null
          was_correct_exit?: boolean | null
          z_charm?: number | null
          z_vanna?: number | null
        }
        Update: {
          actual_slippage?: number | null
          call_touched_by_exit?: boolean | null
          charm_velocity?: number | null
          created_at?: string | null
          cv_stress_score?: number | null
          exit_reason?: string | null
          exit_triggered?: boolean | null
          fn_flag?: boolean | null
          forward_pnl_20m?: number | null
          fp_flag?: boolean | null
          id?: string
          pct_max_profit?: number | null
          position_id?: string | null
          position_state?: number | null
          predicted_slippage?: number | null
          put_touched_by_exit?: boolean | null
          regime?: string | null
          sigma_effective?: number | null
          sigma_implied?: number | null
          sigma_realized?: number | null
          signal_type?: string | null
          slippage_delta?: number | null
          spx_price?: number | null
          strategy_type?: string | null
          t_years_to_exit?: number | null
          touch_prob_call?: number | null
          touch_prob_max?: number | null
          touch_prob_put?: number | null
          ts?: string
          unrealized_pnl?: number | null
          vanna_velocity?: number | null
          vix?: number | null
          vvix?: number | null
          was_correct_exit?: boolean | null
          z_charm?: number | null
          z_vanna?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "trading_calibration_log_position_id_fkey"
            columns: ["position_id"]
            isOneToOne: false
            referencedRelation: "trading_positions"
            referencedColumns: ["id"]
          },
        ]
      }
      trading_feature_flags: {
        Row: {
          enabled: boolean
          flag_key: string
          updated_at: string
          updated_by: string | null
        }
        Insert: {
          enabled?: boolean
          flag_key: string
          updated_at?: string
          updated_by?: string | null
        }
        Update: {
          enabled?: boolean
          flag_key?: string
          updated_at?: string
          updated_by?: string | null
        }
        Relationships: []
      }
      trading_model_performance: {
        Row: {
          accuracy_20d: number | null
          accuracy_5d: number | null
          accuracy_60d: number | null
          accuracy_event_day: number | null
          accuracy_range_day: number | null
          accuracy_reversal_day: number | null
          accuracy_trend_day: number | null
          challenger_active: boolean | null
          challenger_model_id: string | null
          champion_model_id: string | null
          created_at: string | null
          cv_stress_fn_rate: number | null
          cv_stress_fp_rate: number | null
          drift_status: string | null
          drift_z_score: number | null
          id: string
          preservation_triggers_this_week: number | null
          profit_factor_20d: number | null
          recorded_at: string
          regime_agreement_rate: number | null
          samples_since_retrain: number | null
          session_id: string | null
          sharpe_20d: number | null
          slippage_mae: number | null
          slippage_observations: number | null
          touch_prob_brier: number | null
          touch_prob_observations: number | null
          win_rate_20d: number | null
          win_rate_5d: number | null
          win_rate_60d: number | null
        }
        Insert: {
          accuracy_20d?: number | null
          accuracy_5d?: number | null
          accuracy_60d?: number | null
          accuracy_event_day?: number | null
          accuracy_range_day?: number | null
          accuracy_reversal_day?: number | null
          accuracy_trend_day?: number | null
          challenger_active?: boolean | null
          challenger_model_id?: string | null
          champion_model_id?: string | null
          created_at?: string | null
          cv_stress_fn_rate?: number | null
          cv_stress_fp_rate?: number | null
          drift_status?: string | null
          drift_z_score?: number | null
          id?: string
          preservation_triggers_this_week?: number | null
          profit_factor_20d?: number | null
          recorded_at?: string
          regime_agreement_rate?: number | null
          samples_since_retrain?: number | null
          session_id?: string | null
          sharpe_20d?: number | null
          slippage_mae?: number | null
          slippage_observations?: number | null
          touch_prob_brier?: number | null
          touch_prob_observations?: number | null
          win_rate_20d?: number | null
          win_rate_5d?: number | null
          win_rate_60d?: number | null
        }
        Update: {
          accuracy_20d?: number | null
          accuracy_5d?: number | null
          accuracy_60d?: number | null
          accuracy_event_day?: number | null
          accuracy_range_day?: number | null
          accuracy_reversal_day?: number | null
          accuracy_trend_day?: number | null
          challenger_active?: boolean | null
          challenger_model_id?: string | null
          champion_model_id?: string | null
          created_at?: string | null
          cv_stress_fn_rate?: number | null
          cv_stress_fp_rate?: number | null
          drift_status?: string | null
          drift_z_score?: number | null
          id?: string
          preservation_triggers_this_week?: number | null
          profit_factor_20d?: number | null
          recorded_at?: string
          regime_agreement_rate?: number | null
          samples_since_retrain?: number | null
          session_id?: string | null
          sharpe_20d?: number | null
          slippage_mae?: number | null
          slippage_observations?: number | null
          touch_prob_brier?: number | null
          touch_prob_observations?: number | null
          win_rate_20d?: number | null
          win_rate_5d?: number | null
          win_rate_60d?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "trading_model_performance_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "trading_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      trading_operator_config: {
        Row: {
          account_type: string | null
          created_at: string | null
          encrypted_key: string | null
          id: string
          is_sandbox: boolean | null
          live_trading_enabled: boolean | null
          sizing_phase: number | null
          tradier_account_id: string | null
          tradier_key_preview: string | null
          updated_at: string | null
          user_id: string
        }
        Insert: {
          account_type?: string | null
          created_at?: string | null
          encrypted_key?: string | null
          id?: string
          is_sandbox?: boolean | null
          live_trading_enabled?: boolean | null
          sizing_phase?: number | null
          tradier_account_id?: string | null
          tradier_key_preview?: string | null
          updated_at?: string | null
          user_id: string
        }
        Update: {
          account_type?: string | null
          created_at?: string | null
          encrypted_key?: string | null
          id?: string
          is_sandbox?: boolean | null
          live_trading_enabled?: boolean | null
          sizing_phase?: number | null
          tradier_account_id?: string | null
          tradier_key_preview?: string | null
          updated_at?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "trading_operator_config_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: true
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      trading_positions: {
        Row: {
          attribution_direction: boolean | null
          attribution_structure: boolean | null
          attribution_timing: boolean | null
          attribution_vol: boolean | null
          commission_cost: number | null
          contracts: number | null
          created_at: string | null
          current_cv_stress: number | null
          current_pnl: number | null
          current_state: number | null
          current_touch_prob: number | null
          decision_context: Json | null
          entry_at: string
          entry_credit: number | null
          entry_cv_stress: number | null
          entry_greeks: Json | null
          entry_rcs: number | null
          entry_regime: string | null
          entry_slippage: number | null
          entry_spx_price: number | null
          entry_touch_prob: number | null
          exit_at: string | null
          exit_credit: number | null
          exit_reason: string | null
          exit_slippage: number | null
          exit_spx_price: number | null
          expiry_date: string | null
          far_expiry_date: string | null
          gross_pnl: number | null
          id: string
          instrument: string
          last_updated_at: string | null
          long_strike: number | null
          long_strike_2: number | null
          net_pnl: number | null
          peak_pnl: number | null
          position_mode: string
          position_type: string | null
          prediction_id: string | null
          session_id: string | null
          short_strike: number | null
          short_strike_2: number | null
          signal_id: string | null
          slippage_cost: number | null
          status: string | null
          strategy_type: string
          tradier_fill_price: number | null
          tradier_order_id: string | null
        }
        Insert: {
          attribution_direction?: boolean | null
          attribution_structure?: boolean | null
          attribution_timing?: boolean | null
          attribution_vol?: boolean | null
          commission_cost?: number | null
          contracts?: number | null
          created_at?: string | null
          current_cv_stress?: number | null
          current_pnl?: number | null
          current_state?: number | null
          current_touch_prob?: number | null
          decision_context?: Json | null
          entry_at: string
          entry_credit?: number | null
          entry_cv_stress?: number | null
          entry_greeks?: Json | null
          entry_rcs?: number | null
          entry_regime?: string | null
          entry_slippage?: number | null
          entry_spx_price?: number | null
          entry_touch_prob?: number | null
          exit_at?: string | null
          exit_credit?: number | null
          exit_reason?: string | null
          exit_slippage?: number | null
          exit_spx_price?: number | null
          expiry_date?: string | null
          far_expiry_date?: string | null
          gross_pnl?: number | null
          id?: string
          instrument: string
          last_updated_at?: string | null
          long_strike?: number | null
          long_strike_2?: number | null
          net_pnl?: number | null
          peak_pnl?: number | null
          position_mode: string
          position_type?: string | null
          prediction_id?: string | null
          session_id?: string | null
          short_strike?: number | null
          short_strike_2?: number | null
          signal_id?: string | null
          slippage_cost?: number | null
          status?: string | null
          strategy_type: string
          tradier_fill_price?: number | null
          tradier_order_id?: string | null
        }
        Update: {
          attribution_direction?: boolean | null
          attribution_structure?: boolean | null
          attribution_timing?: boolean | null
          attribution_vol?: boolean | null
          commission_cost?: number | null
          contracts?: number | null
          created_at?: string | null
          current_cv_stress?: number | null
          current_pnl?: number | null
          current_state?: number | null
          current_touch_prob?: number | null
          decision_context?: Json | null
          entry_at?: string
          entry_credit?: number | null
          entry_cv_stress?: number | null
          entry_greeks?: Json | null
          entry_rcs?: number | null
          entry_regime?: string | null
          entry_slippage?: number | null
          entry_spx_price?: number | null
          entry_touch_prob?: number | null
          exit_at?: string | null
          exit_credit?: number | null
          exit_reason?: string | null
          exit_slippage?: number | null
          exit_spx_price?: number | null
          expiry_date?: string | null
          far_expiry_date?: string | null
          gross_pnl?: number | null
          id?: string
          instrument?: string
          last_updated_at?: string | null
          long_strike?: number | null
          long_strike_2?: number | null
          net_pnl?: number | null
          peak_pnl?: number | null
          position_mode?: string
          position_type?: string | null
          prediction_id?: string | null
          session_id?: string | null
          short_strike?: number | null
          short_strike_2?: number | null
          signal_id?: string | null
          slippage_cost?: number | null
          status?: string | null
          strategy_type?: string
          tradier_fill_price?: number | null
          tradier_order_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "trading_positions_prediction_id_fkey"
            columns: ["prediction_id"]
            isOneToOne: false
            referencedRelation: "trading_prediction_outputs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "trading_positions_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "trading_sessions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "trading_positions_signal_id_fkey"
            columns: ["signal_id"]
            isOneToOne: false
            referencedRelation: "trading_signals"
            referencedColumns: ["id"]
          },
        ]
      }
      trading_prediction_outputs: {
        Row: {
          capital_preservation_mode: boolean | null
          charm_velocity: number | null
          confidence: number | null
          created_at: string | null
          cv_stress_score: number | null
          direction: string | null
          execution_degraded: boolean | null
          expected_move_pct: number | null
          expected_move_pts: number | null
          gex_confidence: number | null
          gex_flip_zone: number | null
          gex_nearest_wall: number | null
          gex_net: number | null
          id: string
          job_execution_id: string | null
          no_trade_reason: string | null
          no_trade_signal: boolean | null
          p_bear: number | null
          p_bull: number | null
          p_neutral: number | null
          predicted_at: string
          rcs: number | null
          regime: string | null
          regime_agreement: boolean | null
          regime_hmm: string | null
          regime_lgbm: string | null
          session_id: string | null
          spx_price: number | null
          vanna_velocity: number | null
          vix: number | null
          vvix: number | null
          vvix_z_score: number | null
        }
        Insert: {
          capital_preservation_mode?: boolean | null
          charm_velocity?: number | null
          confidence?: number | null
          created_at?: string | null
          cv_stress_score?: number | null
          direction?: string | null
          execution_degraded?: boolean | null
          expected_move_pct?: number | null
          expected_move_pts?: number | null
          gex_confidence?: number | null
          gex_flip_zone?: number | null
          gex_nearest_wall?: number | null
          gex_net?: number | null
          id?: string
          job_execution_id?: string | null
          no_trade_reason?: string | null
          no_trade_signal?: boolean | null
          p_bear?: number | null
          p_bull?: number | null
          p_neutral?: number | null
          predicted_at?: string
          rcs?: number | null
          regime?: string | null
          regime_agreement?: boolean | null
          regime_hmm?: string | null
          regime_lgbm?: string | null
          session_id?: string | null
          spx_price?: number | null
          vanna_velocity?: number | null
          vix?: number | null
          vvix?: number | null
          vvix_z_score?: number | null
        }
        Update: {
          capital_preservation_mode?: boolean | null
          charm_velocity?: number | null
          confidence?: number | null
          created_at?: string | null
          cv_stress_score?: number | null
          direction?: string | null
          execution_degraded?: boolean | null
          expected_move_pct?: number | null
          expected_move_pts?: number | null
          gex_confidence?: number | null
          gex_flip_zone?: number | null
          gex_nearest_wall?: number | null
          gex_net?: number | null
          id?: string
          job_execution_id?: string | null
          no_trade_reason?: string | null
          no_trade_signal?: boolean | null
          p_bear?: number | null
          p_bull?: number | null
          p_neutral?: number | null
          predicted_at?: string
          rcs?: number | null
          regime?: string | null
          regime_agreement?: boolean | null
          regime_hmm?: string | null
          regime_lgbm?: string | null
          session_id?: string | null
          spx_price?: number | null
          vanna_velocity?: number | null
          vix?: number | null
          vvix?: number | null
          vvix_z_score?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "trading_prediction_outputs_job_execution_id_fkey"
            columns: ["job_execution_id"]
            isOneToOne: false
            referencedRelation: "job_executions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "trading_prediction_outputs_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "trading_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      trading_sessions: {
        Row: {
          actual_pnl: number | null
          allocation_tier: string | null
          capital_preservation_active: boolean | null
          consecutive_loss_sessions: number | null
          consecutive_losses_today: number | null
          created_at: string | null
          day_type: string | null
          day_type_confidence: number | null
          halt_reason: string | null
          id: string
          market_close_at: string | null
          market_open_at: string | null
          rcs: number | null
          regime: string | null
          session_date: string
          session_status: string | null
          spx_open: number | null
          updated_at: string | null
          virtual_losses: number | null
          virtual_pnl: number | null
          virtual_trades_count: number | null
          virtual_wins: number | null
          vix_open: number | null
          vvix_20d_mean: number | null
          vvix_20d_std: number | null
          vvix_open: number | null
        }
        Insert: {
          actual_pnl?: number | null
          allocation_tier?: string | null
          capital_preservation_active?: boolean | null
          consecutive_loss_sessions?: number | null
          consecutive_losses_today?: number | null
          created_at?: string | null
          day_type?: string | null
          day_type_confidence?: number | null
          halt_reason?: string | null
          id?: string
          market_close_at?: string | null
          market_open_at?: string | null
          rcs?: number | null
          regime?: string | null
          session_date: string
          session_status?: string | null
          spx_open?: number | null
          updated_at?: string | null
          virtual_losses?: number | null
          virtual_pnl?: number | null
          virtual_trades_count?: number | null
          virtual_wins?: number | null
          vix_open?: number | null
          vvix_20d_mean?: number | null
          vvix_20d_std?: number | null
          vvix_open?: number | null
        }
        Update: {
          actual_pnl?: number | null
          allocation_tier?: string | null
          capital_preservation_active?: boolean | null
          consecutive_loss_sessions?: number | null
          consecutive_losses_today?: number | null
          created_at?: string | null
          day_type?: string | null
          day_type_confidence?: number | null
          halt_reason?: string | null
          id?: string
          market_close_at?: string | null
          market_open_at?: string | null
          rcs?: number | null
          regime?: string | null
          session_date?: string
          session_status?: string | null
          spx_open?: number | null
          updated_at?: string | null
          virtual_losses?: number | null
          virtual_pnl?: number | null
          virtual_trades_count?: number | null
          virtual_wins?: number | null
          vix_open?: number | null
          vvix_20d_mean?: number | null
          vvix_20d_std?: number | null
          vvix_open?: number | null
        }
        Relationships: []
      }
      trading_signals: {
        Row: {
          contracts: number | null
          correlation_id: string | null
          created_at: string | null
          cv_stress_at_signal: number | null
          ev_net: number | null
          expiry_date: string | null
          gex_confidence_at_signal: number | null
          gex_wall_distance_pct: number | null
          id: string
          instrument: string
          job_execution_id: string | null
          long_strike: number | null
          long_strike_2: number | null
          position_size_pct: number | null
          position_type: string | null
          predicted_slippage: number | null
          prediction_id: string | null
          profit_target: number | null
          rcs_at_signal: number | null
          regime_at_signal: string | null
          rejection_reason: string | null
          session_id: string | null
          short_strike: number | null
          short_strike_2: number | null
          sigma_effective: number | null
          signal_at: string
          signal_status: string | null
          stop_loss_level: number | null
          strategy_type: string
          target_credit: number | null
          target_debit: number | null
          touch_prob_at_entry: number | null
        }
        Insert: {
          contracts?: number | null
          correlation_id?: string | null
          created_at?: string | null
          cv_stress_at_signal?: number | null
          ev_net?: number | null
          expiry_date?: string | null
          gex_confidence_at_signal?: number | null
          gex_wall_distance_pct?: number | null
          id?: string
          instrument: string
          job_execution_id?: string | null
          long_strike?: number | null
          long_strike_2?: number | null
          position_size_pct?: number | null
          position_type?: string | null
          predicted_slippage?: number | null
          prediction_id?: string | null
          profit_target?: number | null
          rcs_at_signal?: number | null
          regime_at_signal?: string | null
          rejection_reason?: string | null
          session_id?: string | null
          short_strike?: number | null
          short_strike_2?: number | null
          sigma_effective?: number | null
          signal_at?: string
          signal_status?: string | null
          stop_loss_level?: number | null
          strategy_type: string
          target_credit?: number | null
          target_debit?: number | null
          touch_prob_at_entry?: number | null
        }
        Update: {
          contracts?: number | null
          correlation_id?: string | null
          created_at?: string | null
          cv_stress_at_signal?: number | null
          ev_net?: number | null
          expiry_date?: string | null
          gex_confidence_at_signal?: number | null
          gex_wall_distance_pct?: number | null
          id?: string
          instrument?: string
          job_execution_id?: string | null
          long_strike?: number | null
          long_strike_2?: number | null
          position_size_pct?: number | null
          position_type?: string | null
          predicted_slippage?: number | null
          prediction_id?: string | null
          profit_target?: number | null
          rcs_at_signal?: number | null
          regime_at_signal?: string | null
          rejection_reason?: string | null
          session_id?: string | null
          short_strike?: number | null
          short_strike_2?: number | null
          sigma_effective?: number | null
          signal_at?: string
          signal_status?: string | null
          stop_loss_level?: number | null
          strategy_type?: string
          target_credit?: number | null
          target_debit?: number | null
          touch_prob_at_entry?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "trading_signals_job_execution_id_fkey"
            columns: ["job_execution_id"]
            isOneToOne: false
            referencedRelation: "job_executions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "trading_signals_prediction_id_fkey"
            columns: ["prediction_id"]
            isOneToOne: false
            referencedRelation: "trading_prediction_outputs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "trading_signals_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "trading_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      trading_system_health: {
        Row: {
          cboe_connected: boolean | null
          created_at: string | null
          current_session_id: string | null
          data_lag_seconds: number | null
          databento_connected: boolean | null
          details: Json | null
          error_count_1h: number | null
          gex_confidence: number | null
          gex_staleness_seconds: number | null
          id: string
          is_market_hours: boolean | null
          last_data_at: string | null
          last_error_message: string | null
          last_heartbeat_at: string
          last_valid_trade_at: string | null
          latency_ms: number | null
          service_name: string
          slippage_model_age_hours: number | null
          slippage_model_observations: number | null
          status: string
          tradier_ws_connected: boolean | null
          updated_at: string | null
        }
        Insert: {
          cboe_connected?: boolean | null
          created_at?: string | null
          current_session_id?: string | null
          data_lag_seconds?: number | null
          databento_connected?: boolean | null
          details?: Json | null
          error_count_1h?: number | null
          gex_confidence?: number | null
          gex_staleness_seconds?: number | null
          id?: string
          is_market_hours?: boolean | null
          last_data_at?: string | null
          last_error_message?: string | null
          last_heartbeat_at?: string
          last_valid_trade_at?: string | null
          latency_ms?: number | null
          service_name: string
          slippage_model_age_hours?: number | null
          slippage_model_observations?: number | null
          status: string
          tradier_ws_connected?: boolean | null
          updated_at?: string | null
        }
        Update: {
          cboe_connected?: boolean | null
          created_at?: string | null
          current_session_id?: string | null
          data_lag_seconds?: number | null
          databento_connected?: boolean | null
          details?: Json | null
          error_count_1h?: number | null
          gex_confidence?: number | null
          gex_staleness_seconds?: number | null
          id?: string
          is_market_hours?: boolean | null
          last_data_at?: string | null
          last_error_message?: string | null
          last_heartbeat_at?: string
          last_valid_trade_at?: string | null
          latency_ms?: number | null
          service_name?: string
          slippage_model_age_hours?: number | null
          slippage_model_observations?: number | null
          status?: string
          tradier_ws_connected?: boolean | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "trading_system_health_current_session_id_fkey"
            columns: ["current_session_id"]
            isOneToOne: false
            referencedRelation: "trading_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      user_roles: {
        Row: {
          assigned_at: string
          assigned_by: string | null
          id: string
          role_id: string
          user_id: string
        }
        Insert: {
          assigned_at?: string
          assigned_by?: string | null
          id?: string
          role_id: string
          user_id: string
        }
        Update: {
          assigned_at?: string
          assigned_by?: string | null
          id?: string
          role_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "user_roles_role_id_fkey"
            columns: ["role_id"]
            isOneToOne: false
            referencedRelation: "roles"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      cleanup_mfa_recovery_codes: { Args: never; Returns: undefined }
      get_feedback_trades: {
        Args: never
        Returns: {
          contracts: number
          entry_at: string
          entry_credit: number
          entry_regime: string
          exit_at: string
          id: string
          net_pnl: number
          prediction_confidence: number
          prediction_direction: string
          prediction_regime: string
          session_id: string
          strategy_type: string
        }[]
      }
      get_my_authorization_context: { Args: never; Returns: Json }
      has_permission: {
        Args: { _permission_key: string; _user_id: string }
        Returns: boolean
      }
      has_role:
        | {
            Args: {
              _role: Database["public"]["Enums"]["app_role"]
              _user_id: string
            }
            Returns: boolean
          }
        | { Args: { _role_key: string; _user_id: string }; Returns: boolean }
      is_superadmin: { Args: { _user_id: string }; Returns: boolean }
      rpc_batch_delete_audit_logs: {
        Args: { batch_size?: number; cutoff: string }
        Returns: number
      }
    }
    Enums: {
      app_role: "admin" | "moderator" | "user"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      app_role: ["admin", "moderator", "user"],
    },
  },
} as const
