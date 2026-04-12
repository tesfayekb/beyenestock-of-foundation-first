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
          email_verified: boolean | null
          id: string
          status: string
          updated_at: string
        }
        Insert: {
          avatar_url?: string | null
          created_at?: string
          display_name?: string | null
          email_verified?: boolean | null
          id: string
          status?: string
          updated_at?: string
        }
        Update: {
          avatar_url?: string | null
          created_at?: string
          display_name?: string | null
          email_verified?: boolean | null
          id?: string
          status?: string
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
          key?: string
          name?: string
          updated_at?: string
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
