# MediTrack: AI-Powered Clinic Appointment No-Show Reconciliation & Triage

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2018%20+%20Vite-61DAFB.svg?logo=react&logoColor=black)](https://vitejs.dev)
[![Redis](https://img.shields.io/badge/Cache-Redis-DC382D.svg?logo=redis&logoColor=white)](https://redis.io)
[![Tests](https://img.shields.io/badge/Tests-22%20Passed%20(100%25)-success.svg)]()

> **Submission for AidenAI Build Round — AI Engineer**  
> **Candidate:** Utkarsh  
> **Application:** Outpatient clinic platform for daily appointment no-show reconciliation, calibrated ML attendance prediction, financial risk analytics, and proactive clinical triage.

---

## Table of Contents
1. [Overview & Problem Statement](#overview--problem-statement)
2. [System Architecture](#system-architecture)
3. [Machine Learning Pipeline & Cost Theory](#machine-learning-pipeline--cost-theory)
4. [High-Performance Caching (Redis + Fallback)](#high-performance-caching-redis--fallback)
5. [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
6. [Quick Start & Setup](#quick-start--setup)
7. [Automated Test Suite](#automated-test-suite)
8. [AI Usage Disclosure](#ai-usage-disclosure)

---

## Overview & Problem Statement

Outpatient clinic chains face an average **15% to 25% appointment no-show rate**, resulting in wasted specialist hours, delayed patient care, and lost revenue (~**$120/unfilled slot**).

**MediTrack delivers an end-to-end operational solution:**
- **Daily Reconciliation:** Fast one-click attendance logging (`ATTENDED` / `NO_SHOW`) with notes and audit trails.
- **Predictive ML Triage:** Real-time calibrated no-show probabilities (0–100%) and automated intervention recommendations.
- **Financial Analytics:** Daily executive report comparing predicted vs. actual no-shows and revenue at risk.
- **High-Performance Caching:** Sub-millisecond response caching using **Redis** with in-memory fallback and live telemetry HUD.
- **RBAC Security:** Strict boundary enforcement separating `CLINIC_STAFF` from `CLINIC_MANAGER`.

---

## System Architecture

```
                       +---------------------------------------+
                       |         React 18 + Vite SPA           |
                       |  - Dark Glassmorphic Dashboard        |
                       |  - Live Cache Telemetry HUD (Redis)   |
                       |  - Persona / RBAC Role Switcher       |
                       +-------------------+-------------------+
                                           |  REST API (JSON)
                                           v
                       +---------------------------------------+
                       |         FastAPI Backend               |
                       |  - Pydantic v2 Request Validation     |
                       |  - RBAC Policy Enforcer               |
                       +---------+-------------------+---------+
                                 |                   |
          +----------------------+                   +---------------------+
          v                                                                v
+-----------------------------------+                            +-----------------------------------+
|     Redis Distributed Cache       |                            |       ML Inference Engine         |
| - Process-shared sub-ms lookups   |                            | - Calibrated GradientBoosting     |
| - In-memory fallback on failure   |                            | - Feature Extraction Pipeline     |
| - Prefix invalidation on writes   |                            | - Tri-Level Clinical Triage       |
+-----------------+-----------------+                            +-----------------+-----------------+
                  | (Cache Miss)                                                   | (Model Artifacts)
                  v                                                                v
+-----------------------------------+                            +-----------------------------------+
|      SQLite Persistence (WAL)     |                            |      Joblib Model Store           |
| - Concurrent Read/Write Pragma    |                            | - no_show_model.joblib            |
| - Indexed (clinic_id, date, status)|                           | - model_metrics.json              |
+-----------------------------------+                            +-----------------------------------+
```

- **Frontend:** React 18 SPA (Vite + Vanilla CSS) with zero bloated component libraries.
- **Backend:** FastAPI with asynchronous request handlers and Pydantic v2 data models.
- **Database:** SQLite configured with `PRAGMA journal_mode=WAL` and `synchronous=NORMAL` for concurrent reads/writes without table lockups.
- **Cache:** Redis caching with sub-millisecond retrieval, single-flight coalescing, and transparent fallback to an in-memory $O(1)$ LRU cache.

---

## Machine Learning Pipeline & Cost Theory

### 1. Model Selection & Performance
Trained on 15,000 outpatient visit records with domain-specific features (80/20 stratified split; executable via `PYTHONPATH=backend python3 backend/app/ml/benchmark.py`):

| Model Architecture | Holdout ROC-AUC | Brier Score (Calibration) | Latency | Interpretability |
| :--- | :---: | :---: | :---: | :--- |
| **Calibrated Gradient Boosting (Selected)** | **0.7878** | **0.1033** | **0.81 ms** | **High** (Tree MDI importances) |
| Logistic Regression | 0.7861 | 0.1023 | 0.35 ms | Very High (Linear odds) |
| Deep Neural Net (MLP) | 0.7312 | 0.1132 | 0.36 ms | Low (Black box) |

### 2. Primary Risk Drivers
1. **`prior_no_show_ratio` (41.6%):** Past patient attendance history is the dominant predictor.
2. **`lead_days` (17.8%):** Time between booking and visit; $>14$ days sharply spikes no-show likelihood.
3. **`age` (11.1%):** Young adults (18–28) miss more appointments; seniors (65+) attend reliably.
4. **`sms_reminder` (10.7%):** Active 24h & 2h reminders reduce no-show odds by ~35%.

### 3. Cost-Sensitive Bayesian Threshold ($\tau^{\ast} = 0.25$)
In clinic operations, false negatives are far more costly than false positives:
- **Cost of False Negative ($C_{\text{FN}} = \$120$):** Unfilled doctor slot, empty exam room, permanent lost revenue.
- **Cost of False Positive ($C_{\text{FP}} = \$40$):** Proactive staff outreach / standby preparation for a patient who attends.

Under **Bayesian Risk Minimization**, the optimal intervention threshold is:
$$
\tau^{\ast} = \frac{C_{\text{FP}}}{C_{\text{FP}} + C_{\text{FN}}} = \frac{40}{40 + 120} = \mathbf{0.25}
$$
Lowering the threshold from the default $0.50$ to the Bayes optimal $\mathbf{0.25}$ more than doubles test-set Recall (**18.8% $\rightarrow$ 45.0%**) and minimizes total operational loss.

### 4. Tri-Level Operational Triage
- **Low Risk ($P < 25\%$):** Standard automated SMS reminder 24h prior ($\approx \$0.05$).
- **Medium Risk ($25\% \le P < 50\%$):** Automated two-way WhatsApp interactive confirmation prompt ($\approx \$0.10$).
- **High Risk ($P \ge 50\%$):** Manual coordinator phone call, transport assistance, and standby buffer activation ($\approx \$40$).

---

## High-Performance Caching (Redis + Fallback)

1. **Redis Cache Layer (`backend/app/core/cache.py`):**
   - Connects to **Redis** (`redis://127.0.0.1:6379/0`) for process-shared, sub-millisecond caching.
   - Dual-mode serialization: Clean JSON for readable inspection in `redis-cli`, with automatic pickle fallback.
   - Single-flight request coalescing (`get_or_compute`) to prevent cache stampedes / thundering herds under concurrent load.
   - **Automatic Fallback:** Gracefully degrades to a local thread-safe $O(1)$ LRU cache with monotonic TTL if Redis is unreachable.
2. **Write-Through Prefix Invalidation:**
   - Any appointment creation or status reconciliation automatically invalidates `appointments:*` and `reports:*` keys to guarantee fresh data.
3. **Live Telemetry HUD:**
   - Real-time display of cache state (`[REDIS]` or `[IN_MEMORY]`), Hits, Misses, Hit Ratio %, and estimated Latency Saved.
4. **Manager-Only Flush:**
   - Role-restricted endpoint (`POST /api/v1/cache/clear`) allows clinic managers to flush cache on demand.

---

## Role-Based Access Control (RBAC)

Enforced via FastAPI dependency injection (`require_roles`):

| Capability | `CLINIC_STAFF` | `CLINIC_MANAGER` |
| :--- | :---: | :---: |
| View Appointments & Schedule | ✅ Allowed | ✅ Allowed |
| Create New Appointments | ✅ Allowed | ✅ Allowed |
| Reconcile No-Show Statuses | ✅ Allowed | ✅ Allowed |
| View Daily Summary Reports | ✅ Allowed | ✅ Allowed |
| **Inspect Staff Audit Trail** | ❌ **403 Forbidden** | ✅ **Allowed** |
| **Flush System Cache** | ❌ **403 Forbidden** | ✅ **Allowed** |
| **Trigger Model Retraining** | ❌ **403 Forbidden** | ✅ **Allowed** |

*The top header includes a one-click persona switcher to test both roles directly.*

---

## Quick Start & Setup

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Node.js 18+ and npm
- Redis (optional — automatically starts daemon if installed, or falls back to in-memory)

### One-Command Start (Recommended)
```bash
./run.sh
```
*Frontend runs at `http://127.0.0.1:3000` | Backend API Docs at `http://127.0.0.1:8000/docs`*

### Manual Setup
```bash
# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=backend uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend (in another terminal)
cd frontend && npm install && npm run dev -- --port 3000
```

---

## Automated Test Suite

22 automated tests covering ML pipeline, caching, concurrency, and RBAC:
```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests -v
```

```
backend/tests/test_api_and_caching.py   6 passed
backend/tests/test_enhanced_cache.py    6 passed
backend/tests/test_ml_model.py          4 passed
backend/tests/test_redis_cache.py       6 passed
======================== 22 passed in 2.44s =========================
```

---

## AI Usage Disclosure

In compliance with AidenAI evaluation standards:
- **Candidate Ownership (100%):** Core system architecture, database modeling & SQLite WAL concurrency, ML selection & calibration, Bayesian threshold derivation ($\tau^{\ast}=0.25$), Redis caching layer with single-flight coalescing & fallback, RBAC policy design, and test suite definitions.
- **AI Acceleration:** Used strictly for generating synthetic training distribution boilerplate in `dataset.py` and repetitive React JSX/CSS layout scaffolding.
