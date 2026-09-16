import { api, qs } from "./client";
import type {
  AuthOut, CaregiverCard, CaregiverProfileOut, CaregiverPublic, ContactMessage, ContactOut, Page,
  PatientCard, PatientCreateOut, ProductCard, ProductDetail, UserOut,
} from "./types";

export const AuthApi = {
  register: (body: { full_name: string; email: string; password: string; phone?: string; account_type: "family" | "caregiver" }) =>
    api.post<AuthOut>("/auth/register", body),
  login: (email: string, password: string) => api.post<AuthOut>("/auth/login", { email, password }),
  me: () => api.get<UserOut>("/users/me"),
  logout: (refresh_token: string) => api.post<void>("/auth/logout", { refresh_token }),
  uploadAvatar: (file: File) => api.upload<UserOut>("/users/me/avatar", file),
};

export const PatientsApi = {
  list: () => api.get<Page<PatientCard>>("/patients"),
  create: (body: { full_name: string; birth_date: string; sex?: string; conditions?: string[]; notes?: string }) =>
    api.post<PatientCreateOut>("/patients", body),
};

export const CaregiverApi = {
  myProfile: () => api.get<CaregiverProfileOut>("/caregiver/profile"),
  updateProfile: (body: Partial<{
    headline: string; bio: string; years_experience: number; specialties: string[];
    languages: string[]; zones: string[]; certifications: { name: string; issuer?: string; year?: number }[];
    is_listed: boolean;
  }>) => api.put<CaregiverProfileOut>("/caregiver/profile", body),
  contacts: () => api.get<Page<ContactMessage>>("/caregiver/contacts"),
};

export const MarketplaceApi = {
  search: (params: { q?: string; zone?: string; specialty?: string; language?: string; min_rating?: number }) =>
    api.get<Page<CaregiverCard>>(`/marketplace/caregivers${qs(params)}`),
  detail: (profileId: string) => api.get<CaregiverPublic>(`/marketplace/caregivers/${profileId}`),
  contact: (profileId: string, message?: string) =>
    api.post<ContactOut>(`/marketplace/caregivers/${profileId}/contact`, { message }),
  review: (profileId: string, rating: number, comment?: string) =>
    api.post<{ review_id: string }>(`/marketplace/caregivers/${profileId}/reviews`, { rating, comment }),
  products: (params: { category?: string; q?: string }) =>
    api.get<Page<ProductCard>>(`/marketplace/products${qs(params)}`),
  product: (id: string) => api.get<ProductDetail>(`/marketplace/products/${id}`),
};
