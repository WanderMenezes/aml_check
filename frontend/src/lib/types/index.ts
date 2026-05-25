export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface DashboardTotals {
  screenings: number;
  critical: number;
  pending: number;
  review: number;
  high_risk_countries: number;
}

export interface ScreeningMatch {
  id: number;
  source_code: string;
  matched_name: string;
  score: number;
  risk_level: RiskLevel;
  aliases?: string[];
  details?: Record<string, unknown>;
  remarks: string;
}

export interface ScreeningRequest {
  id: number;
  risk_level: RiskLevel;
  status: string;
  recommendation: string;
  created_at: string;
  client: {
    full_name: string;
    country: string;
  };
  matches: ScreeningMatch[];
  grouped_matches?: Array<{
    key: string;
    url?: string;
    source_code?: string;
    title?: string;
    snippet?: string;
    matches: ScreeningMatch[];
  }>;
}

export interface AuditEvent {
  id: number;
  created_at: string;
  action: string;
  resource_type: string;
  resource_id: string;
  severity: string;
  status: string;
  ip_address?: string;
  user_email?: string;
}

export interface AlertItem {
  id: number;
  title: string;
  message: string;
  alert_type: string;
  is_read: boolean;
  created_at: string;
  screening?: number;
}

export interface SanctionsSource {
  id: number;
  code: string;
  name: string;
  enabled: boolean;
  health_status: string;
  last_synced_at: string | null;
  source_type: string;
  source_format: string;
  endpoint: string;
}

export interface RiskRule {
  id: number;
  name: string;
  condition_type: string;
  source_code: string;
  target_value: string;
  risk_level: RiskLevel;
  weight: number;
  enabled: boolean;
}

export interface UserAccount {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  is_active: boolean;
  preferred_language: string;
  permissions: string[];
}
