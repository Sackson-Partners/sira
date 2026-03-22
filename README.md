# SIRA Platform
**Shipping / Supply Chain Intelligence & Risk Analytics**
*Digital Control Tower · Fleet & Market Intelligence · AI Analytics*

Sponsored by **Energie Partners (EP)**  |  Version: **2.0.0 (MVP Phase 2)**  |  Status: **Active Development**

[![Deploy to Azure Container Apps](https://github.com/Sackson-Partners/sira/actions/workflows/azure-deploy.yml/badge.svg)](https://github.com/Sackson-Partners/sira/actions/workflows/azure-deploy.yml)
[![Frontend](https://img.shields.io/badge/Frontend-Vercel-black)](https://sira-teal.vercel.app)

---

## Overview

SIRA is a full-stack Digital Control Tower platform for logistics operators managing commodity imports and exports (oil, iron, bauxite) across road, rail, and maritime transport modes. Phase 2 elevates the platform with real-time telematics, vessel tracking, AI analytics, and geospatial visualization.

### Key Capabilities (Phase 2)
- **Real-time GPS & IoT Telematics** — Flespi MQTT/REST for trucks and trains
- - **Maritime Vessel Tracking** — MarineTraffic AIS API for tankers and cargo ships
  - - **AI Intelligence Engine** — Claude API (Anthropic) + OpenAI: delay prediction, anomaly detection, predictive maintenance, market intelligence
    - - **Strategic Intelligence Map** — Mapbox GL JS v3: real-time fleet + vessel + AI risk heatmap
      - - **Fleet Management** — Vehicle registry, trip scheduling, route optimization, driver management
        - - **Secure Multi-Tenant Auth** — Supabase Auth with JWT, RBAC, Row-Level Security
          - - **Cloud Deployment** — Docker → Azure Container Apps (Resource Group: `sira-rg`) + Vercel (frontend)
           
            - ---

            ## Live Deployment
            - **Frontend (Vercel):** https://sira-teal.vercel.app
            - - **Backend API (Azure Container Apps):** Deployed to resource group `sira-rg` in `westeurope`
              - - **API Docs:** `{API_URL}/docs`
               
                - ---

                ## Tech Stack

                | Domain | Technology | Version |
                |--------|-----------|---------|
                | Backend | Python + FastAPI | 3.12 / 0.115+ |
                | Database | PostgreSQL + TimescaleDB | 15+ / 2.x |
                | Auth | Supabase Auth (JWT + RLS) | Latest |
                | Telematics | Flespi API + MQTT | Latest |
                | Maritime | MarineTraffic AIS API | v2 |
                | AI / LLM | Claude API (claude-3-5-sonnet) | Latest |
                | AI Fallback | OpenAI GPT-4o | Latest |
                | Maps | Mapbox GL JS | v3 |
                | Frontend | Next.js 14 (App Router) | 14.x |
                | Mobile | React Native (Expo) | SDK 51 |
                | Deployment | Docker + Azure Container Apps | Latest |
                | Frontend Host | Vercel | Pro |
                | CI/CD | GitHub Actions | Latest |
                | Secrets | Azure Key Vault | Latest |

                ---

                ## Repository Structure

                ```
                sira/
                ├── backend/                    # Python FastAPI backend
                │   ├── app/
                │   │   ├── core/               # config, db, auth (Supabase JWT)
                │   │   ├── models/             # SQLAlchemy 2.0 ORM models (Phase 2)
                │   │   ├── routers/            # API route handlers (fleet, maritime, AI)
                │   │   ├── services/           # Business logic
                │   │   └── prompts/            # AI prompt library (delay, maintenance, market)
                │   ├── services/
                │   │   ├── telematics/         # Flespi MQTT ingestion worker + Dockerfile
                │   │   ├── maritime/           # MarineTraffic polling worker + Dockerfile
                │   │   └── ai/                 # AI intelligence engine worker + Dockerfile
                │   ├── Dockerfile              # API Gateway container
                │   └── requirements.txt        # Phase 2 dependencies
                ├── frontend/                   # Next.js 14 web dashboard (Vercel)
                │   ├── app/                    # App Router pages
                │   ├── components/
                │   │   └── StrategicMap.tsx    # Mapbox Strategic Intelligence Map
                │   ├── lib/
                │   │   └── supabase.ts         # Supabase auth client + RBAC helpers
                │   └── middleware.ts           # Next.js route protection (Supabase)
                ├── supabase/
                │   ├── config.toml             # Supabase local config
                │   └── migrations/
                │       └── 001_phase2_schema.sql  # Full Phase 2 schema (TimescaleDB, RLS)
                ├── infra/azure/
                │   ├── main.bicep              # Subscription-scope: creates sira-rg
                │   └── modules/
                │       └── container-apps.bicep   # ACR, Container Apps, Key Vault, Log Analytics
                ├── .github/workflows/
                │   ├── ci.yml                  # PR lint, test, security scan
                │   ├── azure-deploy.yml        # Build images → Push ACR → Deploy sira-rg
                │   └── deploy.yml              # Legacy deployment
                ├── docker-compose.phase2.yml   # Full local dev stack (all microservices)
                └── .env.phase2.example         # Environment variable template
                ```

                ---

                ## Quick Start (Local Development)

                ### Prerequisites
                - Python 3.12+
                - - Node.js 20+
                  - - Docker + Docker Compose
                    - - Supabase account (or local Supabase CLI)
                      - - API keys: Flespi, MarineTraffic, Claude, Mapbox
                       
                        - ### 1. Clone & configure
                        - ```bash
                          git clone https://github.com/Sackson-Partners/sira.git
                          cd sira
                          cp .env.phase2.example .env.phase2
                          # Edit .env.phase2 with your API keys and credentials
                          ```

                          ### 2. Start full Phase 2 stack
                          ```bash
                          docker-compose -f docker-compose.phase2.yml up -d
                          ```

                          Services started:
                          - `sira-postgres` — PostgreSQL 15 + TimescaleDB on port 5432
                          - - `sira-redis` — Redis 7 on port 6379
                            - - `sira-api` — FastAPI gateway on port 8000
                              - - `sira-telematics` — Flespi MQTT ingestion worker
                                - - `sira-maritime` — MarineTraffic polling worker
                                  - - `sira-ai` — AI intelligence engine worker
                                   
                                    - ### 3. Run Supabase migrations
                                    - ```bash
                                      # Using Supabase CLI
                                      supabase db push --local
                                      # OR manually
                                      psql $DATABASE_URL < supabase/migrations/001_phase2_schema.sql
                                      ```

                                      ### 4. Start frontend (Next.js / Vercel)
                                      ```bash
                                      cd frontend
                                      npm install
                                      npm run dev
                                      # Frontend: http://localhost:3000
                                      # API Docs: http://localhost:8000/docs
                                      ```

                                      ---

                                      ## Azure Deployment (sira-rg)

                                      ### GitHub Actions (recommended)
                                      Push to `main` branch triggers automatic deployment to Azure Container Apps in resource group `sira-rg`.

                                      **Required GitHub Secrets:**
                                      ```
                                      AZURE_CREDENTIALS        # az ad sp create-for-rbac output
                                      AZURE_SUBSCRIPTION_ID    # Your Azure subscription ID
                                      AZURE_SUBSCRIPTION_SUFFIX # Unique string for ACR name
                                      ```

                                      ### Manual Deployment
                                      ```bash
                                      # 1. Create resource group and deploy infrastructure
                                      az login
                                      az deployment sub create \
                                        --location westeurope \
                                        --template-file infra/azure/main.bicep \
                                        --parameters location=westeurope environment=prod

                                      # 2. Build and push Docker images
                                      ACR_NAME=siracr$(az account show --query id -o tsv | head -c 8)
                                      az acr login --name $ACR_NAME

                                      docker build -t $ACR_NAME.azurecr.io/sira-api:latest -f backend/Dockerfile ./backend
                                      docker push $ACR_NAME.azurecr.io/sira-api:latest

                                      # 3. Update container apps
                                      az containerapp update \
                                        --name sira-api-prod \
                                        --resource-group sira-rg \
                                        --image $ACR_NAME.azurecr.io/sira-api:latest
                                      ```

                                      ### Bicep Infrastructure (sira-rg)
                                      `infra/azure/main.bicep` creates at subscription scope:
                                      - Resource Group `sira-rg`
                                      - - Azure Container Registry (ACR)
                                        - - Container Apps Environment with Log Analytics
                                          - - Container Apps: `sira-api`, `sira-telematics`, `sira-maritime`, `sira-ai-worker`
                                            - - Azure Key Vault for secrets
                                             
                                              - ---

                                              ## Authentication (Supabase)

                                              SIRA uses **Supabase Auth** for all user-facing applications:

                                              | Flow | Implementation |
                                              |------|---------------|
                                              | Web Dashboard | Supabase JS SDK · Email/password · JWT in secure cookie |
                                              | Mobile App | Supabase React Native SDK · JWT in Expo SecureStore |
                                              | Backend API | JWT verified via Supabase JWT secret middleware |

                                              **RBAC Roles:** `super_admin` › `org_admin` › `logistics_manager` › `fleet_manager` › `analyst` › `driver` › `client_read`

                                              **Row Level Security:** All tables enforce `org_id` isolation — users can only access data within their own organisation.

                                              Vercel environment variables needed:
                                              ```
                                              NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
                                              NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
                                              ```

                                              ---

                                              ## API Endpoints (Phase 2)

                                              ### Authentication
                                              - `POST /api/v1/auth/token` — Login
                                              - - `POST /api/v1/auth/register` — Register
                                                - - `GET /api/v1/auth/me` — Current user profile
                                                 
                                                  - ### Fleet Management
                                                  - - `GET /api/v2/fleet/vehicles` — List vehicles
                                                    - - `POST /api/v2/fleet/vehicles` — Register vehicle
                                                      - - `GET /api/v2/fleet/vehicles/{id}/telemetry` — Latest telemetry
                                                        - - `POST /api/v2/fleet/trips` — Schedule trip
                                                          - - `GET /api/v2/fleet/alerts` — Active alerts
                                                            - - `GET /api/v2/fleet/geojson` — Vehicle positions (Mapbox)
                                                             
                                                              - ### Maritime
                                                              - - `GET /api/v2/maritime/vessels/geojson` — Vessel positions (Mapbox)
                                                                - - `GET /api/v2/maritime/arrivals/{port_id}` — Expected arrivals
                                                                 
                                                                  - ### AI Intelligence
                                                                  - - `POST /api/v2/ai/delay-risk` — Delay risk assessment
                                                                    - - `POST /api/v2/ai/maintenance` — Predictive maintenance
                                                                      - - `GET /api/v2/ai/risk-heatmap` — Risk heatmap GeoJSON
                                                                        - - `GET /api/v2/ai/market-intel` — Market intelligence
                                                                         
                                                                          - ### WebSocket
                                                                          - - `WS /ws/fleet` — Real-time fleet position updates (Mapbox SIM)
                                                                           
Phase 2: Update README.md (Azure sira-rg, Supabase auth, Docker, Vercel, full stack guide)
                                                                            ## Version Roadmap

                                                                            | Version | Status | Scope |
                                                                            |---------|--------|-------|
                                                                            | v1.0 MVP Phase 1 | Done | FastAPI, PostgreSQL, basic auth, partial Flespi |
                                                                            | v2.0 MVP Phase 2 | **Current** | Full Control Tower: Flespi + MarineTraffic + AI + Mapbox + Azure sira-rg + Vercel |
                                                                            | v2.5 Smart Contracts | Planned | Polygon/Hyperledger for shipment milestone verification |
                                                                            | v3.0 Advanced AI | Planned | Custom ML models, autonomous rerouting |

                                                                            ---

                                                                            ## Running Tests
                                                                            ```bash
                                                                            cd backend
                                                                            python -m pytest tests/ -v --cov=app
                                                                            ```

                                                                            ---

                                                                            ## License
                                                                            Proprietary — Energie Partners (EP)

                                                                            ## Support
                                                                            - Issues: [GitHub Issues](https://github.com/Sackson-Partners/sira/issues)
                                                                            - - Email: support@sira-platform.com
