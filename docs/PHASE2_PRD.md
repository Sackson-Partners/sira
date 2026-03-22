# SIRA Platform — MVP Phase 2 PRD & Implementation Guide

| Field | Value |
|-------|-------|
| Platform | SIRA – Shipping / Supply Chain Intelligence & Risk Analytics |
| Sponsor | Energie Partners (EP) |
| Phase | MVP Phase 2 (Smart Contracts deferred to v2.5) |
| Version | 2.0.0 |
| Date | 18 March 2026 |
| Status | ACTIVE — Implementation In Progress |
| Confidentiality | CONFIDENTIAL — Internal Use Only |

---

## 1. Executive Summary

SIRA Phase 2 elevates the platform from a basic backend service into an end-to-end intelligence platform integrating:

- **Real-time telematics** via Flespi MQTT for trucks and trains
- **Vessel tracking** via MarineTraffic AIS API
- **AI Intelligence Engine** via Claude API (Anthropic) + OpenAI fallback
- **Strategic Intelligence Map** via Mapbox GL JS v3
- **Fleet Management** with scheduling, predictive maintenance, and driver management
- **Supabase Auth** — JWT, RBAC, Row-Level Security (multi-tenant)
- **Azure Container Apps** deployment in Resource Group `sira-rg`
- **Vercel** frontend hosting for Next.js 14

### Deferred to v2.5
Smart Contracts (Polygon/Hyperledger) are out of scope for Phase 2.

---

## 2. User Roles (RBAC)

| Role | Capabilities |
|------|-------------|
| `super_admin` | Full platform access, tenant management, API key management |
| `org_admin` | Manage users, fleets, routes within their organisation |
| `logistics_manager` | View control tower, manage shipments, receive AI alerts |
| `fleet_manager` | Schedule trips, manage vehicles, view maintenance alerts |
| `driver` | Mobile app only: routes, checkpoint confirmation |
| `client_read` | Read-only: tracking and reports for their shipments |
| `analyst` | AI insights, market feeds, export dashboards |

---

## 3. Primary Use Cases

### 3.1 Import Corridor — Oil: Port → Storage → Market
1. Tanker arrives → MarineTraffic AIS provides real-time ETA
2. Offloading begins → IoT sensors via Flespi confirm tank fill levels
3. Trucks dispatched → Flespi GPS tracks each truck in real time
4. AI predicts route delays → mobile app reroutes driver
5. Delivery confirmed → inventory updated in PostgreSQL
6. Logistics Manager views full chain on Strategic Map

### 3.2 Export Corridor — Iron / Bauxite: Mining Site → Port
1. Fleet management assigns trucks and trains
2. AI monitors vehicle health → alerts before breakdown
3. Commodity market feed monitored → AI recommends optimal dispatch timing
4. Train handoff at rail terminal → tracked
5. Port arrival predicted → vessel readiness checked via MarineTraffic
6. Export manifest generated → client receives milestone notifications

---

## 4. Architecture

### 4.1 Service Decomposition

| Service | Responsibility | Azure Target |
|---------|---------------|-------------|
| `api-gateway` | FastAPI main app (REST + WebSocket) | Container Apps, min 2 replicas |
| `telematics-worker` | Flespi MQTT ingestion | Container Apps, always-on |
| `maritime-worker` | MarineTraffic polling | Container Apps, cron scaling |
| `ai-worker` | AI Engine async processor | Container Apps, queue scaling |
| `postgres` | PostgreSQL 15 + TimescaleDB | Azure Database for PostgreSQL Flexible |
| `frontend` | Next.js 14 web app | Vercel (NOT Container Apps) |

