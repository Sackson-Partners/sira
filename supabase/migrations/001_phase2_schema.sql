-- =============================================================================
-- SIRA Platform — Phase 2 Schema Migration
-- Supabase PostgreSQL + TimescaleDB
-- Authentication: Supabase Auth (JWT + RBAC + Row Level Security)
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =============================================================================
-- ORGANISATIONS (Multi-tenant)
-- =============================================================================
CREATE TABLE IF NOT EXISTS organisations (
      id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      name        TEXT NOT NULL,
      slug        TEXT UNIQUE NOT NULL,
      plan        TEXT DEFAULT 'starter' CHECK (plan IN ('starter','professional','enterprise')),
      settings    JSONB DEFAULT '{}',
      active      BOOLEAN DEFAULT TRUE,
      created_at  TIMESTAMPTZ DEFAULT NOW(),
      updated_at  TIMESTAMPTZ DEFAULT NOW()
  );

-- =============================================================================
-- USERS (linked to Supabase auth.users)
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
      id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
      org_id      UUID REFERENCES organisations(id),
      role        TEXT NOT NULL DEFAULT 'client_read'
                  CHECK (role IN ('super_admin','org_admin','logistics_manager','fleet_manager','driver','client_read','analyst')),
      full_name   TEXT,
      phone       TEXT,
      avatar_url  TEXT,
      active      BOOLEAN DEFAULT TRUE,
      created_at  TIMESTAMPTZ DEFAULT NOW(),
      updated_at  TIMESTAMPTZ DEFAULT NOW()
  );

-- Trigger: auto-create user record on Supabase Auth signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO users (id, full_name)
    VALUES (NEW.id, NEW.raw_user_meta_data->>'full_name')
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- =============================================================================
-- VEHICLES
-- =============================================================================
CREATE TABLE IF NOT EXISTS vehicles (
      id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      org_id          UUID REFERENCES organisations(id) NOT NULL,
      plate           TEXT NOT NULL,
      type            TEXT CHECK (type IN ('truck','train','vessel','other')),
      make            TEXT,
      model           TEXT,
      year            INTEGER,
      status          TEXT DEFAULT 'idle'
                      CHECK (status IN ('idle','active','maintenance','offline','alert')),
      device_id       TEXT,                    -- Flespi device ident
    assigned_driver UUID,
      current_trip_id UUID,
      last_seen_at    TIMESTAMPTZ,
      metadata        JSONB DEFAULT '{}',
      created_at      TIMESTAMPTZ DEFAULT NOW()
  );

-- =============================================================================
-- DRIVERS
-- =============================================================================
CREATE TABLE IF NOT EXISTS drivers (
      id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id         UUID REFERENCES users(id),
      org_id          UUID REFERENCES organisations(id),
      licence_no      TEXT UNIQUE,
      licence_expiry  DATE,
      hours_driven    REAL DEFAULT 0,
      perf_score      REAL DEFAULT 100 CHECK (perf_score BETWEEN 0 AND 100),
      active          BOOLEAN DEFAULT TRUE,
      created_at      TIMESTAMPTZ DEFAULT NOW()
  );

-- =============================================================================
-- ROUTES
-- =============================================================================
CREATE TABLE IF NOT EXISTS routes (
      id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      org_id          UUID REFERENCES organisations(id),
      name            TEXT NOT NULL,
      origin          TEXT NOT NULL,
      destination     TEXT NOT NULL,
      waypoints       JSONB DEFAULT '[]',
      distance_km     REAL,
      est_duration_h  REAL,
      restrictions    JSONB DEFAULT '{}',
      active          BOOLEAN DEFAULT TRUE,
      created_at      TIMESTAMPTZ DEFAULT NOW()
  );

