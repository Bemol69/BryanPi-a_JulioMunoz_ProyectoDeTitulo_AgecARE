-- Esquema de la base de datos de el sitio público
-- Generado desde los modelos SQLAlchemy del proyecto (dialecto PostgreSQL).
-- Referencia: backend-general/app/models.py

CREATE TABLE caregiver_documents (
	id UUID NOT NULL, 
	caregiver_profile_id UUID NOT NULL, 
	doc_type VARCHAR(20) NOT NULL, 
	file_url VARCHAR(500) NOT NULL, 
	original_filename VARCHAR(255) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	pending_file_url VARCHAR(500), 
	pending_filename VARCHAR(255), 
	review_note TEXT, 
	reviewed_at TIMESTAMP WITH TIME ZONE, 
	uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(caregiver_profile_id) REFERENCES caregiver_profiles (id)
);

CREATE INDEX ix_caregiver_documents_caregiver_profile_id ON caregiver_documents (caregiver_profile_id);

CREATE TABLE caregiver_engagements (
	id UUID NOT NULL, 
	caregiver_profile_id UUID NOT NULL, 
	family_user_id UUID NOT NULL, 
	patient_id UUID, 
	status VARCHAR(10) NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	ended_at TIMESTAMP WITH TIME ZONE, 
	review_id UUID, 
	PRIMARY KEY (id), 
	FOREIGN KEY(caregiver_profile_id) REFERENCES caregiver_profiles (id), 
	FOREIGN KEY(family_user_id) REFERENCES users (id), 
	FOREIGN KEY(patient_id) REFERENCES patients (id)
);

CREATE INDEX ix_caregiver_engagements_caregiver_profile_id ON caregiver_engagements (caregiver_profile_id);

CREATE INDEX ix_caregiver_engagements_family_user_id ON caregiver_engagements (family_user_id);

CREATE INDEX ix_caregiver_engagements_status ON caregiver_engagements (status);

CREATE TABLE caregiver_profiles (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	headline VARCHAR(160), 
	bio TEXT, 
	years_experience INTEGER, 
	specialties JSONB NOT NULL, 
	languages JSONB NOT NULL, 
	zones JSONB NOT NULL, 
	certifications JSONB NOT NULL, 
	rating_avg FLOAT, 
	reviews_count INTEGER NOT NULL, 
	is_listed BOOLEAN NOT NULL, 
	is_featured BOOLEAN NOT NULL, 
	admin_status VARCHAR(12) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE UNIQUE INDEX ix_caregiver_profiles_user_id ON caregiver_profiles (user_id);

CREATE TABLE caregiver_reviews (
	id UUID NOT NULL, 
	caregiver_profile_id UUID NOT NULL, 
	author_user_id UUID NOT NULL, 
	author_name VARCHAR(120) NOT NULL, 
	rating INTEGER NOT NULL, 
	comment TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(caregiver_profile_id) REFERENCES caregiver_profiles (id), 
	FOREIGN KEY(author_user_id) REFERENCES users (id)
);

CREATE INDEX ix_caregiver_reviews_caregiver_profile_id ON caregiver_reviews (caregiver_profile_id);

CREATE TABLE chat_conversations (
	id UUID NOT NULL, 
	caregiver_profile_id UUID NOT NULL, 
	family_user_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	last_message_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_chat_pair UNIQUE (caregiver_profile_id, family_user_id), 
	FOREIGN KEY(caregiver_profile_id) REFERENCES caregiver_profiles (id), 
	FOREIGN KEY(family_user_id) REFERENCES users (id)
);

CREATE INDEX ix_chat_conversations_caregiver_profile_id ON chat_conversations (caregiver_profile_id);

CREATE INDEX ix_chat_conversations_family_user_id ON chat_conversations (family_user_id);

CREATE INDEX ix_chat_conversations_last_message_at ON chat_conversations (last_message_at);

CREATE TABLE chat_messages (
	id UUID NOT NULL, 
	conversation_id UUID NOT NULL, 
	sender_user_id UUID NOT NULL, 
	body VARCHAR(1000) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(conversation_id) REFERENCES chat_conversations (id), 
	FOREIGN KEY(sender_user_id) REFERENCES users (id)
);

CREATE INDEX ix_chat_messages_conversation_id ON chat_messages (conversation_id);

CREATE INDEX ix_chat_messages_created_at ON chat_messages (created_at);

CREATE TABLE contact_requests (
	id UUID NOT NULL, 
	caregiver_profile_id UUID NOT NULL, 
	family_user_id UUID NOT NULL, 
	message VARCHAR(500), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(caregiver_profile_id) REFERENCES caregiver_profiles (id), 
	FOREIGN KEY(family_user_id) REFERENCES users (id)
);

CREATE INDEX ix_contact_requests_caregiver_profile_id ON contact_requests (caregiver_profile_id);

CREATE INDEX ix_contact_requests_family_user_id ON contact_requests (family_user_id);

CREATE TABLE hire_requests (
	id UUID NOT NULL, 
	caregiver_profile_id UUID NOT NULL, 
	family_user_id UUID NOT NULL, 
	patient_id UUID, 
	message VARCHAR(500), 
	status VARCHAR(12) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	responded_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(caregiver_profile_id) REFERENCES caregiver_profiles (id), 
	FOREIGN KEY(family_user_id) REFERENCES users (id), 
	FOREIGN KEY(patient_id) REFERENCES patients (id)
);

CREATE INDEX ix_hire_requests_caregiver_profile_id ON hire_requests (caregiver_profile_id);

CREATE INDEX ix_hire_requests_family_user_id ON hire_requests (family_user_id);

CREATE INDEX ix_hire_requests_status ON hire_requests (status);

CREATE TABLE market_products (
	id UUID NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	category VARCHAR(20) NOT NULL, 
	description TEXT NOT NULL, 
	thumbnail_url VARCHAR(500), 
	photos JSONB NOT NULL, 
	price_range VARCHAR(60) NOT NULL, 
	external_url VARCHAR(500), 
	contact_info VARCHAR(200), 
	PRIMARY KEY (id)
);

CREATE INDEX ix_market_products_category ON market_products (category);

CREATE TABLE patient_members (
	id UUID NOT NULL, 
	patient_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	role VARCHAR(12) NOT NULL, 
	is_owner BOOLEAN NOT NULL, 
	joined_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(patient_id) REFERENCES patients (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_patient_members_patient_id ON patient_members (patient_id);

CREATE INDEX ix_patient_members_user_id ON patient_members (user_id);

CREATE TABLE patients (
	id UUID NOT NULL, 
	full_name VARCHAR(120) NOT NULL, 
	birth_date DATE NOT NULL, 
	sex VARCHAR(10), 
	photo_url VARCHAR(500), 
	conditions JSONB NOT NULL, 
	medication_allergies JSONB NOT NULL, 
	food_allergies JSONB NOT NULL, 
	notes TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE refresh_sessions (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	refresh_hash VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	rotated_to UUID, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE UNIQUE INDEX ix_refresh_sessions_refresh_hash ON refresh_sessions (refresh_hash);

CREATE INDEX ix_refresh_sessions_user_id ON refresh_sessions (user_id);

CREATE TABLE users (
	id UUID NOT NULL, 
	full_name VARCHAR(120) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	phone VARCHAR(30), 
	avatar_url VARCHAR(500), 
	locale VARCHAR(5) NOT NULL, 
	account_type VARCHAR(12) NOT NULL, 
	failed_attempts INTEGER NOT NULL, 
	locked_until TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);
