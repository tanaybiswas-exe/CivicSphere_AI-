<div align="center">

# 🛡️ নাগরিক বন্ধু (NagorikBondhu) • CivicSphere AI
### AI-Powered Citizen Assistance, Civic Grievance Drafting & Public Transparency Platform for Bangladesh

[![Live Demo](https://img.shields.io/badge/Live_Demo-Vercel-047857?style=for-the-badge&logo=vercel&logoColor=white)](https://civic-sphere-ai-ccog.vercel.app)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/Database-Neon_PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech/)
[![OpenAI](https://img.shields.io/badge/AI_Engine-OpenAI_GPT--4o--mini-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)
[![License](https://img.shields.io/badge/License-MIT-amber?style=for-the-badge)](LICENSE)

*An independent civic-tech initiative bridging the gap between everyday citizens and public service delivery in Bangladesh through Bangla-first AI, geospatial deduplication, and transparent cost auditing.*

</div>

---

## 📌 Problem Statement

Millions of citizens in Bangladesh face everyday civic challenges—damaged roads, waterlogging, uncollected waste, broken streetlights, consumer overcharging, and bureaucratic complexity—yet struggle with:
1. **Drafting Formal Complaints:** Not knowing which government authority or legal framework applies to a specific civic issue.
2. **Fragmented Tracking:** Losing track of complaint progress, updates, and formal copies after drafting.
3. **Duplicate Reporting:** Multiple uncoordinated reports for the exact same street-level hazard without priority aggregation.
4. **Public Cost & Rights Opacity:** Difficulty verifying local infrastructure Bill of Quantities (BOQ) against standard LGED/PWD rates or calculating statutory consumer rights rewards.
5. **Dense Policy Documents:** Navigating lengthy government PDF circulars to extract actionable instructions.

---

## 💡 Our Solution

**নাগরিক বন্ধু (NagorikBondhu / CivicSphere AI)** unifies civic grievance drafting, geospatial hazard mapping, public expenditure auditing, and Bangla AI guidance into a single, mobile-responsive web application.

> **Transparency Disclaimer:** *NagorikBondhu is an independent citizen assistance and civic-tech prototype. It is not an official government portal and does not claim direct API submission to government ministries.*

---

## ✨ Key Features

| Module | Capability & Impact |
| :--- | :--- |
| **✍️ AI Complaint Generator** | Takes district, area, category, landmark, photo/file evidence, and Bangla/English problem descriptions to automatically identify the responsible authority, cite relevant Bangladeshi laws, and generate an editable, downloadable, and printable formal complaint letter. |
| **📋 Smart Complaint Tracker** | Assigns unique tracking IDs (`NB-2026-XXXX`), tracks lifecycle stages (`Draft` → `Submitted` → `In Progress` → `Resolved`), and maintains a timestamped status history modal. |
| **🗺️ Geospatial Issue Map** | Interactive Leaflet map with category/status filters, click-to-pin coordinates, **100-meter Haversine duplicate detection**, and community **Upvoting** to surface high-priority hazards. |
| **💬 Bangla AI Citizen Assistant** | Conversational assistant answering civic and public-service queries in Bangla/English with verified official government portal links (`bdris.gov.bd`, `grs.gov.bd`, `bangladesh.gov.bd`). |
| **📄 PDF Document Assistant** | Client-side `PDF.js` extraction paired with AI/keyword Q&A to retrieve grounded references directly from uploaded government circulars and forms without hallucination. |
| **💰 Public Project BOQ Audit** | Compares contractor quoted unit rates against **LGED** and **PWD** schedule benchmarks, flagging items exceeding a **>20% variance threshold** alongside budget variance metrics. |
| **🏷️ Consumer Rights Calculator (16121)** | Calculates overcharge amount, percentage markup above MRP, and the statutory **25% citizen whistleblower reward** under the Consumer Rights Protection Act, 2009. |
| **🛡️ Anti-Corruption & Portal Directory** | Highlights whistleblower protection (Act 2011), ACC helpline (`106`), emergency helplines (`999`, `333`), and verified national service portals. |
| **👤 Citizen Profile & Admin Analytics** | Cross-device Neon PostgreSQL authentication, full citizen profile view/edit, interactive Chart.js analytics, audit logs, and clickable registered user inspection for admins. |

---

## 🏗️ System Architecture

```text
┌──────────────────────────────────────────────────────────────────────┐
│                   Frontend (Responsive SPA / Mobile Drawer)          │
│   HTML5 • Tailwind CSS • Leaflet.js • Chart.js • PDF.js • Vanilla JS │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │ REST API (JSON / Multipart)
┌──────────────────────────────────▼───────────────────────────────────┐
│                     Backend (Python FastAPI)                         │
│  • Auth & Profile Management   • Haversine 100m Geo-Deduplication    │
│  • AI Complaint & Chat Engine  • LGED / PWD BOQ Variance Engine      │
└───────────────┬──────────────────────────────────┬───────────────────┘
                │                                  │
┌───────────────▼───────────────┐  ┌───────────────▼───────────────────┐
│   Neon Serverless PostgreSQL  │  │        OpenAI REST API            │
│  (Users, Complaints, Hazards, │  │  (gpt-4o-mini Bangla Civic NLP    │
│   Audit Logs, Govt Services)  │  │   with Deterministic Fallbacks)   │
└───────────────────────────────┘  └───────────────────────────────────┘
