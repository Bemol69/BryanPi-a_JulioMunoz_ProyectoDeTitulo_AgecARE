import { api, qs } from "./client";
import type {
  AdoptionOut, AlertsOut, CaregiverDocumentOut, CaregiverOut, CaregiverRankingItem, CaregiverReviewOut,
  CommercialSummaryOut, FunnelOut, IncidentOut, LoginOutT, MarketingDashboardOut,
  MeOut, OpsStatusOut, Page, PlansOut, ProductOut, RolesSummaryOut,
  SupportSummaryOut, TicketOut,
} from "./types";

// ---- Auth ----
export const AuthApi = {
  login: (email: string, password: string) => api.post<LoginOutT>("/auth/login", { email, password }),
  me: () => api.get<MeOut>("/auth/me"),
  logout: (refresh_token: string) => api.post<void>("/auth/logout", { refresh_token }),
};

// ---- Marketplace / Fidelizacion (nuestro modulo) ----
export const MarketplaceApi = {
  listCaregivers: (params: { status?: string; zone?: string; q?: string; page?: number }) =>
    api.get<Page<CaregiverOut>>(`/marketplace/caregivers${qs({ ...params, page_size: 100 })}`),
  getCaregiver: (id: string) => api.get<CaregiverOut>(`/marketplace/caregivers/${id}`),
  deleteCaregiver: (id: string) => api.del<void>(`/marketplace/caregivers/${id}`),
  patchCaregiver: (id: string, body: { status?: string; reason?: string; internal_note?: string }) =>
    api.patch<CaregiverOut>(`/marketplace/caregivers/${id}`, body),
  reviewDocument: (id: string, docType: string, action: "approve" | "reject", note?: string) =>
    api.post<CaregiverDocumentOut>(`/marketplace/caregivers/${id}/documents/${docType}/review`, { action, note }),
  ranking: (params: { zone?: string; page?: number; page_size?: number }) =>
    api.get<Page<CaregiverRankingItem>>(`/marketplace/caregivers/ranking${qs(params)}`),
  awardPoints: (id: string, body: { points: number; reason: string; note?: string }) =>
    api.post(`/marketplace/caregivers/${id}/points`, body),
  createReview: (body: { caregiver_id: string; family_name: string; rating: number; comment?: string; job_reference?: string }) =>
    api.post<CaregiverReviewOut>("/marketplace/reviews", body),
  listReviews: (caregiverId: string, page = 1) =>
    api.get<Page<CaregiverReviewOut>>(`/marketplace/caregivers/${caregiverId}/reviews${qs({ page })}`),
  archiveReview: (reviewId: string, archived: boolean) =>
    api.patch<CaregiverReviewOut>(`/marketplace/reviews/${reviewId}`, { archived }),
  deleteReview: (reviewId: string) => api.del<void>(`/marketplace/reviews/${reviewId}`),
  listProducts: (params: { category?: string; status?: string; q?: string; page?: number }) =>
    api.get<Page<ProductOut>>(`/marketplace/products${qs(params)}`),
};

export const MarketingApi = {
  dashboardSummary: (days = 30) => api.get<MarketingDashboardOut>(`/marketing/dashboard/summary${qs({ days })}`),
};

// ---- Comercial ----
export const CommercialApi = {
  summary: (period: string) => api.get<CommercialSummaryOut>(`/metrics/commercial/summary${qs({ period })}`),
  plans: () => api.get<PlansOut>("/metrics/commercial/plans"),
  funnel: () => api.get<FunnelOut>("/metrics/commercial/funnel"),
};

// ---- Operativo ----
export const OpsApi = {
  status: () => api.get<OpsStatusOut>("/ops/status"),
  incidents: (days = 30) => api.get<Page<IncidentOut>>(`/ops/incidents${qs({ days })}`),
};

// ---- Usuarios y soporte ----
export const RolesApi = {
  summary: (days = 30) => api.get<RolesSummaryOut>(`/metrics/roles/summary${qs({ days })}`),
};
export const SupportApi = {
  summary: () => api.get<SupportSummaryOut>("/support/summary"),
  tickets: (params: { status?: string; page?: number }) => api.get<Page<TicketOut>>(`/support/tickets${qs(params)}`),
};

// ---- Funcionalidades ----
export const FeaturesApi = {
  adoption: (days = 30) => api.get<AdoptionOut>(`/metrics/features/adoption${qs({ days })}`),
  alerts: (days = 30, threshold = 0.15) => api.get<AlertsOut>(`/metrics/features/alerts${qs({ days, threshold })}`),
};

// ---- Moderacion ----
