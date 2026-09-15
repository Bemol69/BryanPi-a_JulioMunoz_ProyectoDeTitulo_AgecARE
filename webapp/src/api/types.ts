export type AccountType = "family" | "caregiver";
export type RoleType = "family" | "caregiver" | "doctor" | "elder";

export interface Membership {
  patient_id: string;
  patient_name: string;
  role: RoleType;
}

export interface UserOut {
  user_id: string;
  full_name: string;
  email: string;
  phone: string | null;
  avatar_url: string | null;
  locale: string;
  account_type: AccountType;
  memberships: Membership[];
}

export interface AuthOut {
  access_token: string;
  refresh_token: string;
  user: UserOut;
}

export interface Page<T> {
  items: T[];
  total: number;
}

export interface PatientCard {
  patient_id: string;
  full_name: string;
  photo_url: string | null;
  role: string;
  wellbeing_status: string;
}

export interface PatientCreateOut {
  patient_id: string;
  full_name: string;
  created_at: string;
}

export interface Certification {
  name: string;
  issuer: string | null;
  year: number | null;
}

export interface CaregiverProfileOut {
  profile_id: string;
  headline: string | null;
  bio: string | null;
  years_experience: number | null;
  specialties: string[];
  languages: string[];
  zones: string[];
  certifications: Certification[];
  rating_avg: number | null;
  reviews_count: number;
  is_listed: boolean;
  is_featured: boolean;
}

export interface CaregiverCard {
  profile_id: string;
  full_name: string;
  photo_url: string | null;
  headline: string | null;
  years_experience: number | null;
  specialties: string[];
  zones: string[];
  rating_avg: number | null;
  reviews_count: number;
  is_featured: boolean;
}

export interface Review {
  review_id: string;
  rating: number;
  comment: string | null;
  author_name: string;
  created_at: string;
}

export interface CaregiverPublic extends CaregiverProfileOut {
  full_name: string;
  photo_url: string | null;
  reviews: Review[];
}

export interface ContactOut {
  contact_channel: "phone" | "whatsapp" | "email";
  contact_value: string;
}

export interface ContactMessage {
  contact_id: string;
  family_name: string;
  family_email: string;
  message: string | null;
  created_at: string;
}

export type ProductCategory = "mobility" | "monitoring" | "home_safety" | "daily_care";

export interface ProductCard {
  product_id: string;
  name: string;
  category: ProductCategory;
  thumbnail_url: string | null;
  price_range: string;
}

export interface ProductDetail {
  product_id: string;
  name: string;
  category: ProductCategory;
  description: string;
  photos: string[];
  price_range: string;
  external_url: string | null;
  contact_info: string | null;
}