### 4.2 Data Flow
```
[Trucks/IoT] --MQTT--> [Flespi] --webhook--> [telematics-worker]
[Vessels/AIS] --REST--> [MarineTraffic] -----------> [maritime-worker]
[Market APIs] --REST--> [Quandl/Refinitiv] ---------> [ai-worker]
                              |
                                                            v
                                                                                [api-gateway FastAPI]
                                                                                               [PostgreSQL + TimescaleDB]
                                                                                                                             |
                                                                                                                                                           v
                                                                                                                                                                              [ai-worker (Claude/OpenAI)]
                                                                                                                                                                                                 /                          \
                                                                                                                                                                                                     [Next.js / Vercel]              [React Native Mobile]
                                                                                                                                                                                                         [Strategic Map (Mapbox)]         [Driver Routing]
                                                                                                                                                                                                                            ^                          ^
                                                                                                                                                                                                                                               +------[Supabase Auth]-----+
                                                                                                                                                                                                                                               ```
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ---
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ## 5. Database Architecture
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ### 5.1 TimescaleDB Hypertables (time-series)
                                                                                                                                                                                                                                               - `telemetry_events` — GPS/CAN bus data from Flespi (7-day chunks, 30-day compression)
                                                                                                                                                                                                                                               - `vessel_positions` — AIS data from MarineTraffic
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ### 5.2 Core Relational Tables
                                                                                                                                                                                                                                               `organisations`, `users`, `vehicles`, `drivers`, `routes`, `trips`, `shipments`, `alerts`, `maintenance_records`, `maintenance_predictions`, `geofences`, `market_data`, `ai_insights`, `audit_log`
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ### 5.3 Supabase RLS
                                                                                                                                                                                                                                               All tables with `org_id` enforce Row-Level Security — users can only access their own organisation's data.
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ---
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ## 6. AI Intelligence Engine
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ### 6.1 Capabilities
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               | Capability | Model |
                                                                                                                                                                                                                                               |-----------|-------|
                                                                                                                                                                                                                                               | Delay Prediction | Claude claude-3-5-sonnet / GPT-4o |
                                                                                                                                                                                                                                               | Anomaly Detection | Rule engine + Claude interpretation |
                                                                                                                                                                                                                                               | Predictive Maintenance | Time-series trends + Claude explanation |
                                                                                                                                                                                                                                               | Route Optimisation | Claude reasoning + Mapbox Directions |
                                                                                                                                                                                                                                               | Market Intelligence | Claude synthesis of commodity feeds |
                                                                                                                                                                                                                                               | Risk Alerts | Claude structured JSON output |
                                                                                                                                                                                                                                               | Report Generation | Claude markdown generation |
                                                                                                                                                                                                                                               | Driver Coaching | Claude low-latency prompts |
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ### 6.2 Prompt Library Location
                                                                                                                                                                                                                                               `backend/app/prompts/` — YAML/Python prompt templates for all AI capabilities.
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ### 6.3 Fallback Strategy
                                                                                                                                                                                                                                               If Claude API returns an error, automatically fallback to OpenAI GPT-4o. AI results are advisory — the platform continues operating without AI.
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ---
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ## 7. Strategic Intelligence Map (Mapbox)
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               Built on Mapbox GL JS v3 (`frontend/components/StrategicMap.tsx`):
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               | Layer | Source | Update Strategy |
                                                                                                                                                                                                                                               |-------|--------|----------------|
                                                                                                                                                                                                                                               | Truck Fleet | Flespi via WebSocket | Push every 10s |
                                                                                                                                                                                                                                               | Vessel Positions | MarineTraffic AIS | Poll every 5min |
                                                                                                                                                                                                                                               | AI Risk Heatmap | AI Worker | Recalculate every 15min |
                                                                                                                                                                                                                                               | Alert Markers | PostgreSQL alerts | Real-time on new alert |
                                                                                                                                                                                                                                               | Market Data | Commodity APIs | Poll every 30min |
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ---
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ## 8. Deployment
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ### 8.1 Azure Infrastructure (`sira-rg`)
                                                                                                                                                                                                                                               - **Bicep template:** `infra/azure/main.bicep` (subscription scope)
                                                                                                                                                                                                                                               - **Module:** `infra/azure/modules/container-apps.bicep`
                                                                                                                                                                                                                                               - **Resource Group:** `sira-rg` (West Europe)
                                                                                                                                                                                                                                               - **Components:** ACR, Container Apps Environment, 4x Container Apps, Key Vault, Log Analytics
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ### 8.2 CI/CD Pipeline
                                                                                                                                                                                                                                               `.github/workflows/azure-deploy.yml`:
                                                                                                                                                                                                                                               1. Build Docker images for all 4 services
                                                                                                                                                                                                                                               2. Push to Azure Container Registry
                                                                                                                                                                                                                                               3. Deploy Bicep infrastructure (creates `sira-rg` idempotently)
                                                                                                                                                                                                                                               4. Update all Container Apps
                                                                                                                                                                                                                                               5. Smoke test API health endpoint
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ### 8.3 Vercel (Frontend)
                                                                                                                                                                                                                                               - Auto-deploys on merge to `main`
                                                                                                                                                                                                                                               - Preview deployments on every PR
                                                                                                                                                                                                                                               - Environment variables: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_MAPBOX_TOKEN`, `NEXT_PUBLIC_API_URL`
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ---
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ## 9. Security Controls
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               | Control | Implementation |
                                                                                                                                                                                                                                               |---------|---------------|
                                                                                                                                                                                                                                               | TLS/HTTPS | Azure Container Apps (managed) + Vercel (enforced) |
                                                                                                                                                                                                                                               | API Key Management | Azure Key Vault — never in code |
                                                                                                                                                                                                                                               | Data Encryption | AES-256 at rest |
                                                                                                                                                                                                                                               | Multi-tenant Isolation | Supabase RLS on all tables |
                                                                                                                                                                                                                                               | Rate Limiting | slowapi middleware (per-user + per-IP) |
                                                                                                                                                                                                                                               | Input Validation | Pydantic v2 on all endpoints |
                                                                                                                                                                                                                                               | Audit Logging | `audit_log` table with user_id, action, diff |
                                                                                                                                                                                                                                               | CORS | Restricted to known Vercel origins |
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ---
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ## 10. Non-Functional Requirements
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               | Metric | Target |
                                                                                                                                                                                                                                               |--------|--------|
                                                                                                                                                                                                                                               | API Response Time (p95) | < 200ms reads, < 500ms writes/AI |
                                                                                                                                                                                                                                               | Telemetry Throughput | > 10,000 events/second |
                                                                                                                                                                                                                                               | Map Refresh Latency | Truck position within 15s of GPS event |
                                                                                                                                                                                                                                               | AI Response (Claude) | < 3s alerts, < 10s reports |
                                                                                                                                                                                                                                               | Page Load (Vercel) | < 2s first contentful paint |
                                                                                                                                                                                                                                               | Target SLA | 99.5% uptime (production) |
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ---
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ## 11. Implementation Roadmap
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               | Sprint | Deliverables | Duration |
                                                                                                                                                                                                                                               |--------|-------------|---------|
                                                                                                                                                                                                                                               | S1–S2 | Foundation: repo, CI/CD, Docker, DB migrations, Supabase auth | 2 weeks |
                                                                                                                                                                                                                                               | S3–S4 | Telematics: Flespi MQTT, TimescaleDB, basic map | 2 weeks |
                                                                                                                                                                                                                                               | S5–S6 | Maritime: MarineTraffic AIS, vessel tracking, Mapbox maritime layer | 2 weeks |
                                                                                                                                                                                                                                               | S7–S8 | Fleet Management: vehicle/driver/trip CRUD, geofencing, mobile alpha | 2 weeks |
                                                                                                                                                                                                                                               | S9–S10 | AI Engine: prompt library, delay risk, anomaly, predictive maintenance | 2 weeks |
                                                                                                                                                                                                                                               | S11–S12 | Intelligence Map: full Mapbox SIM, all layers, WebSocket real-time | 2 weeks |
                                                                                                                                                                                                                                               | S13–S14 | Market Data: commodity feeds, market intelligence, analytics widgets | 2 weeks |
                                                                                                                                                                                                                                               | S15–S16 | Mobile App: routing, checkpoints, notifications, offline mode | 2 weeks |
                                                                                                                                                                                                                                               | S17–S18 | QA & Hardening: integration tests, load test, security audit | 2 weeks |
                                                                                                                                                                                                                                               | S19–S20 | Production Launch: go-live, monitoring, client onboarding | 2 weeks |
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ---
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ## 12. Required Secrets (Azure Key Vault + GitHub)
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               See `.env.phase2.example` for full list. Key secrets:
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               - `DATABASE_URL` — PostgreSQL connection string
                                                                                                                                                                                                                                               - `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` / `SUPABASE_JWT_SECRET`
                                                                                                                                                                                                                                               - `FLESPI_TOKEN` — Flespi API access token
                                                                                                                                                                                                                                               - `MARINE_TRAFFIC_API_KEY`
                                                                                                                                                                                                                                               - `CLAUDE_API_KEY` — Anthropic Claude
                                                                                                                                                                                                                                               - `OPENAI_API_KEY` — OpenAI fallback
                                                                                                                                                                                                                                               - `MAPBOX_SECRET_TOKEN`
                                                                                                                                                                                                                                               - `AZURE_CREDENTIALS` — GitHub Secret (JSON) for CI/CD
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               ---
                                                                                                                                                                                                                                               
                                                                                                                                                                                                                                               *This PRD supersedes and improves upon the original Phase 2 draft. Smart Contracts remain deferred to v2.5.*
