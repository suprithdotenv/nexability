# NexAbility — Inclusive Hiring & AI-Powered Accessibility Platform

[![Backend CI](https://github.com/nexability/nexability/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/nexability/nexability/actions)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%200.162-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2019%20%2B%20Vite%208-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/Database-Neon%20Postgres%20%2B%20pgvector-336791.svg?logo=postgresql&logoColor=white)](https://neon.tech)
[![Accessibility](https://img.shields.io/badge/Accessibility-WCAG%202.2%20AA-blue.svg)](https://www.w3.org/WAI/standards-guidelines/wcag/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](#license)

NexAbility is an inclusive hiring and talent-matching platform engineered to connect candidates with disabilities to inclusive employers. By combining dense semantic vector search with independent workplace accessibility auditing, NexAbility ensures candidates are evaluated strictly on their professional merits while empowering transparent accommodation requests.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Key Features](#2-key-features)
3. [Technology Stack](#3-technology-stack)
4. [System Architecture](#4-project-architecture)
5. [Repository Structure](#5-folder-structure)
6. [Installation & Local Setup](#6-installation-and-setup)
7. [Environment Variables](#7-environment-variables)
8. [Comprehensive API Documentation](#8-api-documentation)
9. [User Workflows](#9-user-workflows)
10. [Testing & Quality Assurance](#10-testing-and-quality-assurance)
11. [Accessibility & Inclusivity Principles](#11-accessibility-and-inclusivity)
12. [Development & Contribution Workflow](#12-development-workflow)
13. [Future Enhancements](#13-future-enhancements)
14. [Troubleshooting & Support](#14-additional-documentation)

---

## 1. Project Overview

### The Problem
Conventional applicant tracking systems (ATS) and hiring portals evaluate candidates through opaque filters that frequently penalize non-traditional career timelines, screen out individuals requiring workplace accommodations, and obscure critical workplace accessibility data. Candidates with disabilities are often forced to choose between disclosing their needs prematurely—facing unconscious bias—or entering an inaccessible interview process.

### The NexAbility Solution
NexAbility redesigns recruitment through a dual-lens framework:
- **Strict Separation of Professional Qualification and Accessibility:** Professional compatibility (skills, technical proficiencies, domain experience) is scored completely independently from accessibility requirements. A missing accessibility accommodation or undeclared need **never** lowers a candidate's professional match score.
- **Transparent Accessibility Statuses:** Instead of binary "accessible/inaccessible" labels, workplaces and job roles evaluate needs using four explicit statuses: `AVAILABLE`, `ON_REQUEST`, `NOT_SPECIFIED`, and `UNAVAILABLE`. Crucially, `NOT_SPECIFIED` is never conflated with `UNAVAILABLE`.
- **Voluntary & Private Self-Declaration:** Candidates can voluntarily declare disability statuses under cryptographic privacy safeguards. No diagnosis paperwork, doctor's notes, or medical history are ever required.
- **Direct Accommodation Pathways:** Every identified accommodation gap provides an actionable pathway for the candidate to request accommodations directly from the employer's hiring team.

### Target Users
- **Candidates with Disabilities:** Job seekers looking for transparent workplaces with verified accessibility capabilities (screen readers, quiet rooms, flexible hours, captioning, wheelchair access).
- **Inclusive Employers & HR Leaders:** Organizations striving for neurodiverse and disability-inclusive talent pipelines with structured accommodation request management.

---

## 2. Key Features

| Feature | Status | Description |
|---|---|---|
| **Role-Based Authentication** | **Implemented** | Candidate and Employer login with Argon2-hashed passwords, short-lived JWT access tokens (15 min), rolling refresh tokens (7 days), and route guards. |
| **Email Verification & OTP** | **Implemented** | 6-digit cryptographic OTP generation, SHA-256 hashed storage, verified email ticket exchange, Resend API & Gmail SMTP failover. |
| **Google OAuth 2.0** | **Implemented** | Seamless single sign-on verifying Google ID tokens with automated profile generation. |
| **Candidate Profile & Resume Vault** | **Implemented** | Complete candidate management, document uploads (PDF/DOCX up to 10 MB) stored in Supabase with signed download URLs. |
| **Automated Text Extraction & Chunker** | **Implemented** | PyPDF and structural regex parsing into overlapping semantic chunks with character coverage guarantees. |
| **Neon pgvector 768-d Embeddings** | **Implemented** | 768-dimensional dense vector embeddings generated and indexed in Neon PostgreSQL for semantic matching. |
| **Standalone ML Matchmaker** | **Implemented** | Standalone microservice on port 8001 evaluating dense cosine similarity + keyword matching against job requirements. |
| **Voluntary Disability Declaration** | **Implemented** | Versioned, timestamped declaration management with explicit candidate withdrawal endpoints and privacy safeguards. |
| **Job Postings & Discovery** | **Implemented** | Public listings, search, work-mode filters (Remote/Hybrid/Onsite), and detailed accessibility capability breakdowns. |
| **Application Pipeline** | **Implemented** | 1-click candidate applications with custom cover notes, duplicate application prevention, and real-time status tracking. |
| **Accommodation Requests** | **Implemented** | Structured request system linking candidate preferences to job postings with employer response workflows. |
| **Employer Portal & Analytics** | **Implemented** | Employer dashboard with metrics: active jobs, pending applications, open accommodation requests, and document parsing status. |
| **AI Specialist Agents (L4)** | **Partially Implemented** | Agent architecture and tool wrappers defined in `backend/app/agents/`; coordinator loop awaiting full integration. |
| **Live Captioned Video Interviews (L5)** | **Planned** | WebRTC video SDK integration with live captioning and scheduling coordination. |
| **SAP SuccessFactors Integration (L5)** | **Planned** | Mock bidirectional export payload conforming to SAP SuccessFactors ATS schemas. |

---

## 3. Technology Stack

### Frontend Application (`frontend/`)
- **Framework:** [React 19.3.1](https://react.dev/)
- **Bundler & Dev Server:** [Vite 8.3.5](https://vite.dev/)
- **Routing:** [React Router v7.18.5](https://reactrouter.com/)
- **Styling:** Custom CSS Design Tokens (`tokens.css`, `base.css`, `App.css`) optimized for high-contrast WCAG 2.2 AA compliance. No heavy third-party CSS dependencies.
- **State Management:** React Context API (`AuthContext.jsx`) with in-memory JWT storage and automatic token refresh interceptors.
- **Test Runner:** Node.js native test runner (`node --test tests/**/*.test.js`).

### Backend Platform (`backend/`)
- **Framework:** [FastAPI 0.162.0](https://fastapi.tiangolo.com/) (Python 3.11+)
- **ASGI Server:** [Uvicorn 0.54.0](https://www.uvicorn.org/)
- **Data Validation & Schemas:** [Pydantic v2.14](https://docs.pydantic.dev/) and `pydantic-settings`
- **ORM & Database Toolkit:** [SQLAlchemy 2.1.6](https://www.sqlalchemy.org/)
- **Database Driver:** [psycopg3 3.3.6](https://www.psycopg.org/psycopg3/) with `pgvector 0.5.1`
- **Database Migrations:** [Alembic 1.20.1](https://alembic.sqlalchemy.org/)
- **Security & Cryptography:** `pwdlib[argon2]`, `PyJWT 2.15.1`, `cryptography 50.0.2`
- **Email Delivery:** [Resend SDK](https://resend.com) with standard `smtplib` Gmail fallback

### Machine Learning & Vector Service (`ml/`)
- **Service Engine:** FastAPI 0.115+ on port 8001
- **Vector Embeddings:** 768-dimensional vectors supporting `intfloat/e5-base-v2` (`sentence-transformers`) with deterministic bag-of-words fallback (`SimpleEmbeddingModel`).
- **Document Ingestion:** [PyPDF 6.21.4](https://pypdf.readthedocs.io/) and XML DOM for DOCX extraction.
- **LLM Integration (Optional):** Groq Cloud API (`openai/gpt-oss-120b`) with strict fail-closed privacy redaction for contact details and disability disclosures.

### Storage & Cloud Infrastructure
- **Relational & Vector Database:** [Neon Serverless PostgreSQL](https://neon.tech/) with `vector` extension.
- **Object Storage:** [Supabase Storage](https://supabase.com/) (`resumes` and `job-documents` private buckets).
- **Deployment Platform:** [Render](https://render.com) using native `render.yaml` Blueprint.

---

## 4. Project Architecture

NexAbility follows a 5-layer separation of concerns:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      L1: Accessible Frontend                           │
│     React 19 SPA • WCAG 2.2 AA Contrast • In-Memory Auth Guard        │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ HTTPS / REST JSON
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        L2: Core FastAPI Platform                       │
│    Auth • Endpoints • DB Sessions • Validation • Storage Service       │
└───────────────┬───────────────────────────────┬────────────────────────┘
                │ Internal HTTP                 │ SQLAlchemy 2.0
                ▼                               ▼
┌───────────────────────────────┐  ┌─────────────────────────────────────┐
│    L3: Standalone ML Service  │  │       Neon Serverless PostgreSQL    │
│  Port 8001 • Cosine Vector    │  │   Users • Profiles • Applications   │
│  Similarity • E5 Embeddings   │  │   Disabilities • pgvector Chunks    │
└───────────────┬───────────────┘  └─────────────────────────────────────┘
                │ S3 API
                ▼
┌───────────────────────────────┐
│     Supabase Object Storage   │
│   Private Resumes & Job PDFs  │
└───────────────────────────────┘
```

### System Component Interactions

```mermaid
sequenceDiagram
    autonumber
    actor Candidate
    participant Frontend as React 19 Frontend
    participant Backend as FastAPI Backend (8000)
    participant ML as ML Service (8001)
    participant Neon as Neon Postgres (pgvector)
    participant Supabase as Supabase Storage

    Candidate->>Frontend: Upload Resume (PDF)
    Frontend->>Backend: POST /api/v1/candidates/me/resume
    Backend->>Supabase: Store Encrypted File Binary
    Backend->>Neon: Insert Resume Record (Status: UPLOADED)
    Backend->>Backend: Synchronous Extract & Chunk
    Backend->>Neon: Store 768-d Vectors in candidate_resume_chunks
    Backend-->>Frontend: 201 Created (Status: PROCESSED)

    Candidate->>Frontend: Click "AI Match"
    Frontend->>Backend: GET /api/v1/candidates/me/matches?min_threshold=60.0
    Backend->>ML: GET /api/v1/ml/matches (Candidate ID + Threshold)
    ML->>Neon: Vector Cosine Similarity Query (<=> operator)
    ML->>ML: Compute Professional Match Score (0 - 100%)
    ML->>ML: Evaluate Accessibility Accommodations Independently
    ML-->>Backend: Ranked Qualifying Job Matches
    Backend-->>Frontend: Enriched Matches with Company Profiles
    Frontend-->>Candidate: Render Ranked Jobs with Transparent Acc Badges
```

### Authentication & Token Refresh Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant App as React Frontend
    participant Store as In-Memory TokenStore
    participant API as FastAPI Backend

    User->>App: Submit Email & Password
    App->>API: POST /api/v1/auth/login
    API->>API: Verify Argon2 Password Hash
    API->>API: Issue Access Token (15m) & Refresh Token (7d)
    API-->>App: Return Tokens
    App->>Store: Store Access Token in Memory (Never localStorage)
    App->>Store: Store Refresh Token in Memory

    Note over App,API: Subsequent Authenticated Requests
    App->>API: GET /api/v1/candidates/me (Header: Bearer AccessToken)
    API-->>App: 200 OK

    Note over App,API: On Access Token Expiry (401 Unauthorized)
    App->>API: POST /api/v1/auth/refresh (Body: { refresh_token })
    API->>API: Verify Token Family & Revocation Table
    API-->>App: Return New Access & Refresh Tokens
    App->>Store: Rotate Tokens in Memory
```

---

## 5. Folder Structure

```
nexability/
├── .github/
│   └── workflows/
│       └── backend-ci.yml             # Automated CI workflow running pytest and ruff
├── backend/                           # Core FastAPI application
│   ├── alembic/                       # Database migrations
│   │   ├── versions/                  # Revision files for profiles, vector tables, and jobs
│   │   └── env.py                     # Alembic configuration
│   ├── app/
│   │   ├── agents/                    # Specialist agent definitions (Candidate, Matching)
│   │   ├── api/
│   │   │   ├── dependencies.py        # Token, DB, and Role-Based dependency injectors
│   │   │   └── v1/
│   │   │       ├── endpoints/         # HTTP route controllers
│   │   │       │   ├── auth.py        # Registration, login, OTP, Google OAuth, password reset
│   │   │       │   ├── candidates.py  # Profiles, resumes, accessibility preferences
│   │   │       │   ├── employers.py   # Company profiles, job documents, capabilities
│   │   │       │   ├── matches.py     # Candidate AI job matching endpoint
│   │   │       │   └── ml_access.py   # Internal service-to-service endpoints for ML
│   │   │       └── router.py          # Consolidated V1 API router
│   │   ├── automated_pipeline/        # Automated text extraction, chunking, and Neon pgvector
│   │   │   ├── chunker.py             # Overlapping text chunk generator
│   │   │   ├── embeddings.py          # 768-d vector encoder
│   │   │   ├── extractor.py           # Regex-based skill, title, and heading extractor
│   │   │   ├── matching.py            # Vector similarity calculation
│   │   │   ├── models.py              # pgvector chunk models for Neon
│   │   │   └── processor.py           # Document processing orchestrator
│   │   ├── core/                      # Configuration, settings, and security helpers
│   │   ├── db/                        # SQLAlchemy base and session makers
│   │   ├── models/                    # Persistence models (User, Resume, JobDocument, etc.)
│   │   ├── repositories/              # Database access layer
│   │   ├── schemas/                   # Pydantic request and response contracts
│   │   ├── services/                  # Business logic (Auth, Email, Storage, Matching)
│   │   └── main.py                    # FastAPI entrypoint and CORS middleware
│   ├── declaration_feature/           # Voluntary Disability Self-Declaration package
│   │   ├── api.py                     # Declaration CRUD endpoints
│   │   └── schemas/declaration.py     # Pydantic schemas for declarations
│   ├── employer_feature/              # Job posting, applications, and accommodation inbox
│   │   ├── api/                       # Jobs, applications, accommodations, dashboard routers
│   │   ├── models/                    # JobPosting, JobApplication, AccommodationRequest models
│   │   └── services/                  # Business services for employer workflows
│   ├── tests/                         # Pytest test suite (unit, integration, api, contract)
│   ├── pyproject.toml                 # Backend package definitions and ruff config
│   └── requirements.txt               # Pinned pip dependencies (UTF-8)
├── frontend/                          # Client React 19 application
│   ├── src/
│   │   ├── api/                       # API clients with auto-refresh token store
│   │   │   ├── auth.js                # Auth, registration, and OTP API calls
│   │   │   ├── candidate.js           # Candidate dashboard, jobs, and matches API calls
│   │   │   └── client.js              # Centralized fetch wrapper with Bearer injection
│   │   ├── components/                # Reusable UI components
│   │   │   ├── AccessibilityPreferencesManager.jsx # Candidate accessibility preference editor
│   │   │   ├── CandidateProfileEditor.jsx          # Personal info and profile editor
│   │   │   ├── DisabilityDeclaration.jsx           # Voluntary declaration consent component
│   │   │   ├── ProtectedRoute.jsx                  # Client-side RBAC route guard
│   │   │   ├── ResumeManager.jsx                   # Resume upload, download, and delete UI
│   │   │   ├── SiteHeader.jsx                      # Accessible navigation bar with role toggles
│   │   │   └── SiteFooter.jsx                      # Standard footer component
│   │   ├── context/                   # React Context providers (AuthContext.jsx)
│   │   ├── features/
│   │   │   ├── candidate/components/  # InclusiveJobMatches, MyApplications, MyAccommodations
│   │   │   └── employer/components/   # JobManager, AccommodationInbox, ApplicationsDashboard
│   │   ├── pages/                     # Routed view pages
│   │   │   ├── CandidateDashboardPage.jsx  # Candidate home dashboard
│   │   │   ├── EmployerDashboardPage.jsx   # Employer analytics and management portal
│   │   │   ├── JobDiscoveryPage.jsx        # Public job explorer with search and filters
│   │   │   ├── LoginPage.jsx               # Universal sign-in page
│   │   │   └── RegisterPage.jsx            # Multi-step candidate/employer registration
│   │   ├── styles/                    # Design tokens and high-contrast CSS rules
│   │   └── utils/matching.js          # Deterministic matching & accessibility evaluation logic
│   ├── tests/                         # Node.js test runner unit and integration suites
│   ├── package.json                   # NPM dependencies and scripts
│   └── vite.config.js                 # Vite configuration with local proxy to port 8000
├── ml/                                # Machine Learning Matching Service
│   ├── nexability_ml/
│   │   ├── chunking.py                # Document chunking routines
│   │   ├── embeddings.py              # E5 model with fallback tokenizer & encoder
│   │   ├── groq_extraction.py         # Optional LLM extraction with privacy filters
│   │   ├── matcher.py                 # Core professional matching rules & substitutions
│   │   ├── matching_service.py        # Standalone FastAPI service running on port 8001
│   │   ├── normalizer.py              # Heading, section, and skill normalizer
│   │   └── parser.py                  # In-memory PDF/DOCX byte parser
│   ├── tests/                         # 114 ML unit tests
│   └── pyproject.toml                 # ML package definition
├── docs/                              # Architectural documents and layer ownership guides
├── render.yaml                        # Render Blueprint specification for zero-config deployment
├── render_start.sh                    # Production script running ML (8001) & Backend (8000)
└── README.md                          # Project documentation (this file)
```

---

## 6. Installation and Setup

### Prerequisites
- **Node.js:** v20.x or v22.x LTS (`node -v`)
- **Python:** v3.11.x or v3.12.x (`python --version`)
- **Git:** v2.30+
- **PostgreSQL / Neon Account:** Instance with `pgvector` enabled.

---

### Step 1: Clone Repository
```bash
git clone https://github.com/nexability/nexability.git
cd nexability
```

---

### Step 2: Backend Setup
Open a terminal in the `backend/` directory:

```bash
cd backend

# Create Python virtual environment
python -m venv .venv

# Activate virtual environment:
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate

# Upgrade pip and install dependencies in editable mode
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e ".[dev]"
pip install -e ../ml
```

#### Configure Backend Environment Variables
Create `backend/.env` (see [Environment Variables](#7-environment-variables) for guidance):
```bash
# Windows:
copy .env.example .env
# Linux / macOS:
# cp .env.example .env
```

#### Run Database Migrations
```bash
alembic upgrade head
```

#### Start Backend API Server
```bash
# Runs on http://localhost:8000
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

### Step 3: ML Matching Service Setup
Open a second terminal in the `ml/` directory:

```bash
cd ml

# Use the backend virtual environment:
# Windows (PowerShell):
$env:PYTHONPATH = "D:\sap\nexability\ml;D:\sap\nexability\backend"
..\backend\.venv\Scripts\python.exe -m uvicorn nexability_ml.matching_service:app --host 0.0.0.0 --port 8001 --reload

# Linux / macOS:
# export PYTHONPATH="$(pwd):$(pwd)/../backend"
# ../backend/.venv/bin/python -m uvicorn nexability_ml.matching_service:app --host 0.0.0.0 --port 8001 --reload
```

---

### Step 4: Frontend Setup
Open a third terminal in the `frontend/` directory:

```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev -- --host 0.0.0.0 --port 5000
```

---

### Local Service Verification

| Service | Local URL | Health Endpoint | Interactive Documentation |
|---|---|---|---|
| **Frontend Application** | [http://localhost:5000](http://localhost:5000) | N/A | N/A |
| **Backend API** | [http://localhost:8000](http://localhost:8000) | `GET /health` | [Swagger UI](http://localhost:8000/docs) \| [ReDoc](http://localhost:8000/redoc) |
| **ML Matching Service** | [http://localhost:8001](http://localhost:8001) | `GET /docs` | [Swagger UI](http://localhost:8001/docs) |

---

## 7. Environment Variables

> **Security Rule:** Never commit real secrets, passwords, or credentials into version control. Use `.env` locally and configure secrets directly within your hosting provider.

### Backend Environment Variables (`backend/.env`)

| Variable Name | Required | Default / Example Placeholder | Purpose |
|---|---|---|---|
| `DATABASE_URL` | **Yes** | `postgresql://user:pass@host/dbname?sslmode=require` | Connection string for Neon PostgreSQL database. |
| `JWT_SECRET_KEY` | **Yes** | `replace_with_64_char_random_hex_key` | Secret key used to sign and verify HMAC-SHA256 JWTs. |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` | Lifetime of short-lived access tokens. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Lifetime of rolling refresh tokens. |
| `OTP_SECRET` | **Yes** | `replace_with_random_32_byte_hex` | Cryptographic secret for generating 6-digit OTP codes. |
| `OTP_HASH_SECRET` | **Yes** | `replace_with_random_32_byte_hex` | Salt for hashing OTP records stored in database. |
| `RESEND_API_KEY` | Optional | `re_123456789...` | API key for transactional emails via Resend. |
| `EMAIL_FROM` | No | `NexAbility <onboarding@resend.dev>` | Outgoing sender identity for email notifications. |
| `SMTP_HOST` | Optional | `smtp.gmail.com` | SMTP host used as failover when Resend is unconfigured. |
| `SMTP_PORT` | Optional | `587` | SMTP port (587 for STARTTLS). |
| `SMTP_EMAIL` | Optional | `notifications@example.com` | SMTP authentication user. |
| `SMTP_PASSWORD` | Optional | `app_specific_password` | SMTP app-specific password. |
| `GOOGLE_CLIENT_ID` | Optional | `123456...apps.googleusercontent.com` | OAuth client ID for Google SSO validation. |
| `SUPABASE_URL` | **Yes** | `https://your-project.supabase.co` | Supabase API URL for object storage access. |
| `SUPABASE_SERVICE_ROLE_KEY` | **Yes** | `sb_secret_...` | Supabase Service Role Key for authenticated uploads/downloads. |
| `SUPABASE_STORAGE_BUCKET_RESUMES` | No | `resumes` | Storage bucket for candidate resume documents. |
| `SUPABASE_STORAGE_BUCKET_JOB_DOCS` | No | `job-documents` | Storage bucket for employer job descriptions. |
| `MAX_UPLOAD_SIZE_BYTES` | No | `10485760` (10 MB) | Maximum permitted file upload size in bytes. |
| `INTERNAL_ML_API_KEY` | **Yes** | `ml-internal-secret-token` | Shared secret header (`X-Internal-Service-Key`) for internal ML calls. |
| `ML_SERVICE_URL` | **Yes** | `http://127.0.0.1:8001` | Base URL of the standalone ML Matching Service. |
| `PROFESSIONAL_MATCH_THRESHOLD` | No | `60.0` | Default minimum threshold percentage for AI job matching. |

### ML Service Environment Variables (`ml/.env`)

| Variable Name | Required | Default / Example Placeholder | Purpose |
|---|---|---|---|
| `NEXABILITY_BACKEND_URL` | No | `http://127.0.0.1:8000` | Backend API URL for retrieving document metadata and files. |
| `NEXABILITY_INTERNAL_ML_API_KEY` | No | `ml-internal-secret-token` | Must match `INTERNAL_ML_API_KEY` in the backend. |
| `EMBEDDING_MODEL` | No | `placeholder` (or `intfloat/e5-base-v2`) | Embedding encoder engine. |
| `EMBEDDING_DIM` | No | `768` | Vector dimension for pgvector embeddings. |
| `NEXABILITY_LLM_EXTRACTION` | No | `false` | Enable Groq LLM extraction (defaults to `false` for rule-based). |
| `GROQ_API_KEY` | Optional | `gsk_...` | Required only when `NEXABILITY_LLM_EXTRACTION=true`. |

### Frontend Environment Variables (`frontend/.env.production`)

| Variable Name | Required | Default / Example Placeholder | Purpose |
|---|---|---|---|
| `VITE_API_BASE_URL` | No | `/api/v1` (Proxy) \| `https://api.yourdomain.com/api/v1` | Base URL used by the frontend client to query the backend. |

---

## 8. API Documentation

### 8.1 Authentication & Security (`/api/v1/auth`)

| Method | Endpoint | Description | Auth Required | Request Body | Response Model | Status |
|---|---|---|---|---|---|---|
| `POST` | `/api/v1/auth/employer/email/check` | Validate employer corporate email domain | Public | `EmployerEmailCheckRequest` | `EmployerEmailCheckResponse` | 200 |
| `POST` | `/api/v1/auth/otp/send` | Request 6-digit email OTP code | Public | `OTPSendRequest` | `OTPResponse` | 200 |
| `POST` | `/api/v1/auth/otp/verify` | Verify OTP and receive verification ticket | Public | `OTPVerifyRequest` | `OTPVerifyResponse` | 200 |
| `POST` | `/api/v1/auth/candidate/register` | Register new candidate with verified ticket | Public | `CandidateRegisterRequest` | `CandidateRegisterResponse` | 201 |
| `POST` | `/api/v1/auth/employer/register` | Register new employer with verified ticket | Public | `EmployerRegisterRequest` | `EmployerRegisterResponse` | 201 |
| `POST` | `/api/v1/auth/login` | Authenticate with email and password | Public | `LoginRequest` | `TokenResponse` | 200 |
| `POST` | `/api/v1/auth/refresh` | Exchange refresh token for new token pair | Public | `RefreshRequest` | `TokenResponse` | 200 |
| `POST` | `/api/v1/auth/logout` | Revoke active refresh token family | Bearer JWT | `RefreshRequest` | `LogoutResponse` | 200 |
| `GET` | `/api/v1/auth/me` | Fetch authenticated user identity & role | Bearer JWT | None | `UserResponse` | 200 |
| `POST` | `/api/v1/auth/google` | Sign in or sign up with Google ID token | Public | `GoogleLoginRequest` | `TokenResponse` | 200 |
| `POST` | `/api/v1/auth/password/forgot` | Initiate password reset flow | Public | `ForgotPasswordRequest` | `dict` | 200 |
| `POST` | `/api/v1/auth/password/reset` | Complete password reset with OTP ticket | Public | `ResetPasswordRequest` | `dict` | 200 |

### 8.2 Candidates & Resumes (`/api/v1/candidates`)

| Method | Endpoint | Description | Auth Required | Request Body | Response Model | Status |
|---|---|---|---|---|---|---|
| `GET` | `/api/v1/candidates/me` | Retrieve candidate profile | Candidate | None | `CandidateProfileResponse` | 200 |
| `PATCH` | `/api/v1/candidates/me` | Update candidate profile details | Candidate | `CandidateProfileUpdate` | `CandidateProfileResponse` | 200 |
| `POST` | `/api/v1/candidates/me/resume` | Upload PDF/DOCX resume file | Candidate | `multipart/form-data` | `ResumeMetadataResponse` | 201 |
| `GET` | `/api/v1/candidates/me/resume` | Get active resume metadata and signed URL | Candidate | None | `ResumeMetadataResponse` | 200 |
| `GET` | `/api/v1/candidates/me/resume/download` | Download raw resume binary stream | Candidate | None | Binary (`application/pdf`) | 200 |
| `DELETE` | `/api/v1/candidates/me/resume` | Delete active resume document | Candidate | None | `ResumeActionResponse` | 200 |
| `GET` | `/api/v1/candidates/me/accessibility` | List candidate accessibility preferences | Candidate | None | `list[AccessibilityPreferenceResponse]` | 200 |
| `POST` | `/api/v1/candidates/me/accessibility` | Declare new accessibility preference | Candidate | `AccessibilityPreferenceCreate` | `AccessibilityPreferenceResponse` | 201 |
| `PATCH` | `/api/v1/candidates/me/accessibility/{id}` | Update declared accessibility preference | Candidate | `AccessibilityPreferenceUpdate` | `AccessibilityPreferenceResponse` | 200 |
| `DELETE` | `/api/v1/candidates/me/accessibility/{id}` | Remove declared accessibility preference | Candidate | None | `dict` | 200 |
| `GET` | `/api/v1/candidates/me/matches` | Retrieve AI-ranked job recommendations | Candidate | Query: `min_threshold=60.0` | `CandidateMatchResponse` | 200 |

### 8.3 Voluntary Disability Declaration (`/api/v1/candidates/me/declaration`)

| Method | Endpoint | Description | Auth Required | Request Body | Response Model | Status |
|---|---|---|---|---|---|---|
| `GET` | `/api/v1/candidates/me/declaration` | Check active declaration status | Candidate | None | `DeclarationResponse` | 200 |
| `POST` | `/api/v1/candidates/me/declaration` | Record voluntary disability declaration | Candidate | `DeclarationCreate` | `DeclarationResponse` | 201 |
| `PUT` | `/api/v1/candidates/me/declaration` | Update existing declaration terms | Candidate | `DeclarationCreate` | `DeclarationResponse` | 200 |
| `DELETE` | `/api/v1/candidates/me/declaration` | Withdraw active disability declaration | Candidate | None | `DeclarationDeleteResponse` | 200 |

### 8.4 Employers & Job Postings (`/api/v1`)

| Method | Endpoint | Description | Auth Required | Request Body | Response Model | Status |
|---|---|---|---|---|---|---|
| `GET` | `/api/v1/employers/me` | Get employer company profile | Employer | None | `EmployerProfileResponse` | 200 |
| `PATCH` | `/api/v1/employers/me` | Update employer company profile | Employer | `EmployerProfileUpdate` | `EmployerProfileResponse` | 200 |
| `GET` | `/api/v1/employers/me/dashboard` | Aggregated employer analytics & counts | Employer | None | `EmployerDashboardResponse` | 200 |
| `POST` | `/api/v1/employers/me/jobs` | Create new structured job posting | Employer | `JobCreate` | `JobResponse` | 201 |
| `GET` | `/api/v1/employers/me/jobs` | List employer's created job postings | Employer | None | `list[JobResponse]` | 200 |
| `GET` | `/api/v1/employers/me/jobs/{job_id}` | Retrieve single job posting details | Employer | None | `JobResponse` | 200 |
| `PATCH` | `/api/v1/employers/me/jobs/{job_id}` | Edit job posting details or status | Employer | `JobUpdate` | `JobResponse` | 200 |
| `DELETE` | `/api/v1/employers/me/jobs/{job_id}` | Delete job posting | Employer | None | `dict` | 200 |
| `POST` | `/api/v1/employers/me/job-documents` | Upload PDF/DOCX job description | Employer | `multipart/form-data` | `JobDocumentResponse` | 201 |
| `GET` | `/api/v1/employers/me/job-documents` | List uploaded job documents | Employer | None | `list[JobDocumentResponse]` | 200 |
| `DELETE` | `/api/v1/employers/me/job-documents/{id}` | Delete uploaded job document | Employer | None | `JobDocumentActionResponse` | 200 |
| `GET` | `/api/v1/jobs` | Public listing of all active jobs | Public | None | `list[JobResponse]` | 200 |
| `GET` | `/api/v1/jobs/{job_id}` | Public details of specific job | Public | None | `JobResponse` | 200 |

### 8.5 Applications & Accommodations (`/api/v1`)

| Method | Endpoint | Description | Auth Required | Request Body | Response Model | Status |
|---|---|---|---|---|---|---|
| `POST` | `/api/v1/candidates/me/jobs/{id}/apply` | Submit job application | Candidate | `JobApplicationCreate` | `JobApplicationResponse` | 201 |
| `GET` | `/api/v1/candidates/me/applications` | Candidate lists own applications | Candidate | None | `list[JobApplicationResponse]` | 200 |
| `GET` | `/api/v1/employers/me/applications` | Employer reviews candidate applications | Employer | Query: `status`, `job_id` | `list[JobApplicationResponse]` | 200 |
| `PATCH` | `/api/v1/employers/me/applications/{id}/status` | Update application stage (Reviewed, Interview, etc.) | Employer | `JobApplicationStatusUpdate` | `JobApplicationResponse` | 200 |
| `POST` | `/api/v1/candidates/me/jobs/{id}/accommodations` | Submit interview accommodation request | Candidate | `AccommodationRequestCreate` | `AccommodationRequestResponse` | 201 |
| `GET` | `/api/v1/candidates/me/accommodations` | Candidate lists own requests | Candidate | None | `list[AccommodationRequestResponse]` | 200 |
| `GET` | `/api/v1/employers/me/accommodations` | Employer inbox for accommodation requests | Employer | None | `list[AccommodationRequestResponse]` | 200 |
| `PATCH` | `/api/v1/employers/me/accommodations/{id}` | Employer responds to request (Granted/Alternative) | Employer | `AccommodationResponseUpdate` | `AccommodationRequestResponse` | 200 |

---

## 9. User Workflows

### Candidate Journey

```mermaid
flowchart TD
    A[Visit NexAbility] --> B[Register with Email OTP or Google SSO]
    B --> C[Candidate Dashboard]
    C --> D[Upload Resume PDF/DOCX]
    D --> E[Automatic Text Chunking & 768-d Vector Generation]
    C --> F[Declare Voluntary Accessibility Preferences]
    C --> G[Optional Voluntary Disability Self-Declaration]
    E & F --> H[View AI-Ranked Inclusive Job Matches]
    H --> I{Review Match Details}
    I -->|Professional Score >= 60%| J[Inspect Matched Skills & Independence Badges]
    J --> K[Submit Job Application with Custom Note]
    J --> L[Submit Direct Workplace Accommodation Request]
    K --> M[Track Application Stages in Real-Time]
    L --> N[Receive Employer Accommodation Response]
```

1. **Onboarding & Verification:** The candidate registers with an email address, verifies via a secure 6-digit OTP, or uses Google single sign-on.
2. **Document Ingestion:** The candidate uploads their resume. The backend synchronously parses the text, extracts competencies, generates 768-dimensional embeddings, and stores them in Neon pgvector.
3. **Accessibility Profiling:** The candidate records voluntary accommodation needs (e.g., screen reader compatibility, captions, flexible work hours, low-sensory environment).
4. **AI-Powered Discovery:** The candidate explores jobs ranked strictly by professional compatibility. Each card displays transparent accommodation badges (`AVAILABLE`, `ON_REQUEST`, `NOT_SPECIFIED`, `UNAVAILABLE`).
5. **Application & Request:** The candidate applies with one click and can attach an interview accommodation request directly to the employer's inbox.

---

### Employer Journey

```mermaid
flowchart TD
    A[Employer Portal] --> B[Register with Verified Corporate Domain]
    B --> C[Verify Email via OTP]
    C --> D[Employer Dashboard]
    D --> E[Configure Company Accessibility Capabilities]
    D --> F[Create Structured Job Posting OR Upload Job Description PDF]
    F --> G[Synchronous Requirement Extraction & Vector Indexing]
    G --> H[Job Published to Inclusive Candidates]
    H --> I[Review Candidate Applications Dashboard]
    H --> J[Review Accommodation Requests Inbox]
    J --> K[Grant Accommodation or Suggest Alternative Arrangement]
    I --> L[Update Candidate Hiring Stage]
```

1. **Domain Verification:** Employers register using verified corporate domains (disposable email domains are blocked).
2. **Capability Setup:** Employers specify their workplace facilities (wheelchair ramps, quiet rooms, screen-reader-certified tools, captioning).
3. **Job Publishing:** Employers can either fill out a structured job posting form or upload an existing job description document (PDF/DOCX). The automated pipeline extracts requirements and indexes dense vectors.
4. **Talent Management:** Employers review incoming applications, read candidate cover notes, and manage interview accommodation requests with transparent audit logs.

---

## 10. Testing and Quality Assurance

NexAbility enforces a comprehensive testing regime across frontend, backend, and machine learning components.

### 1. Frontend Test Suite
The frontend utilizes the Node.js native test runner (`node --test`) to test authorization normalization, client-side RBAC guards, matching utilities, and API service contracts:

```bash
cd frontend
npm test
```
**Test Results:** 23 tests across 7 suites passing with 0 failures:
- `auth-and-roles.test.js`: Case-insensitive role normalization (`CANDIDATE` -> `candidate`), unauthenticated redirect guards.
- `candidate-services.test.js`: File validation (size & MIME type), accessibility preference schema integrity.
- `employer-documents.test.js`: Document upload validation.
- `matching.test.js`: Verification of independent accessibility scoring without penalty.

### 2. Machine Learning Test Suite
The ML test suite covers document parsing, text chunking with full character coverage, E5 embeddings, fallback tokenizers, and matching accuracy:

```bash
cd ml
# Using backend virtual environment
..\backend\.venv\Scripts\python.exe -m pytest tests -q
```
**Test Results:** 112 passed, 2 skipped (live external Groq integration tests intentionally skipped when API key is unset).

### 3. Backend Test Suite
```bash
cd backend
pytest tests/unit -q
pytest tests/api -q
pytest tests/integration -q
```

### 4. Code Formatting & Linting
```bash
# Backend linting & format checks
cd backend
ruff check app tests
ruff format --check app tests

# Frontend linting
cd frontend
npm run lint

# Frontend production build verification
npm run build
```

---

## 11. Accessibility and Inclusivity

NexAbility is designed from the ground up to comply with **WCAG 2.2 Level AA** standards:

### 1. Non-Penalizing Match Framework
- **0–100% Professional Score:** Based strictly on demonstrated skills, qualifications, and semantic relevance.
- **Independent Accommodation Breakdown:** Missing employer capabilities are explicitly designated as `NOT_SPECIFIED – Inquire with employer`. They are **never** marked as `UNAVAILABLE` and do not reduce the match percentage.

### 2. Privacy-Guaranteed Disability Self-Declaration
- Voluntary declaration is 100% optional.
- Paperwork, medical diagnoses, and doctor forms are strictly prohibited from being requested.
- Declarations can be updated or completely withdrawn at any time via a single click (`DELETE /api/v1/candidates/me/declaration`).

### 3. UI/UX Accessibility Standards
- **Color Contrast:** All text, badges, and controls meet or exceed the 4.5:1 contrast ratio (7:1 for headers).
- **Keyboard Navigation:** Full focus trap management in modals, visible focus indicators (`:focus-visible`), and logical tab ordering.
- **Screen Reader Support:** Semantic HTML5 landmarks (`<main>`, `<header>`, `<article>`, `<nav>`), ARIA labels on dynamic elements, and live regions for status updates.

---

## 12. Development Workflow

### Git & Branching Strategy
- **`main`**: Production-ready branch. Direct pushes are restricted.
- **`feature/<feature-name>`**: Development of new features.
- **`fix/<bug-name>`**: Bug fixes and patch resolutions.

### Contribution Guidelines
1. Fork or clone the repository into your local development environment.
2. Create a dedicated feature branch (`git checkout -b feature/interview-scheduler`).
3. Ensure all frontend and backend tests pass before committing:
   ```bash
   cd frontend && npm test
   cd ../ml && pytest tests -q
   ```
4. Adhere to Ruff formatting rules for Python (`ruff format app tests`) and ESLint for JavaScript.
5. Submit a Pull Request targeting `main`. Include a clear description of changes, screenshots of UI updates, and test confirmation.

---

## 13. Future Enhancements

The following roadmap items represent planned platform extensions:

1. **L4 Agent Coordinator & Orchestration Loop:**
   - Integration of multi-specialist agents (Candidate Intelligence Specialist, Job Matching Specialist, Accommodation Specialist) with controlled tool access and human-in-the-loop approval gates.
2. **L5 Accessible Video Interviewing:**
   - In-browser WebRTC video room integration featuring real-time automated speech-to-text live captions and sign-language interpretation support.
3. **Enterprise ATS Synchronization:**
   - Bidirectional candidate and accommodation export conforming to SAP SuccessFactors and Workday HR integration APIs.
4. **Enhanced OCR Processing:**
   - Optional local OCR for scanned paper resumes and image-based job postings using Tesseract or AWS Textract.

---
