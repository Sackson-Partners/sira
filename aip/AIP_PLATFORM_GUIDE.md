# AIP Platform Guide
## African Infrastructure Partners — User & Administrator Manual

---

## Table of Contents

1. [Platform Overview](#1-platform-overview)
2. [Authentication & Access](#2-authentication--access)
3. [Dashboard](#3-dashboard)
4. [Projects](#4-projects)
5. [PETFEL Due Diligence Engine](#5-petfel-due-diligence-engine)
6. [Executive Investment Notes (EIN)](#6-executive-investment-notes-ein)
7. [Pipeline Management](#7-pipeline-management)
8. [Investment Committee (IC) Governance](#8-investment-committee-ic-governance)
9. [Investors](#9-investors)
10. [Verifications](#10-verifications)
11. [Data Rooms](#11-data-rooms)
12. [Deal Rooms](#12-deal-rooms)
13. [Analytics](#13-analytics)
14. [Events](#14-events)
15. [Users Management](#15-users-management)
16. [Integrations](#16-integrations)
17. [AI Engine](#17-ai-engine)
18. [Excel Bulk Upload](#18-excel-bulk-upload)
19. [Environment Configuration](#19-environment-configuration)
20. [Roles & Permissions](#20-roles--permissions)

---

## 1. Platform Overview

The AIP (African Infrastructure Partners) platform is an institutional-grade deal origination and investment management system designed specifically for African infrastructure projects.

**Core capabilities:**
- Project origination and lifecycle management
- PETFEL due diligence scoring engine
- Executive Investment Note (EIN) generation
- IC governance with structured voting
- Investor matching and capital deployment tracking
- AI-powered analysis via Claude (primary) / OpenAI (fallback)

**Technology stack:**
- Frontend: Next.js (React) — deployed on Vercel (`aip-plum.vercel.app`)
- Backend: FastAPI (Python) — deployed on Railway
- Database: PostgreSQL (Supabase) / SQLite (local dev)
- Auth: Supabase Auth + optional Azure AD B2C

---

## 2. Authentication & Access

### Logging In

1. Navigate to the AIP platform URL
2. Enter your registered email and password
3. Click **Sign In**

The platform uses Supabase Authentication. Your session token is automatically sent to all API requests.

### Azure AD B2C (SSO)

If your organisation uses Azure Active Directory:
1. Click **Sign in with Microsoft** on the login page
2. Complete the B2C authentication flow
3. You will be redirected back to the dashboard

> **Admin note:** Set `NEXT_PUBLIC_AUTH_PROVIDER=azure_b2c` and configure the MSAL environment variables to enable B2C.

### First Login — Auto-Provisioning

New users who authenticate via Supabase or Azure B2C are automatically provisioned with the `analyst` role. An admin must elevate privileges if a higher role is needed (see [Users Management](#15-users-management)).

---

## 3. Dashboard

The main dashboard shows a summary of:
- **Total projects** in the pipeline
- **Pending IC sessions** requiring votes or decisions
- **Recent activity** across all modules
- **SLA alerts** for pipeline items approaching deadlines

Use the left sidebar to navigate between modules.

---

## 4. Projects

The Projects module is the core of the platform. Each project represents an African infrastructure opportunity.

### Creating a Project (Manual)

1. Click **New Project** (top-right button on the Projects page)
2. Fill in the form:
   - **Project Name** *(required)*
   - **Sector** — Energy, Mining, Water, Transport, Ports, Rail, Roads, Agriculture, Health, ICT, Social
   - **Country** — African country
   - **Region** — sub-national region
   - **Project Type** — PPP, Greenfield, Brownfield, etc.
   - **Stage** — planned, pre-feasibility, feasibility, procurement, construction, operational
   - **Estimated Cost** — free text (e.g., "$500M", "USD 1.2B")
   - **Description** — project overview
   - **Strategic Notes** — internal notes for analysts
3. Click **Create Project**

### Editing a Project

1. Find the project in the table
2. Click **Edit** in the Actions column
3. Modify any fields
4. Click **Save Changes**

### Deleting a Project

1. Click **Delete** in the Actions column
2. Confirm the deletion dialog

> **Note:** Deletion is permanent. Archive the project (change status to `decommissioned`) instead if you want to retain the record.

### Generating an AI Brief

1. Open a project
2. Click **Generate AI Brief**
3. Claude will analyse the project data and produce a structured intelligence brief covering risk factors, market context, and investment thesis

---

## 5. PETFEL Due Diligence Engine

PETFEL is the platform's proprietary due diligence framework covering six pillars:

| Pillar | Description |
|--------|-------------|
| **P** — Political & Regulatory | Governance stability, regulatory clarity, permits |
| **E** — Economic & Financial | Revenue model, IRR, debt service, fiscal viability |
| **T** — Technical | Engineering readiness, EPC quality, technology risk |
| **F** — Fiduciary & Legal | Legal structure, contracts, land rights, compliance |
| **E** — Environmental & Social | ESG standards, resettlement, community impact |
| **L** — Liquidity & Capital Markets | Exit options, DFI appetite, capital markets access |

### Running a PETFEL Assessment

1. Navigate to a project
2. Click **PETFEL Assessment**
3. Select **Create Assessment**
4. Score each sub-criterion (1–5) with evidence notes
5. Click **Calculate** to generate the weighted overall score
6. Review the rating (AAA, AA, A, BBB, BB, B, C) and gating result
7. Click **Submit** to lock the assessment

### PETFEL Scoring Guide

| Score | Interpretation |
|-------|----------------|
| 5     | Excellent — no material risk |
| 4     | Good — minor risks, mitigated |
| 3     | Acceptable — manageable risks |
| 2     | Weak — material risk, requires mitigation |
| 1     | Poor — deal-breaker risk |

---

## 6. Executive Investment Notes (EIN)

An EIN is a structured investment memorandum generated for IC presentation. It has 12 standard sections:

| Section | Content |
|---------|---------|
| 1 | Executive Summary |
| 2 | Project Overview |
| 3 | Market & Sector Analysis |
| 4 | Technical Assessment |
| 5 | Financial Model |
| 6 | Risk Register |
| 7 | ESG & Impact |
| 8 | Legal & Regulatory |
| 9 | Deal Structure |
| 10 | Sensitivity Analysis |
| 11 | Comparables |
| 12 | Recommendation |

### Creating an EIN

1. Navigate to the project
2. Click **Generate EIN**
3. Optionally link an existing PETFEL assessment
4. The AI engine will draft all 12 sections automatically
5. Review and edit each section as needed
6. Click **Submit for Review** when ready
7. An admin/IC member approves the EIN

### AI-Assisted EIN Drafting

Click **AI Draft** on any section to have Claude generate content based on the project data and PETFEL scores. You can regenerate individual sections without affecting others.

### EIN Workflow States

`draft` → `submitted` → `approved` → `sent`

---

## 7. Pipeline Management

The Pipeline module tracks the progression of projects through defined deal stages and monitors SLA compliance.

### Pipeline Stages

| Stage Code | Stage Name |
|------------|------------|
| `origination` | Deal Origination |
| `screening` | Initial Screening |
| `petfel_dd` | PETFEL Due Diligence |
| `ein_drafting` | EIN Drafting |
| `ic_review` | IC Review |
| `term_sheet` | Term Sheet |
| `financial_close` | Financial Close |
| `monitoring` | Active Monitoring |

### Moving a Project

1. Navigate to **Pipeline**
2. Find the project
3. Click **Move Stage**
4. Select the target stage
5. Add optional notes (e.g., reason for advancement)
6. Click **Confirm**

The system records all stage transitions with timestamps and the user who made the change.

### SLA Alerts

Each stage has a configurable SLA (Service Level Agreement) in days. Projects exceeding the SLA appear in red on the Pipeline overview and in the **SLA Alerts** panel on the Dashboard.

---

## 8. Investment Committee (IC) Governance

The IC module manages the formal investment decision-making process.

### Scheduling an IC Session

1. Navigate to **Investment Committee**
2. Click **Schedule IC Session**
3. Select the project
4. Set the scheduled date and time
5. Set the quorum required (default: 3 votes)
6. Click **Schedule**

### Submitting a Vote

1. Click on an IC session to open the detail view
2. In the **Cast Your Vote** section, select:
   - **Approve** — recommend investment
   - **Reject** — recommend declining
   - **Abstain** — no position (counts toward quorum)
   - **Defer** — recommend postponing decision
3. Optionally add a rationale
4. Click **Submit Vote**

> Each IC member can vote once per session. Re-submitting replaces the previous vote.

### Recording the Final Decision

Once quorum is met, authorised users (admin or IC members) can record the formal outcome:

1. In the **Record Final Decision** section
2. Select **Approved**, **Rejected**, or **Deferred**
3. The session status changes to `decided`

### IC Session Statuses

| Status | Meaning |
|--------|---------|
| `scheduled` | Session created, voting open |
| `in_progress` | At least one vote submitted |
| `decided` | Final decision recorded |

---

## 9. Investors

The Investors module maintains a database of fund managers, DFIs, and institutional investors.

### Registering an Investor

1. Navigate to **Investors**
2. Click **Add Investor**
3. Fill in:
   - Fund name
   - AUM (Assets Under Management)
   - Ticket size range (min/max)
   - Investment instruments (equity, debt, mezzanine, guarantee)
   - Target IRR
   - Country and sector focus
   - ESG constraints

### Investor Matching

1. On the Investors page, click **Match** next to an investor
2. The AI engine compares the investor's mandate against the project database
3. Matches are ranked by compatibility score with a written rationale

---

## 10. Verifications

Verifications record third-party or internal bankability assessments for projects.

### Creating a Verification

1. Navigate to **Verifications**
2. Click **Add Verification**
3. Select the project
4. Choose the verification level:
   - `preliminary` — desk review
   - `standard` — site visit + financial review
   - `full` — comprehensive bankability assessment
5. Enter bankability scores (technical readiness, financial robustness, legal clarity, ESG compliance)
6. Submit

---

## 11. Data Rooms

Data Rooms are secure, access-controlled document repositories for each project.

### Creating a Data Room

1. Navigate to **Data Rooms**
2. Click **New Data Room**
3. Select the linked project
4. Configure access controls:
   - **Require NDA** — users must confirm NDA before access
   - **Require Verification** — user's investor verification level threshold
   - **Enable Watermark** — PDF watermarking
   - **Allow Download / Print** — document export controls
5. Click **Create**

### Granting Access

1. Open the Data Room
2. Click **Manage Access**
3. Add users by email
4. Set their access level (view/download)

---

## 12. Deal Rooms

Deal Rooms are collaborative workspaces for active transactions — combining document sharing, messaging, and deal tracking.

### Creating a Deal Room

1. Navigate to **Deal Rooms**
2. Click **New Deal Room**
3. Link to a project
4. Set deal value, currency, and target close date
5. Enable video and chat as needed

Deal Rooms include:
- **Messaging** — threaded discussion between deal participants
- **Document sharing** — upload and share deal documents
- **Deal tracking** — status, milestones, and close timeline

---

## 13. Analytics

The Analytics module provides reporting and data exports.

**Available reports:**
- Portfolio overview (projects by sector, country, stage)
- Investment pipeline funnel
- IC decision history
- Investor deployment tracking
- ESG impact metrics

Click **New Report** to create a custom report with a sector/country filter.

---

## 14. Events

Track deal-related events, conferences, and milestones.

### Event Types

- `conference` — industry events
- `roadshow` — investor roadshows
- `ic_meeting` — formal IC sessions
- `site_visit` — project site visits
- `milestone` — project milestone (financial close, COD, etc.)

### Creating an Event

1. Navigate to **Events**
2. Click **Add Event**
3. Fill in name, description, date, and type
4. Optionally link related projects

---

## 15. Users Management

> **Admin role required.**

### Viewing Users

Navigate to **Users** to see all registered platform users with their role, verification status, and active status.

Use the search bar to filter by name, email, or organisation. Use the Role dropdown to filter by role.

### Adding a New User

1. Click **Add User**
2. Enter email, password, full name, organisation, and role
3. Click **Create User**

The user can log in immediately with the credentials provided.

### Editing a User

1. Click **Edit** next to a user
2. Update name, organisation, role, or active status
3. Click **Save Changes**

### Activating / Deactivating Users

- Click **Deactivate** to revoke platform access without deleting the account
- Click **Activate** to restore access

### Verifying Users

KYC-verified users (investors who have completed identity verification) should be marked as **Verified**:
1. Click **Verify** next to the user
2. The user's verification badge updates to ✓ Verified

### Deleting a User

Click **Delete** and confirm. This is permanent.

---

## 16. Integrations

The Integrations module connects AIP to external systems.

**Supported integrations:**
- **Airtable** — sync project data from Airtable bases
- **Azure AD B2C** — SSO authentication
- **OpenAI / Claude** — AI analysis engine

Configure integrations in **Settings → Integrations** by providing the required API keys and configuration.

---

## 17. AI Engine

The platform uses **Claude (Anthropic)** as the primary AI engine, with OpenAI as fallback. AI capabilities include:

### Project Analysis
- Automated project brief generation
- Country risk assessment
- Sector market analysis

### PETFEL Augmentation
On any PETFEL assessment, click **AI Augment** to have the AI:
- Suggest scores for incomplete criteria
- Identify missing risk factors
- Recommend mitigations

### EIN Drafting
Each EIN section can be AI-drafted using Claude. The prompt incorporates:
- Project metadata
- PETFEL scores and flags
- Country context

### Investor Matching
The AI matching engine compares each investor's mandate parameters against the project database and returns ranked matches with narrative rationale.

### Country Risk Briefs
Navigate to **Analytics → Country Risk** and enter a country name to generate a real-time risk brief covering political, economic, and infrastructure risk factors.

---

## 18. Excel Bulk Upload

Projects can be bulk-imported from an Excel spreadsheet.

### Template Format

Create an `.xlsx` file with the following columns (row 1 = headers):

| Column | Field | Required | Example |
|--------|-------|----------|---------|
| A | `project_name` | Yes | Lekki Deep Sea Port Phase 2 |
| B | `country` | Yes | Nigeria |
| C | `region` | No | Lagos |
| D | `sector` | No | Ports |
| E | `project_type` | No | Greenfield |
| F | `estimated_cost` | No | USD 1.5B |
| G | `status` | No | feasibility |
| H | `description` | No | Expansion of container handling... |
| I | `strategic_notes` | No | DFI anchor interest confirmed |
| J | `source_url` | No | https://... |

### Upload Procedure

**Via API (direct):**

```bash
curl -X POST https://your-backend/api/projects/bulk-upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@projects.xlsx"
```

**Via Admin Panel:**
1. Navigate to **Projects**
2. Click **Bulk Upload** (admin only)
3. Select your `.xlsx` file
4. Review the preview (shows parsed rows)
5. Click **Import** to commit all valid rows

### Validation Rules

- `project_name` must not be empty
- `status` must be one of: `planned`, `pre-feasibility`, `feasibility`, `procurement`, `construction`, `operational`, `decommissioned`
- Duplicate project names within the file are flagged as warnings (not errors)
- Invalid rows are skipped; a summary shows how many rows were imported vs skipped

---

## 19. Environment Configuration

### Required Environment Variables

#### Frontend (Vercel)

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `https://your-backend.railway.app` |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL | `https://xxx.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon/public key | `eyJ...` |
| `NEXT_PUBLIC_AUTH_PROVIDER` | Auth provider (`supabase` or `azure_b2c`) | `supabase` |
| `NEXT_PUBLIC_AZURE_CLIENT_ID` | Azure AD B2C client ID (if using B2C) | `xxxxxxxx-...` |
| `NEXT_PUBLIC_AZURE_TENANT_NAME` | Azure B2C tenant name | `yourtenant` |
| `NEXT_PUBLIC_AZURE_POLICY_NAME` | B2C sign-in policy | `B2C_1_signupsignin` |

#### Backend (Railway / Azure)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing secret (generate with `openssl rand -hex 32`) |
| `SUPABASE_JWT_SECRET` | Supabase JWT secret (from Supabase Settings → API → JWT Secret) |
| `ANTHROPIC_API_KEY` | Claude API key for AI features |
| `OPENAI_API_KEY` | OpenAI fallback API key |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed frontend origins |

### Setting Up Supabase JWT Bridge

The backend validates Supabase JWTs by reading `SUPABASE_JWT_SECRET`. To configure:

1. Go to Supabase Dashboard → Settings → API
2. Copy the **JWT Secret**
3. Set it as `SUPABASE_JWT_SECRET` in your backend environment

---

## 20. Roles & Permissions

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| `admin` | Platform administrator | All permissions including user management |
| `analyst` | Deal team analyst | Create/edit projects, run PETFEL/EIN, move pipeline |
| `ic_member` | Investment Committee member | Submit IC votes, view EINs |
| `gov_partner` | Government partner | View projects, data rooms |
| `epc` | EPC contractor | View relevant projects |
| `investor` | Registered investor | View data rooms (with access), deal rooms |
| `viewer` | Read-only access | View public project summaries |

### Changing a User's Role

1. Navigate to **Users** (admin only)
2. Click **Edit** next to the user
3. Select the new role from the dropdown
4. Click **Save Changes**

---

*AIP Platform Guide — v2.1 — African Infrastructure Partners*
