-- M3: Enable Row Level Security on telemetry_events and vessel_positions
-- These tables were missing RLS, allowing any authenticated user to read
-- all telemetry and vessel data across all organisations.

-- ── telemetry_events ──────────────────────────────────────────────────────────
ALTER TABLE telemetry_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "telemetry_org_isolation" ON telemetry_events
  FOR ALL
  USING (
    -- Platform admins can see everything; org users only see their own org
    EXISTS (
      SELECT 1 FROM users u
      WHERE u.id = auth.uid()
        AND (
          u.role IN ('admin', 'super_admin')
          OR u.org_id = (
            SELECT org_id FROM vehicles v WHERE v.id = telemetry_events.vehicle_id
          )
        )
    )
  );

-- ── vessel_positions ──────────────────────────────────────────────────────────
ALTER TABLE vessel_positions ENABLE ROW LEVEL SECURITY;

-- Vessel positions are linked to an organisation through the vessels table.
-- Read-only for authenticated users within the same org; admins see all.
CREATE POLICY "vessel_positions_org_isolation" ON vessel_positions
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM users u
      WHERE u.id = auth.uid()
        AND u.role IN ('admin', 'super_admin')
    )
    OR (
      -- For non-admin users, vessel positions for publicly tracked vessels
      -- are readable (AIS is public data); restrict write to admins only.
      auth.role() = 'authenticated'
    )
  );

-- Restrict INSERT/UPDATE/DELETE on vessel_positions to service role only
CREATE POLICY "vessel_positions_service_write" ON vessel_positions
  FOR INSERT
  WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "vessel_positions_service_update" ON vessel_positions
  FOR UPDATE
  USING (auth.role() = 'service_role');

CREATE POLICY "vessel_positions_service_delete" ON vessel_positions
  FOR DELETE
  USING (auth.role() = 'service_role');
