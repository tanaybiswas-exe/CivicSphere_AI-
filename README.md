<div align="center">

# 🛡️ নাগরিক বন্ধু (NagorikBondhu) • CivicSphere AI
### AI-Powered Citizen Assistance, Civic Grievance Drafting & Public Transparency Platform for Bangladesh

[![Live Demo](https://img.shields.io/badge/Live_Demo-Vercel-047857?style=for-the-badge&logo=vercel&logoColor=white)](https://civic-sphere-ai-ccog.vercel.app)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/Database-Neon_Serverless_PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech/)
[![OpenAI](https://img.shields.io/badge/AI_Engine-OpenAI_GPT--4o--mini-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)
[![Leaflet](https://img.shields.io/badge/GIS_Mapping-Leaflet.js-199900?style=for-the-badge&logo=leaflet&logoColor=white)](https://leafletjs.com/)
[![License](https://img.shields.io/badge/License-MIT-amber?style=for-the-badge)](LICENSE)

*An independent civic-tech initiative bridging the gap between everyday citizens and public service delivery in Bangladesh through Bangla-first AI, 100-meter geospatial deduplication, grounded PDF circular analysis, and transparent infrastructure cost auditing.*

[Live Application](https://civic-sphere-ai-ccog.vercel.app) • [Key Features](#-key-features) • [System Architecture](#-system-architecture) • [API Reference](#-api-endpoints-reference) • [Local Setup](#-local-setup--installation)

</div>

---

## 📌 Problem Statement

Millions of citizens in Bangladesh encounter everyday municipal and public service friction—damaged roads, waterlogging, uncollected waste, broken streetlights, consumer overcharging, and bureaucratic opacity—yet face five systemic barriers:

1. **Drafting Formal Complaints:** Citizens often do not know which ministry, city corporation, or statutory law applies to a specific civic grievance, nor how to structure an official Bangla application.
2. **Fragmented Lifecycle Tracking:** Once drafted, formal copies and status updates (`Draft` → `Submitted` → `In Progress` → `Resolved`) are easily lost without a unified tracking mechanism.
3. **Unaggregated Duplicate Reporting:** Multiple residents report the exact same street-level hazard independently, diluting urgency instead of aggregating community priority.
4. **Public Expenditure & Consumer Opacity:** Citizens and local observers lack accessible tools to benchmark local road/culvert Bill of Quantities (BOQ) against **LGED/PWD** schedule rates or compute statutory **25% whistleblower rewards** under consumer law.
5. **Dense Government Circulars:** Extracting actionable steps from lengthy government PDF guidelines is time-consuming and prone to misinterpretation.

---

## 💡 Our Solution

**নাগরিক বন্ধু (NagorikBondhu / CivicSphere AI)** unifies Bangla AI grievance drafting, geospatial hazard mapping, public expenditure auditing, and verified government service directories into a single, mobile-first web application backed by **Neon Serverless PostgreSQL** and **FastAPI**.

> **Governance & Transparency Disclaimer:** *NagorikBondhu is an independent citizen assistance and civic-tech prototype. It is not an official government website and does not claim direct API submission to government ministries; all generated applications are clearly labeled as citizen drafts with direct links to official portals (`grs.gov.bd`, `bdris.gov.bd`, `dncrp.gov.bd`, `acc.org.bd`).*

---

## ✨ Key Features & Core Modules

| Module | Technical Capability & Civic Impact |
| :--- | :--- |
| **✍️ AI Complaint Generator** | Accepts district, area/upazila, category, landmark, photo/PDF evidence upload, and Bangla/English problem descriptions. Automatically maps the issue to the responsible authority, cites relevant Bangladeshi laws, and generates an editable, downloadable (`.txt`), and printable formal application. |
| **📋 Smart Complaint Tracker** | Generates unique tracking IDs (`NB-2026-XXXX`), enables lifecycle stage updates (`Draft`, `Submitted`, `In Progress`, `Resolved`), and maintains a JSON-backed timestamped status history modal. |
| **🗺️ Geospatial Issue Map** | Interactive Leaflet.js map supporting category & status filtering, click-to-pin coordinates, **100-meter Haversine duplicate detection**, and community **Upvoting** to elevate critical local hazards. |
| **💬 Bangla AI Citizen Assistant** | Bilingual (Bangla/English) conversational assistant powered by OpenAI `gpt-4o-mini` with deterministic rule-based fallbacks and curated official government portal citations. |
| **📄 Grounded PDF Assistant** | Client-side `PDF.js` multi-page text extraction paired with AI/keyword retrieval to answer questions strictly from uploaded government documents—eliminating hallucinated policy claims. |
| **💰 Public Project BOQ Audit** | Benchmarks contractor quoted unit rates against official **LGED** and **PWD** schedule rates for earthwork, brick soling, RCC concrete, MS rebar, and bituminous carpeting—flagging any item exceeding a **>20% variance threshold**. |
| **🏷️ Consumer Rights Calculator (`16121`)** | Computes overcharge amount, percentage markup above MRP, and the statutory **25% citizen reward** under the Consumer Rights Protection Act, 2009. |
| **🛡️ Anti-Corruption & Portal Directory** | Educates citizens on the Public-Interest Information Disclosure (Provide Protection) Act, 2011, ACC helpline (`106`), national emergency helplines (`999`, `333`), and verified service portals. |
| **👤 Citizen Profile & Admin Analytics** | Cross-device Neon PostgreSQL authentication (email or 11-digit BD mobile), full citizen profile view/edit, interactive Chart.js analytics, audit ledger, and clickable registered user inspection for administrators. |

---

## 🏗️ System Architecture

```text
┌────────────────────────────────────────────────────────────────────────────┐
│               Client Layer (Mobile-First Responsive Web App)               │
│   HTML5 • Tailwind CSS • Leaflet.js • Chart.js • PDF.js • Vanilla ES6+     │
└────────────────────────────────────┬───────────────────────────────────────┘
                                     │ HTTPS REST API (JSON & Multipart Form)
┌────────────────────────────────────▼───────────────────────────────────────┐
│                   Application Layer (Python FastAPI)                       │
│  • Cross-Device Auth & Profile API   • 100m Haversine Geo-Deduplicator     │
│  • Bangla Civic NLP & Draft Engine   • LGED / PWD BOQ Variance Auditor     │
│  • Grounded PDF Reference Retriever  • Role-Aware Audit Logger             │
└──────────────────┬─────────────────────────────────────┬───────────────────┘
                   │ psycopg2 (SSL)                      │ HTTPS REST
┌──────────────────▼──────────────────┐   ┌──────────────▼───────────────────┐
│   Neon Serverless PostgreSQL        │   │        OpenAI Chat API           │
│  • users         • complaints       │   │  • Model: gpt-4o-mini            │
│  • hazards       • audit_logs       │   │  • Deterministic Fallback Layer  │
│  • govt_services                    │   │                                  │
└─────────────────────────────────────┘   └──────────────────────────────────┘
```

---

## 🧠 Core Engineering Logic & Algorithms

1. **100-Meter Geospatial Deduplication (Haversine Formula):**
   When a citizen pins a new hazard at $(\phi_1, \lambda_1)$, the backend computes the great-circle distance $d$ against all active pins $(\phi_2, \lambda_2)$:
   $$d = 2R \cdot \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)}\right), \quad R = 6371\text{ km}$$
   If $d \le 100\text{ m}$, the system halts duplicate creation and prompts the user to **Upvote** the existing report instead.

2. **BOQ Cost Variance & Anomaly Detection:**
   For each construction line item $i$ with quantity $Q_i$, quoted unit rate $R_{\text{quoted}, i}$, and agency schedule benchmark $R_{\text{std}, i} \in \{\text{LGED}, \text{PWD}\}$:
   $$\text{Variance}_i (\%) = \left(\frac{R_{\text{quoted}, i} - R_{\text{std}, i}}{R_{\text{std}, i}}\right) \times 100$$
   Any item where $\text{Variance}_i > 20\%$ triggers an automated anomaly alert.

3. **Anti-Hallucination Document Guardrail:**
   The PDF Document Assistant enforces strict context grounding—if no PDF is uploaded or no matching clause exists in the extracted text, the system explicitly declines to speculate rather than fabricating administrative rules.

---

## 🗄️ Database Schema (Neon PostgreSQL)

- **`users`**: `id`, `full_name`, `email` (unique), `phone`, `password_hash` (SHA-256), `nid_number` (unique), `dob`, `role` (`Citizen` / `Admin`), `is_verified`, `created_at`
- **`complaints`**: `id`, `tracking_id` (`NB-2026-XXXX`), `citizen_nid`, `external_ref`, `domain`, `department`, `district`, `area`, `description`, `draft_text`, `status`, `status_history` (JSON), `evidence_note`, `created_at`
- **`hazards`**: `id`, `title`, `category`, `lat`, `lng`, `upvotes`, `status`, `created_at`
- **`govt_services`**: `id`, `service_name`, `ministry`, `fee`, `sla_timeline`, `portal_url`, `last_auto_synced`
- **`audit_logs`**: `id`, `actor_role`, `action`, `target_id`, `timestamp`

---

## 🔌 API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Register a new citizen with Gmail, 11-digit BD phone & NID validation |
| `POST` | `/api/auth/login` | Authenticate via email or phone number across devices |
| `POST` | `/api/auth/profile` | Retrieve full citizen profile metadata |
| `POST` | `/api/auth/update-profile` | Update name, phone, NID, DOB, and password |
| `POST` | `/api/chat` | Bangla/English civic assistant with verified portal links |
| `POST` | `/api/assistant/analyze` | Classify issue, map authority/law, and draft formal complaint |
| `POST` | `/api/upload-evidence` | Upload image/PDF evidence attachment |
| `GET` / `POST` | `/api/complaints` | List all complaints or save a new complaint with tracking ID |
| `PATCH` | `/api/complaints/{tracking_id}/status` | Update complaint stage & append timestamped history |
| `GET` / `POST` | `/api/hazards` | Fetch map hazards or pin a new hazard with 100m duplicate check |
| `POST` | `/api/hazards/{hazard_id}/upvote` | Upvote an existing geospatial hazard |
| `POST` | `/api/doc/ask` | Grounded Q&A over extracted PDF document text |
| `GET` / `POST` | `/api/boq/rates` & `/api/boq/audit` | Retrieve LGED/PWD rates and audit project BOQ line items |
| `GET` | `/api/services` | Fetch verified government portal directory |
| `GET` | `/api/admin/analytics` | Retrieve KPI metrics, Chart.js distributions, user list & audit logs |

---

## 📂 Repository Structure

```text
├── main.py                 # FastAPI backend, Neon PostgreSQL schema, AI & Audit endpoints
├── static/
│   └── index.html          # Main responsive UI, Leaflet maps, Chart.js & PDF.js client
├── requirements.txt        # Python dependencies
├── vercel.json             # Vercel serverless routing configuration
├── .gitignore              # Environment & cache exclusions
└── README.md               # Project documentation
```

---

## 🚀 Local Setup & Installation

### Prerequisites
- Python 3.10 or higher
- PostgreSQL connection string (Neon PostgreSQL supported out of the box)

### Step-by-Step Guide

1. **Clone the repository**
   ```bash
   git clone [https://github.com/tanaybiswas-exe/CivicSphere-AI.git](https://github.com/tanaybiswas-exe/CivicSphere-AI.git)
   cd CivicSphere-AI
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables (`.env`)**
   Create a `.env` file in the project root:
   ```env
   DATABASE_URL=postgresql://<user>:<password>@<host>/neondb?sslmode=require
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_MODEL=gpt-4o-mini
   ```

4. **Run the FastAPI Server**
   ```bash
   python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

5. **Access the Application**
   Open `http://127.0.0.1:8000` in your browser.

---

## 🔑 Demo Credentials (For Judges & Evaluators)

| Role | Email / Identifier | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Citizen** | `tanay4@gmail.com` | `123456` | Complaint drafting/saving, hazard pinning, profile editing |
| **Admin** | `admin@civicsphere.gov.bd` | `admin123` | Full analytics dashboard, clickable user directory & audit ledger |

---

## 🗺️ Future Roadmap

- **Direct GRS / DNCRP API Integration:** Official webhook and e-Nothi submission pipelines upon institutional partnership.
- **Bangla Voice-to-Complaint (ASR):** Speech-to-text grievance input for citizens with limited typing literacy.
- **Automated SMS / WhatsApp Status Alerts:** Real-time tracking notifications when complaint stages transition.

---