-- =============================================================================
-- TRIPS
-- =============================================================================
CREATE TABLE IF NOT EXISTS trips (
      id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      org_id          UUID REFERENCES organisations(id),
      vehicle_id      UUID REFERENCES vehicles(id),
      driver_id       UUID REFERENCES drivers(id),
      route_id        UUID REFERENCES routes(id),
      cargo_type      TEXT,
      cargo_quantity  REAL,
      cargo_unit      TEXT DEFAULT 'tonnes',
      status          TEXT DEFAULT 'scheduled'
                      CHECK (status IN ('scheduled','departed','in_transit','delayed','arrived','cancelled')),
      origin          TEXT,
      destination     TEXT,
      scheduled_start TIMESTAMPTZ,
      actual_start    TIMESTAMPTZ,
      scheduled_eta   TIMESTAMPTZ,
      actual_arrival  TIMESTAMPTZ,
      ai_risk_level   TEXT CHECK (ai_risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')),
      ai_delay_est_h  REAL,
      notes           TEXT,
      metadata        JSONB DEFAULT '{}',
      created_at      TIMESTAMPTZ DEFAULT NOW(),
      updated_at      TIMESTAMPTZ DEFAULT NOW()
  );

-- =============================================================================
-- TELEMETRY EVENTS (TimescaleDB hypertable)
-- =============================================================================
CREATE TABLE IF NOT EXISTS telemetry_events (
      timestamp       TIMESTAMPTZ NOT NULL,
      device_id       TEXT NOT NULL,
      vehicle_id      UUID,
      lat             DOUBLE PRECISION,
      lon             DOUBLE PRECISION,
      speed           REAL,
      heading         REAL,
      fuel_level      REAL,
      engine_temp     REAL,
      odometer        REAL,
      ignition        BOOLEAN,
      alarm_event_id  INTEGER,
      raw_payload     JSONB
  );

SELECT create_hypertable('telemetry_events', 'timestamp',
      chunk_time_interval => INTERVAL '7 days',
      if_not_exists => TRUE);

ALTER TABLE telemetry_events SET (timescaledb.compress = true);
SELECT add_compression_policy('telemetry_events', INTERVAL '30 days', if_not_exists => TRUE);

-- Index for fast vehicle lookups
CREATE INDEX IF NOT EXISTS idx_telemetry_vehicle ON telemetry_events (vehicle_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_device ON telemetry_events (device_id, timestamp DESC);

-- =============================================================================
-- VESSEL POSITIONS (TimescaleDB hypertable — AIS data)
-- =============================================================================
CREATE TABLE IF NOT EXISTS vessel_positions (
      timestamp       TIMESTAMPTZ NOT NULL,
      mmsi            TEXT NOT NULL,
      vessel_name     TEXT,
      lat             DOUBLE PRECISION,
      lon             DOUBLE PRECISION,
      speed           REAL,
      heading         REAL,
      status          TEXT,
      destination     TEXT,
      eta             TIMESTAMPTZ,
      raw_payload     JSONB
  );

SELECT create_hypertable('vessel_positions', 'timestamp',
      chunk_time_interval => INTERVAL '7 days',
      if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_vessel_mmsi ON vessel_positions (mmsi, timestamp DESC);

-- =============================================================================
-- SHIPMENTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS shipments (
      id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      org_id          UUID REFERENCES organisations(id),
      type            TEXT CHECK (type IN ('import','export')),
      commodity       TEXT,
      quantity_tonnes REAL,
      origin          TEXT,
      destination     TEXT,
      status          TEXT DEFAULT 'planned',
      vessel_mmsi     TEXT,
      trip_ids        UUID[],
      consignee       TEXT,
      customs_ref     TEXT,
      eta             TIMESTAMPTZ,
      metadata        JSONB DEFAULT '{}',
      created_at      TIMESTAMPTZ DEFAULT NOW()
  );

-- =============================================================================
-- ALERTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS alerts (
      id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      org_id          UUID REFERENCES organisations(id),
      vehicle_id      UUID REFERENCES vehicles(id),
      trip_id         UUID REFERENCES trips(id),
      type            TEXT NOT NULL,
      severity        TEXT CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
      message         TEXT,
      ai_analysis     TEXT,
      resolved        BOOLEAN DEFAULT FALSE,
      resolved_at     TIMESTAMPTZ,
      resolved_by     UUID REFERENCES users(id),
      created_at      TIMESTAMPTZ DEFAULT NOW()
  );

-- =============================================================================
-- MAINTENANCE RECORDS
-- =============================================================================
CREATE TABLE IF NOT EXISTS maintenance_records (
      id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      vehicle_id      UUID REFERENCES vehicles(id),
      service_type    TEXT,
      mileage_at_svc  REAL,
      cost            REAL,
      currency        TEXT DEFAULT 'USD',
      technician      TEXT,
      notes           TEXT,
      next_service_km REAL,
      next_service_dt DATE,
      serviced_at     TIMESTAMPTZ,
      created_at      TIMESTAMPTZ DEFAULT NOW()
  );

-- =============================================================================
-- MAINTENANCE PREDICTIONS (AI-generated)
-- =============================================================================
CREATE TABLE IF NOT EXISTS maintenance_predictions (
      id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      vehicle_id      UUID REFERENCES vehicles(id),
      predicted_at    TIMESTAMPTZ DEFAULT NOW(),
      urgency         TEXT CHECK (urgency IN ('LOW','MEDIUM','HIGH','CRITICAL')),
      failure_type    TEXT,
      days_to_failure INTEGER,
      ai_reasoning    TEXT,
      resolved        BOOLEAN DEFAULT FALSE,
      resolved_at     TIMESTAMPTZ
  );

-- =============================================================================
-- GEOFENCES
-- =============================================================================
CREATE TABLE IF NOT EXISTS geofences (
      id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      org_id      UUID REFERENCES organisations(id),
      name        TEXT NOT NULL,
      type        TEXT CHECK (type IN ('port','mine','storage','depot','restricted','corridor')),
      geometry    JSONB NOT NULL,
      active      BOOLEAN DEFAULT TRUE,
      created_at  TIMESTAMPTZ DEFAULT NOW()
  );

-- =============================================================================
-- MARKET DATA
-- =============================================================================
CREATE TABLE IF NOT EXISTS market_data (
      id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      commodity   TEXT NOT NULL,
      price       REAL NOT NULL,
      currency    TEXT DEFAULT 'USD',
      unit        TEXT DEFAULT 'tonne',
      source      TEXT,
      captured_at TIMESTAMPTZ DEFAULT NOW()
  );

-- =============================================================================
-- AI INSIGHTS (stored prompt/response pairs)
-- =============================================================================
CREATE TABLE IF NOT EXISTS ai_insights (
      id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      org_id          UUID REFERENCES organisations(id),
      context_type    TEXT,
      context_id      UUID,
      model           TEXT,
      prompt_tokens   INTEGER,
      completion_tokens INTEGER,
      risk_level      TEXT,
      delay_est_h     REAL,
      response        JSONB,
      created_at      TIMESTAMPTZ DEFAULT NOW()
  );

-- =============================================================================
-- AUDIT LOG
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
      id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id     UUID REFERENCES users(id),
      action      TEXT NOT NULL,
      table_name  TEXT,
      record_id   UUID,
      diff        JSONB,
      ip_address  INET,
      created_at  TIMESTAMPTZ DEFAULT NOW()
  );

-- =============================================================================
-- ROW LEVEL SECURITY POLICIES (Supabase RLS)
-- =============================================================================

ALTER TABLE organisations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE vehicles ENABLE ROW LEVEL SECURITY;
ALTER TABLE drivers ENABLE ROW LEVEL SECURITY;
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE shipments ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE geofences ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_insights ENABLE ROW LEVEL SECURITY;

-- Users can only see their own org
CREATE POLICY "users_own_org" ON users
    FOR ALL USING (
          org_id = (SELECT org_id FROM users WHERE id = auth.uid())
      );

CREATE POLICY "vehicles_own_org" ON vehicles
    FOR ALL USING (
          org_id = (SELECT org_id FROM users WHERE id = auth.uid())
      );

CREATE POLICY "trips_own_org" ON trips
    FOR ALL USING (
          org_id = (SELECT org_id FROM users WHERE id = auth.uid())
      );

CREATE POLICY "alerts_own_org" ON alerts
    FOR ALL USING (
          org_id = (SELECT org_id FROM users WHERE id = auth.uid())
      );

CREATE POLICY "shipments_own_org" ON shipments
    FOR ALL USING (
          org_id = (SELECT org_id FROM users WHERE id = auth.uid())
      );

CREATE POLICY "ai_insights_own_org" ON ai_insights
    FOR ALL USING (
          org_id = (SELECT org_id FROM users WHERE id = auth.uid())
      );

-- Market data is globally readable (no org scoping)
CREATE POLICY "market_data_read_all" ON market_data
    FOR SELECT USING (TRUE);

-- =============================================================================
-- INDEXES for performance
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_vehicles_org ON vehicles(org_id);
CREATE INDEX IF NOT EXISTS idx_vehicles_status ON vehicles(status);
CREATE INDEX IF NOT EXISTS idx_trips_org ON trips(org_id);
CREATE INDEX IF NOT EXISTS idx_trips_status ON trips(status);
CREATE INDEX IF NOT EXISTS idx_trips_vehicle ON trips(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_alerts_org ON alerts(org_id);
CREATE INDEX IF NOT EXISTS idx_alerts_unresolved ON alerts(org_id) WHERE resolved = FALSE;
CREATE INDEX IF NOT EXISTS idx_shipments_org ON shipments(org_id);
CREATE INDEX IF NOT EXISTS idx_market_data_commodity ON market_data(commodity, captured_at DESC);
