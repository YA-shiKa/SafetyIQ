# SafetyIQ

**AI-Powered Industrial Safety Intelligence Platform**

Zero-Harm Operations through Compound Risk Detection, Geospatial Analytics & Autonomous Emergency Response

`Industrial Intelligence` · `Worker Safety` · `Geospatial Safety Analytics`

Industrial Intelligence Track — Zero-Harm Operations

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Problem Context](#problem-context)
- [Solution Architecture](#solution-architecture)
- [The Five AI Agents](#the-five-ai-agents)
- [Technical Stack](#technical-stack)
- [Key Features & Impact](#key-features--impact)
- [Evaluation Metrics](#evaluation-metrics)
- [Regulatory Compliance Coverage](#regulatory-compliance-coverage)
- [Project File Structure](#project-file-structure)
- [Setup & Deployment](#setup--deployment)
- [Team](#team)

---

## Executive Summary

India records over **6,500 fatal workplace accidents annually** (DGFASLI FY2023). The Visakhapatnam Steel Plant tragedy of January 2025 — eight workers killed by entrapped gas explosion — exposed the defining failure of modern industrial safety: **data was present, but no intelligence layer connected it to decisions in time.**

**The Problem:** Over 60% of large Indian industrial facilities rely on manual handoffs to coordinate between digital safety tools (FICCI 2024). The failure is not absence of technology — it is absence of a unified intelligence layer.

**The Solution:** SafetyIQ closes this gap. It is an AI-powered Industrial Safety Intelligence platform that fuses data from IoT sensors, SCADA systems, permit-to-work logs, CCTV feeds, and shift records into a single predictive layer — detecting compound risk conditions hours before they escalate, and acting autonomously when they do.

---

## Problem Context

### The Data-Decision Gap

Modern heavy industrial plants are not data-poor. A typical Indian steel plant operates hundreds of gas detectors, SCADA endpoints, PTW records, and CCTV feeds simultaneously. The Visakhapatnam investigation found warning signals from gas pressure sensors existed before the explosion — but no intelligence layer connected those readings to operational decisions in time.

- **6,500+** fatal workplace accidents in India — FY2023 (DGFASLI)
- **60%+** of large facilities rely on manual handoffs between digital safety tools (FICCI 2024)
- **8 workers killed** at Vizag Steel Plant, January 2025 — sensors were active, action was not
- **Pattern repeats:** data present, unacted upon — across Indian steel, refinery, and mining sectors

### Why Single-Sensor Systems Fail

Individual sensors flag individual thresholds. They cannot detect **compound risk** — the dangerous co-occurrence of multiple factors that individually appear manageable but together are lethal. The Vizag explosion was not caused by a single sensor exceeding a threshold. It was caused by:

- Gas pressure sensors showing elevated readings (present)
- Maintenance workers inside the coke oven battery (present)
- Shift changeover reducing situational awareness (present)
- No system correlating all three into a compound risk event (**absent**)

> **Core Insight:** The intelligence layer that would have saved those eight lives did not need new sensors. It needed a system that connected the sensors that already existed.

---

## Solution Architecture

### Platform Overview

SafetyIQ is a multi-agent AI platform with five specialized agents, a unified risk engine, a real-time geospatial heatmap, and an autonomous emergency orchestrator. Every component is designed for one measurable outcome: **reducing the false-negative rate** — the metric that actually saves lives.

### System Architecture

| Layer | Components | Technology |
|---|---|---|
| **Data Ingestion** | IoT Sensors, SCADA Systems, CCTV Feeds, PTW Records, Shift Logs | MQTT, WebSocket, REST APIs |
| **AI Agent Layer** | Compound Risk Agent, Permit Intel Agent, Emergency Orchestrator, Incident RAG Agent, Compliance Agent | Claude claude-sonnet-4-6, LangChain, Multi-agent orchestration |
| **Intelligence Layer** | Geospatial Heatmap, Unified Risk Engine, Regulatory Compliance Monitor | FastAPI, Redis, PostgreSQL, ChromaDB |
| **Presentation Layer** | React Dashboard, Live Alerts, Permit Center, Incident Hub, Compliance View | React 18, TypeScript, Recharts, Leaflet.js |

---

## The Five AI Agents

### 1. Compound Risk Detection Engine
The core agent. Correlates gas sensor readings, work permit activity, equipment maintenance status, and shift changeover patterns to identify dangerous combinations hours before they become critical.

- Rule engine identifies structural risk combinations (fast, deterministic)
- Claude AI layer provides contextual analysis, severity scoring, and predicted escalation timeline
- Detects: confined space entry + gas accumulation, hot work + flammable gas proximity, oxygen deficiency + active permits, SIMOPs conflicts, shift changeover + unresolved hazards
- **Output:** `CompoundRiskEvent` with risk level, confidence score, lead time, and regulatory citations

### 2. Digital Permit Intelligence Agent
Validates every permit-to-work request against live plant conditions before issuance. Checks OISD 105 mandatory checklists, atmospheric sensor readings, and simultaneous operations conflicts.

- OISD 105 Section 4.3 checklist: 12-point confined space, 8-point hot work validation
- Real-time sensor cross-reference: blocks permits when O₂ < 19.5% or H₂S ≥ 10ppm
- SIMOPs analysis: flags dangerous concurrent operations (e.g. hot work + confined space within 25m)
- **Returns:** `APPROVED` / `CONDITIONAL` / `SUSPENDED` / `DENIED` with regulatory basis

### 3. Emergency Response Orchestrator
Autonomous agent that, on confirmed trigger, transforms the critical first 10 minutes from chaos to coordinated response. Executes four parallel tracks simultaneously.

- **Track 1 — Evacuation:** PA broadcast to affected and adjacent zones
- **Track 2 — Notifications:** SMS + email to safety officer, hospital, fire station, DGFASLI
- **Track 3 — Evidence:** Locks 48-hour sensor snapshot, CCTV footage, permit archive
- **Track 4 — SCADA Lockdown:** Suspends all active permits, initiates emergency shutdown
- Generates preliminary **DGFASLI Form 18** regulatory incident report within 60 seconds

### 4. Incident Pattern Intelligence (RAG)
RAG-powered agent that cross-references near-miss reports, historical incident data, and OISD/Factory Act regulatory guidance to identify recurring patterns that manual investigations miss.

- ChromaDB vector store with historical incident corpus from Indian steel/refinery sector
- Regulatory corpus: OISD 105, 116, 118 | Factory Act 1948 | DGMS Circulars | DGFASLI Form 18 archives
- Semantic pattern matching: identifies current conditions against historical incident signatures
- **Output:** `PatternMatch` with recurrence count, severity potential, regulatory gaps, prevention priorities

### 5. Quality & Compliance Audit Agent
Continuously monitors safety procedures, inspection records, and statutory compliance documentation against OISD, DGMS, and Factory Act 1948 standards.

- 11 automated compliance checks across OISD / Factory Act / DGMS frameworks
- Scores each framework independently: OISD score, Factory Act score, DGMS score
- Flags: overdue PRV inspections, expired calibration, missing isolation certificates, SCBA shortfalls, overdue rescue drills
- Generates corrective action workflows with responsible officer and resolution deadlines

---

## Technical Stack

### Backend

| Component | Technology | Purpose |
|---|---|---|
| API Server | FastAPI (Python 3.11+) | REST + WebSocket endpoints |
| AI Reasoning | Claude claude-sonnet-4-6 (Anthropic) | All agent reasoning and report generation |
| Agent Orchestration | LangChain | Multi-agent coordination |
| Vector Store | ChromaDB | RAG over incident and regulatory corpus |
| Real-time State | Redis | Sensor state cache, pub/sub for WebSocket broadcast |
| Time-series Data | PostgreSQL + TimescaleDB | Sensor history, audit logs |
| IoT Ingestion | MQTT (Paho) | Live sensor data from plant floor |
| Configuration | pydantic-settings | Typed env-var config with `.env` support |

### Frontend

| Component | Technology | Purpose |
|---|---|---|
| UI Framework | React 18 + TypeScript | Main dashboard and all views |
| Data Visualization | Recharts | Sensor telemetry charts and risk trends |
| Geospatial Map | Leaflet.js | Plant layout heatmap with dynamic risk zones |
| Styling | TailwindCSS | Dark-mode industrial UI |
| State Management | Zustand | Global safety state store |
| API Client | Typed fetch service (`api.ts`) | All backend endpoint calls with full TypeScript types |
| WebSocket | Custom hook (`useSensorStream.ts`) | Live sensor stream with auto-reconnect |

---

## Key Features & Impact

| Feature | Description | Impact |
|---|---|---|
| Compound Risk Engine | Multi-signal correlation across sensors, permits, maintenance, and shift data | Detects risk hours before threshold breach |
| Geospatial Heatmap | Real-time plant layout with dynamic risk zones and worker location overlay | Full situational awareness across facility |
| Permit Intelligence | AI validates every PTW against live conditions and OISD 105 checklist | Blocks dangerous simultaneous operations |
| RAG Incident Patterns | Semantic search over historical incidents + regulatory corpus | Surfaces recurring patterns humans miss |
| Emergency Orchestrator | Autonomous evacuation, notification, evidence preservation, Form 18 | First 10 minutes: chaos → coordinated |
| Compliance Audit Agent | 11 automated checks across OISD/Factory Act/DGMS, continuous | Zero-gap audit trail; pre-audit gap closure |
| Unified Risk Engine | Single 0–100 plant risk score fusing all agent outputs | One number for the safety officer |

---

## Evaluation Metrics

### Judging Criteria Alignment

| Criterion | Weight | SafetyIQ Approach |
|---|---|---|
| Innovation | 25% | Multi-agent compound risk detection — no single-sensor system does this |
| Business Impact | 25% | Directly addresses 6,500+ annual fatalities; quantifiable FNR reduction |
| Technical Excellence | 20% | Rule engine + Claude AI layer + RAG pipeline + WebSocket streaming |
| Scalability | 15% | FastAPI + Redis + PostgreSQL — horizontal scaling ready |
| User Experience | 15% | Dark-mode React dashboard with live alerts, heatmap, and permit center |

### Performance Targets

| Metric | Target | How Achieved |
|---|---|---|
| Compound risk detection accuracy | >90% vs single-sensor baseline | Multi-agent correlation vs threshold-only |
| Prediction lead time | >2 hours before threshold breach | Trend analysis + pattern matching |
| False negative rate reduction | >60% vs manual monitoring | AI compound risk + RAG pattern intelligence |
| Regulatory coverage | OISD + Factory Act + DGMS | RAG over full regulatory corpus, 11 compliance checks |
| Emergency response time | <60 seconds to full orchestration | Parallel async tracks in `EmergencyOrchestrator` |
| WebSocket latency | <2 seconds sensor update | Redis pub/sub + asyncio broadcast loop |

---

## Regulatory Compliance Coverage

SafetyIQ covers the full set of standards specified in the hackathon brief:

| Standard | Sections Covered | Implementation |
|---|---|---|
| OISD 105 | 4.3 (PTW/Confined Space), 6.1 (Isolation), 7.2 (SIMOPs) | Permit Intel Agent + Compliance Agent |
| OISD 116 | 4.1 (SCBA/Respiratory), 5.2 (Gas Detector Calibration) | Compound Risk Agent + Compliance Agent |
| OISD 118 | 8.4 (Pressure Vessel/PRV Inspection) | Compliance Agent + Maintenance alerts |
| Factory Act 1948 | 36, 36A (Dangerous Fumes), 38 (Explosive Gas), 31 (Pressure Plants) | Compound Risk Agent + Permit Intel Agent |
| DGMS | Circular 2019-03 (Rescue Drills), Safety Officer Qualification | Compliance Agent |
| DGFASLI | Form 18 (Incident Notification) | Emergency Orchestrator (auto-generated) |

---

## Project File Structure

### Backend Agents
```
compound_risk_agent.py     # Multi-signal compound risk detection with rule engine + Claude AI layer
permit_intel_agent.py      # OISD 105 checklist validation + real-time sensor cross-reference
emergency_orchestrator.py  # Autonomous 4-track emergency response + DGFASLI Form 18 generation
incident_rag_agent.py      # ChromaDB RAG over incident corpus + regulatory clauses
compliance_agent.py        # 11 automated compliance checks across OISD/Factory Act/DGMS
```

### Backend Core
```
risk_engine.py             # Unified risk scoring fusing all agent outputs into PlantRiskSummary
config.py                  # pydantic-settings configuration with all environment variables
api/routes/sensors.py      # Sensor telemetry REST endpoints with alarm state, history, and acknowledgment
api/main.py                # FastAPI application with WebSocket broadcast loop
```

### Frontend
```
services/api.ts               # Fully typed API client for all 12 backend endpoints
hooks/useSensorStream.ts       # WebSocket hook with auto-reconnect, keepalive, O2-inverted alarm classification
components/AlertPanel.tsx      # Live alert feed with severity filtering, compound factor expansion, and acknowledgment
pages/Dashboard.tsx            # Main operations view wiring all components together
```

---

## Setup & Deployment

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL
- Redis
- (Optional) MQTT broker

### Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m uvicorn api.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(required)* | Claude API key for all AI agents |
| `DATABASE_URL` | `postgresql://localhost/safetyiq` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis for real-time state |
| `DEMO_MODE` | `true` | Use simulator instead of live SCADA/MQTT |
| `PLANT_NAME` | `Visakhapatnam Steel Complex` | Plant name in reports and notifications |
| `MQTT_BROKER_HOST` | `localhost` | MQTT broker for live IoT ingestion |

---

## Team

| Name | Role | Institution |
|---|---|---|
| Yashika | AI Engineering & Full-Stack Development | Bennett University, Greater Noida (B.Tech CS, 2023–2027) |

- **GitHub:** [github.com/YA-shiKa](https://github.com/YA-shiKa)
- **Portfolio:** [aiml-portfolio-gules.vercel.app](https://aiml-portfolio-gules.vercel.app)
- **Email:** myashika2005@gmail.com

---
