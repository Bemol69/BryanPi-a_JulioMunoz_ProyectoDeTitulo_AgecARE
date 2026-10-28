-- Esquema de la base de datos de la Consola de Administración
-- Generado desde los modelos SQLAlchemy del proyecto (dialecto PostgreSQL).
-- Referencia: backend/app/models.py y backend/alembic/versions

CREATE TABLE admin_sessions (
	id UUID NOT NULL, 
	admin_id UUID NOT NULL, 
	refresh_hash VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	rotated_to UUID, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(admin_id) REFERENCES admin_users (id)
);

CREATE INDEX ix_admin_sessions_admin_id ON admin_sessions (admin_id);

CREATE UNIQUE INDEX ix_admin_sessions_refresh_hash ON admin_sessions (refresh_hash);

CREATE TABLE admin_users (
	id UUID NOT NULL, 
	full_name VARCHAR(120) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	password_hash VARCHAR(255), 
	role VARCHAR(20) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	mfa_enabled BOOLEAN NOT NULL, 
	mfa_secret VARCHAR(64), 
	failed_attempts INTEGER NOT NULL, 
	locked_until TIMESTAMP WITH TIME ZONE, 
	invitation_expires_at TIMESTAMP WITH TIME ZONE, 
	last_login_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_admin_users_email ON admin_users (email);

CREATE TABLE audit_log (
	id UUID NOT NULL, 
	actor_id UUID, 
	actor_name VARCHAR(120), 
	actor_role VARCHAR(20), 
	action VARCHAR(60) NOT NULL, 
	entity_type VARCHAR(40), 
	entity_id UUID, 
	before JSONB, 
	after JSONB, 
	ip VARCHAR(45), 
	user_agent VARCHAR(300), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_audit_log_action ON audit_log (action);

CREATE INDEX ix_audit_log_actor_id ON audit_log (actor_id);

CREATE INDEX ix_audit_log_created_at ON audit_log (created_at);

CREATE INDEX ix_audit_log_entity_id ON audit_log (entity_id);

CREATE INDEX ix_audit_log_entity_type ON audit_log (entity_type);

CREATE TABLE content_items (
	id UUID NOT NULL, 
	type VARCHAR(10) NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	body TEXT NOT NULL, 
	tags JSONB NOT NULL, 
	status VARCHAR(12) NOT NULL, 
	tts_ready BOOLEAN NOT NULL, 
	publish_at TIMESTAMP WITH TIME ZONE, 
	published_at TIMESTAMP WITH TIME ZONE, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_by UUID, 
	created_by_name VARCHAR(120), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_content_items_status ON content_items (status);

CREATE INDEX ix_content_items_type ON content_items (type);

CREATE TABLE feature_usage_window (
	id UUID NOT NULL, 
	days_window INTEGER NOT NULL, 
	feature_key VARCHAR(50) NOT NULL, 
	role VARCHAR(12) NOT NULL, 
	users INTEGER NOT NULL, 
	computed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (days_window, feature_key, role), 
	FOREIGN KEY(feature_key) REFERENCES features (feature_key)
);

CREATE INDEX ix_feature_usage_window_days_window ON feature_usage_window (days_window);

CREATE INDEX ix_feature_usage_window_feature_key ON feature_usage_window (feature_key);

CREATE TABLE features (
	feature_key VARCHAR(50) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	applicable_roles JSONB NOT NULL, 
	expected_low BOOLEAN NOT NULL, 
	note VARCHAR(300), 
	sort_order INTEGER NOT NULL, 
	PRIMARY KEY (feature_key)
);

CREATE TABLE legal_versions (
	id UUID NOT NULL, 
	doc_type VARCHAR(10) NOT NULL, 
	semver VARCHAR(10) NOT NULL, 
	content_md TEXT NOT NULL, 
	changelog TEXT NOT NULL, 
	effective_date DATE NOT NULL, 
	requires_reacceptance BOOLEAN NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	published_at TIMESTAMP WITH TIME ZONE, 
	created_by UUID, 
	created_by_name VARCHAR(120), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (doc_type, semver)
);

CREATE INDEX ix_legal_versions_doc_type ON legal_versions (doc_type);

CREATE TABLE marketplace_caregiver_documents (
	id UUID NOT NULL, 
	caregiver_id UUID NOT NULL, 
	doc_type VARCHAR(20) NOT NULL, 
	file_url VARCHAR(500) NOT NULL, 
	original_filename VARCHAR(255) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	pending_file_url VARCHAR(500), 
	pending_filename VARCHAR(255), 
	review_note TEXT, 
	reviewed_at TIMESTAMP WITH TIME ZONE, 
	reviewed_by_name VARCHAR(120), 
	uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(caregiver_id) REFERENCES marketplace_caregivers (id)
);

CREATE INDEX ix_marketplace_caregiver_documents_caregiver_id ON marketplace_caregiver_documents (caregiver_id);

CREATE TABLE marketplace_caregiver_points_log (
	id UUID NOT NULL, 
	caregiver_id UUID NOT NULL, 
	points INTEGER NOT NULL, 
	reason VARCHAR(20) NOT NULL, 
	note VARCHAR(300), 
	review_id UUID, 
	awarded_by UUID, 
	awarded_by_name VARCHAR(120), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(caregiver_id) REFERENCES marketplace_caregivers (id)
);

CREATE INDEX ix_marketplace_caregiver_points_log_caregiver_id ON marketplace_caregiver_points_log (caregiver_id);

CREATE INDEX ix_marketplace_caregiver_points_log_created_at ON marketplace_caregiver_points_log (created_at);

CREATE TABLE marketplace_caregiver_reviews (
	id UUID NOT NULL, 
	caregiver_id UUID NOT NULL, 
	family_name VARCHAR(120) NOT NULL, 
	rating INTEGER NOT NULL, 
	comment TEXT, 
	job_reference VARCHAR(120), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(caregiver_id) REFERENCES marketplace_caregivers (id)
);

CREATE INDEX ix_marketplace_caregiver_reviews_caregiver_id ON marketplace_caregiver_reviews (caregiver_id);

CREATE TABLE marketplace_caregivers (
	id UUID NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	zone VARCHAR(80) NOT NULL, 
	specialties JSONB NOT NULL, 
	languages JSONB NOT NULL, 
	certifications_count INTEGER NOT NULL, 
	certifications_verified BOOLEAN NOT NULL, 
	rating_avg FLOAT, 
	reviews_count INTEGER NOT NULL, 
	is_engaged BOOLEAN NOT NULL, 
	status VARCHAR(12) NOT NULL, 
	status_reason TEXT, 
	internal_note TEXT, 
	submitted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	reviewed_by UUID, 
	reviewed_by_name VARCHAR(120), 
	PRIMARY KEY (id)
);

CREATE INDEX ix_marketplace_caregivers_status ON marketplace_caregivers (status);

CREATE INDEX ix_marketplace_caregivers_zone ON marketplace_caregivers (zone);

CREATE TABLE marketplace_products (
	id UUID NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	category VARCHAR(60) NOT NULL, 
	vendor VARCHAR(120) NOT NULL, 
	price_clp INTEGER, 
	external_url VARCHAR(500) NOT NULL, 
	image_url VARCHAR(500), 
	status VARCHAR(12) NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_marketplace_products_category ON marketplace_products (category);

CREATE INDEX ix_marketplace_products_status ON marketplace_products (status);

CREATE TABLE metrics_daily_users (
	day DATE NOT NULL, 
	signups INTEGER NOT NULL, 
	cancellations INTEGER NOT NULL, 
	downloads INTEGER NOT NULL, 
	active_users_eod INTEGER NOT NULL, 
	paying_users_eod INTEGER NOT NULL, 
	mrr_clp_eod INTEGER NOT NULL, 
	computed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (day)
);

CREATE TABLE metrics_hourly_users (
	id UUID NOT NULL, 
	ts_hour TIMESTAMP WITH TIME ZONE NOT NULL, 
	signups INTEGER NOT NULL, 
	cancellations INTEGER NOT NULL, 
	computed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_metrics_hourly_users_ts_hour ON metrics_hourly_users (ts_hour);

CREATE TABLE metrics_plan_snapshot (
	id UUID NOT NULL, 
	as_of DATE NOT NULL, 
	plan_code VARCHAR(12) NOT NULL, 
	users INTEGER NOT NULL, 
	price_clp INTEGER, 
	mrr_clp INTEGER NOT NULL, 
	monthly_churn FLOAT NOT NULL, 
	computed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (as_of, plan_code)
);

CREATE INDEX ix_metrics_plan_snapshot_as_of ON metrics_plan_snapshot (as_of);

CREATE TABLE moderation_queue (
	id UUID NOT NULL, 
	type VARCHAR(20) NOT NULL, 
	content JSONB NOT NULL, 
	author_user_id UUID, 
	author_name VARCHAR(120) NOT NULL, 
	author_role VARCHAR(12), 
	reported_by JSONB, 
	report_reason VARCHAR(300), 
	is_safety BOOLEAN NOT NULL, 
	status VARCHAR(10) NOT NULL, 
	reject_reason_code VARCHAR(15), 
	decision_note TEXT, 
	decided_by UUID, 
	decided_by_name VARCHAR(120), 
	decided_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_moderation_queue_created_at ON moderation_queue (created_at);

CREATE INDEX ix_moderation_queue_status ON moderation_queue (status);

CREATE INDEX ix_moderation_queue_type ON moderation_queue (type);

CREATE TABLE ops_component_state (
	key VARCHAR(30) NOT NULL, 
	status VARCHAR(15) NOT NULL, 
	uptime_30d FLOAT NOT NULL, 
	latency_p50_ms INTEGER, 
	latency_p95_ms INTEGER, 
	note VARCHAR(200), 
	checked_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (key)
);

CREATE TABLE ops_critical_process_state (
	key VARCHAR(40) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	chain VARCHAR(300) NOT NULL, 
	p95_seconds FLOAT NOT NULL, 
	success_24h FLOAT NOT NULL, 
	status VARCHAR(15) NOT NULL, 
	computed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (key)
);

CREATE TABLE ops_incidents (
	id UUID NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	component_key VARCHAR(30), 
	severity VARCHAR(15) NOT NULL, 
	status VARCHAR(15) NOT NULL, 
	description TEXT NOT NULL, 
	resolution TEXT, 
	is_maintenance BOOLEAN NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	created_by UUID, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_ops_incidents_started_at ON ops_incidents (started_at);

CREATE INDEX ix_ops_incidents_status ON ops_incidents (status);

CREATE TABLE ops_latency_window (
	id UUID NOT NULL, 
	"window" VARCHAR(4) NOT NULL, 
	component_key VARCHAR(30) NOT NULL, 
	p50_ms INTEGER NOT NULL, 
	p95_ms INTEGER NOT NULL, 
	sample_count INTEGER NOT NULL, 
	computed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE ("window", component_key)
);

CREATE INDEX ix_ops_latency_window_window ON ops_latency_window ("window");

CREATE TABLE role_activity_window (
	id UUID NOT NULL, 
	days_window INTEGER NOT NULL, 
	role VARCHAR(12) NOT NULL, 
	active_users INTEGER NOT NULL, 
	growth_8w FLOAT NOT NULL, 
	sessions_per_week FLOAT NOT NULL, 
	avg_session_seconds INTEGER NOT NULL, 
	retention_30d FLOAT NOT NULL, 
	computed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (days_window, role)
);

CREATE INDEX ix_role_activity_window_days_window ON role_activity_window (days_window);

CREATE TABLE role_weekly_active (
	id UUID NOT NULL, 
	week_start DATE NOT NULL, 
	role VARCHAR(12) NOT NULL, 
	active_users INTEGER NOT NULL, 
	computed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (week_start, role)
);

CREATE INDEX ix_role_weekly_active_week_start ON role_weekly_active (week_start);

CREATE TABLE support_ticket_replies (
	id UUID NOT NULL, 
	ticket_id UUID NOT NULL, 
	author_type VARCHAR(10) NOT NULL, 
	author_id UUID, 
	author_name VARCHAR(120) NOT NULL, 
	body TEXT NOT NULL, 
	internal BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES support_tickets (id)
);

CREATE INDEX ix_support_ticket_replies_created_at ON support_ticket_replies (created_at);

CREATE INDEX ix_support_ticket_replies_ticket_id ON support_ticket_replies (ticket_id);

CREATE TABLE support_tickets (
	id UUID NOT NULL, 
	number INTEGER NOT NULL, 
	subject VARCHAR(160) NOT NULL, 
	description TEXT NOT NULL, 
	requester_user_id UUID, 
	requester_name VARCHAR(120) NOT NULL, 
	requester_email VARCHAR(254) NOT NULL, 
	requester_role VARCHAR(12), 
	requester_plan VARCHAR(12), 
	category VARCHAR(20) NOT NULL, 
	priority VARCHAR(10) NOT NULL, 
	status VARCHAR(15) NOT NULL, 
	channel VARCHAR(10) NOT NULL, 
	assigned_to UUID, 
	first_response_at TIMESTAMP WITH TIME ZONE, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	csat_score INTEGER, 
	csat_comment TEXT, 
	requester_context JSONB, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(assigned_to) REFERENCES admin_users (id)
);

CREATE INDEX ix_support_tickets_category ON support_tickets (category);

CREATE INDEX ix_support_tickets_created_at ON support_tickets (created_at);

CREATE UNIQUE INDEX ix_support_tickets_number ON support_tickets (number);

CREATE INDEX ix_support_tickets_priority ON support_tickets (priority);

CREATE INDEX ix_support_tickets_requester_email ON support_tickets (requester_email);

CREATE INDEX ix_support_tickets_status ON support_tickets (status);

CREATE TABLE system_settings (
	key VARCHAR(80) NOT NULL, 
	value JSONB, 
	value_schema JSONB NOT NULL, 
	description VARCHAR(300) NOT NULL, 
	version INTEGER NOT NULL, 
	updated_by UUID, 
	updated_by_name VARCHAR(120), 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (key)
);
