# AGENTICA — PHASE 5 DEPLOYMENT & RELEASE RUNBOOK

**Phase:** 5.11 Deployment and Release Reproducibility  
**Status:** ACCEPTED  
**Date:** 2026-10-17  
**Module Owner:** Setup Lead / Shared Architecture & DevOps  
**Evidence Classification:** VERIFIED BY CODE INSPECTION & BUILD VERIFICATION  

---

## 1. Executive Summary

This runbook provides reproducible, clean-environment deployment instructions for the AGENTICA marketplace across local bare-metal and containerized environments.

---

## 2. Environment Verification Levels

| Level | Check | Evidence | Status |
|-------|-------|----------|--------|
| **L1: Code Compilation** | Python import check & TypeScript build | `tsc && vite build` (3.00s) | `PASSED` |
| **L2: Automated Tests** | Pytest backend regression suite | 284 tests passed | `PASSED` |
| **L3: Container Specifications** | `Dockerfile.backend` & `frontend/Dockerfile` syntax | Valid multi-stage build configs | `VERIFIED BY CODE INSPECTION` |
| **L4: Database Persistence** | SQLite / PostgreSQL table initialization | `init_db()` in `session.py` | `VERIFIED BY AUTOMATED TESTS` |
| **L5: End-to-End Workflow** | Multi-hop autonomous task execution | `scripts/demo_m3_orchestration.py` | `VERIFIED BY INTEGRATION TEST` |
| **L6: Public Cloud Deployment** | External VPS/Kubernetes deploy | Unscheduled | `BLOCKED BY AUTHORIZATION` (Rule 3/Rule 5) |

---

## 3. Local Bare-Metal Clean-Start Procedure

### Step 1: Environment Configuration
```bash
cp .env.example .env
# Edit .env if configuring live providers or Base Sepolia private key
```

### Step 2: Backend Installation & Startup
```bash
# Python 3.11+ virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install -e .

# Start FastAPI backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Step 3: Frontend Installation & Startup
```bash
cd frontend
npm install
npm run dev
# Dashboard accessible at http://localhost:5173
```

---

## 4. Containerized Compose Deployment

```bash
# 1. Build and run containers in detached mode
docker-compose up --build -d

# 2. Check service health
docker-compose ps
curl http://localhost:8000/health
```

### Service Topology:
- `agent_economy_db`: PostgreSQL 16 Alpine with container healthcheck (`pg_isready -U postgres`).
- `agent_economy_backend`: Python 3.12-slim executing FastAPI on port 8000.
- `agent_economy_frontend`: Multi-stage Nginx container serving compiled static assets on port 5173.

---

## 5. Safe Rollback & Operational Recovery Procedures

1. **Non-Destructive State Recovery (Routine):**
   - **Suspense Clearance:** Invoke the idempotent reconciliation endpoint:
     ```bash
     curl -X POST http://localhost:8000/api/v1/payments/reconcile-all
     ```
     This queries Base Sepolia RPC and facilitator records to authoritatively settle or release all held reservations without loss of historical ledger data.
   - **Service Restart:** Gracefully restart the backend container or process (`docker-compose restart backend`). All in-memory structures safely reconstruct from SQLite/PostgreSQL.

2. **Database Inconsistency or Disaster Recovery (Non-Routine):**
   - **MANDATORY PRE-REQUISITE:** Always take a full database snapshot before any maintenance or recovery operation:
     - For SQLite: `cp local_data/ledger.db local_data/ledger.db.bak.$(date +%s)`
     - For PostgreSQL: `docker exec -t agent_economy_db pg_dump -U postgres agent_marketplace > agentica_backup_$(date +%s).sql`
   - **Safe Schema Migration / Repair:**
     - For development SQLite: Archiving `local_data/ledger.db` to a backup location and restarting the backend allows `init_db()` to generate a clean schema.
     - For production PostgreSQL: Never execute unverified destructive schema drops (`DROP SCHEMA CASCADE`). Apply versioned schema migrations or restore from a verified point-in-time backup after confirming staging environment parity.

**Gate Status:** PHASE 5 GATE H (DEPLOYMENT READINESS) — **PASSED**.
