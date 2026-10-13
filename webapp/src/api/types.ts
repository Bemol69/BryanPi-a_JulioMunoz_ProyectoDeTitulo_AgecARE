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
  caregiver_names: string[]; // cuidadoras con trabajo activo; vacío = sin cuidadora
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

export type CaregiverDocType = "id_card" | "background_check" | "certificate";

export type DocStatus = "pending" | "approved" | "rejected";

export interface CaregiverDocumentOut {
  doc_type: CaregiverDocType;
  file_url: string;
  original_filename: string;
  uploaded_at: string;
  status: DocStatus;
  pending_file_url: string | null; // cambio propuesto, esperando la decisión del staff
  pending_filename: string | null;
  review_note: string | null;
  reviewed_at: string | null;
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
  admin_status: "pending" | "approved" | "suspended";
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
  is_engaged: boolean; // tiene un trabajo activo con alguna familia
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
  hired_by_me: boolean;
  my_engagement_id: string | null;
  is_engaged: boolean;
  can_review: boolean; // la familia terminó un trabajo con ella y aún no lo reseñó
  conversation_id: string | null;
  my_request: { request_id: string; status: "pending" | "declined" | "unavailable"; created_at: string } | null;
}

export interface HireRequestOut {
  request_id: string;
  status: string;
  created_at: string;
  conversation_id: string | null;
}

export type HireRequestStatus = "pending" | "accepted" | "declined" | "cancelled" | "unavailable";

export interface ReceivedHireRequest {
  request_id: string;
  status: HireRequestStatus;
  created_at: string;
  responded_at: string | null;
  family_name: string;
  contact_name: string;
  patient_name: string | null;
  patient_age: number | null;
  conditions: string[];
  medication_allergies: string[];
  food_allergies: string[];
  message: string | null;
  conversation_id: string | null;
}

export interface Engagement {
  engagement_id: string;
  family_name: string;
  patient_name: string | null;
  started_at: string;
}

export interface ContactOut {
  contact_channel: "phone" | "whatsapp" | "email";
  contact_value: string;
  conversation_id: string | null;
}

export interface PatientDetail {
  patient_id: string;
  full_name: string;
  birth_date: string;
  sex: string | null;
  photo_url: string | null;
  conditions: string[];
  medication_allergies: string[];
  food_allergies: string[];
  notes: string | null;
  age: number;
  wellbeing_status: string;
  caregiver: { engagement_id: string; profile_id: string; full_name: string; photo_url: string | null; started_at: string } | null;
}

export interface ChatMessage {
  message_id: string;
  body: string;
  mine: boolean;
  created_at: string;
  expires_at: string;
}

export interface ChatSummary {
  conversation_id: string;
  other_name: string;
  other_photo_url: string | null;
  other_profile_id: string | null;
  last_message: { body: string; mine: boolean; created_at: string } | null;
  last_message_at: string;
}

export interface ChatDetail {
  conversation_id: string;
  other_name: string;
  other_photo_url: string | null;
  other_profile_id: string | null;
  retention_days: number;
  messages: ChatMessage[];
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
