export type AdminRole = "admin" | "analyst" | "support" | "editor" | "moderator";

export interface AdminOut {
  id: string;
  full_name: string;
  email: string;
  role: AdminRole;
  mfa_enabled: boolean;
}

export interface MeOut extends AdminOut {
  permissions: string[];
  last_login_at: string | null;
}

export interface LoginOutT {
  access_token: string;
  refresh_token: string;
  admin: AdminOut;
}

export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface ApiErrorBody {
  error: { code: string; message: string; details: unknown; request_id: string };
}

// ---- Marketplace / Fidelizacion ----
export type CaregiverStatus = "pending" | "approved" | "suspended";

export interface CaregiverOut {
  caregiver_id: string;
  name: string;
  zone: string;
  specialties: string[];
  languages: string[];
  certifications_count: number;
  rating_avg: number | null;
  reviews_count: number;
  status: CaregiverStatus;
  submitted_at: string;
  reviewed_by_name: string | null;
  internal_note?: string | null;
}

export interface CaregiverRankingItem {
  rank: number;
  caregiver_id: string;
  name: string;
  zone: string;
  points: number;
  rating_avg: number | null;
  reviews_count: number;
  status: CaregiverStatus;
}

export interface CaregiverReviewOut {
  id: string;
  caregiver_id: string;
  family_name: string;
  rating: number;
  comment: string | null;
  job_reference: string | null;
  points_awarded: number;
  created_at: string;
}

export interface TopCaregiverOut {
  caregiver_id: string;
  name: string;
  zone: string;
  points: number;
  rating_avg: number | null;
}

export interface MarketingDashboardOut {
  active_caregivers: number;
  pending_caregivers: number;
  avg_points: number;
  avg_rating: number | null;
  reviews_last_30d: number;
  points_awarded_last_30d: number;
  top5: TopCaregiverOut[];
}

export interface ProductOut {
  id: string;
  name: string;
  category: string;
  vendor: string;
  price_clp: number | null;
  external_url: string;
  image_url: string | null;
  status: "draft" | "published" | "archived";
  updated_at: string;
}

// ---- Comercial ----
export interface PeriodOut { key: string; start_date: string; end_date: string }
export interface CommercialSummaryOut {
  period: PeriodOut;
  downloads: number;
  new_users: number;
  churned_users: number;
  churn_rate: number;
  active_users: number;
  paying_users: number;
  paying_share: number;
  mrr_clp: number;
  deltas: { new_users_pct: number | null; mrr_pct: number | null; active_users_pct: number | null };
  computed_at: string;
}
export interface PlanRow {
  plan_code: string; name: string; users: number; share: number;
  price_clp: number | null; mrr_clp: number; monthly_churn: number;
}
export interface PlansOut {
  as_of: string; plans: PlanRow[];
  totals: { users: number; mrr_clp: number; monthly_churn: number };
  computed_at: string;
}
export interface FunnelStage { stage: string; name: string; users: number; rate_vs_first: number }
export interface FunnelOut { as_of: string; stages: FunnelStage[]; computed_at: string }

// ---- Operativo ----
export interface ComponentStateOut {
  key: string; name: string; status: "operational" | "degraded" | "outage";
  uptime_30d: number; latency_p50_ms: number | null; latency_p95_ms: number | null; note: string | null;
}
export interface OpsStatusOut { components: ComponentStateOut[]; overall: string; checked_at: string }
export interface IncidentOut {
  id: string; title: string; component_key: string | null; severity: string; status: string;
  description: string; resolution: string | null; is_maintenance: boolean;
  started_at: string; resolved_at: string | null;
}

// ---- Usuarios y soporte ----
export interface RoleSummaryRow {
  role: string; active_users: number; growth_8w: number; sessions_per_week: number;
  avg_session_seconds: number; retention_30d: number;
}
export interface RolesSummaryOut { days: number; roles: RoleSummaryRow[]; computed_at: string }
export interface TicketOut {
  id: string; number: number; subject: string;
  requester: { user_id: string | null; name: string; role: string | null; email: string };
  category: string; priority: string; status: string;
  assigned_to: { admin_id: string; name: string } | null;
  channel: string; created_at: string; updated_at: string; first_response_at: string | null;
}
export interface SupportSummaryOut {
  open: number; in_progress: number; waiting_user: number; resolved_30d: number;
  first_response_hours_avg: number; csat_avg: number | null; csat_count: number;
  deltas: { open_wow: number; resolved_mom_pct: number | null; first_response_mom_hours: number | null };
  computed_at: string;
}

// ---- Funcionalidades ----
export interface FeatureAdoptionRow { feature_key: string; name: string; adoption: (number | null)[] }
export interface AdoptionOut { days: number; roles: string[]; features: FeatureAdoptionRow[]; computed_at: string }
export interface AdoptionAlert {
  feature_key: string; name: string; roles: string[]; adoption: number[];
  expected_low: boolean; note: string | null;
}
export interface AlertsOut { threshold: number; alerts: AdoptionAlert[]; computed_at: string }

// ---- Moderacion ----
export interface ModerationItemOut {
  id: string; type: string; content: Record<string, unknown>; author: Record<string, unknown>;
  reported_by: Record<string, unknown> | null; report_reason: string | null;
  status: "pending" | "approved" | "rejected"; decided_by_name: string | null;
  decided_at: string | null; created_at: string;
}

// ---- Contenido ----
export interface ContentItemOut {
  id: string; type: string; title: string; body: string; audio_available: boolean;
  tags: string[]; status: string; publish_at: string | null; published_at: string | null;
  created_by_name: string | null; updated_at: string;
}
