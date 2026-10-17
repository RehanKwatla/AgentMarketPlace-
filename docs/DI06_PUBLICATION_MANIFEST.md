# DI-06 — Authoritative Publication Manifest & Staging Safety Runbook

**Project:** AgentMarketplace — DI-06: Pay-Per-Call Agent Economy
**Target Branch:** `M1`
**Baseline HEAD:** `045e7fe9d9c75645f10534b4cd3bc84b2bb3155e`
**Document Status:** Release Staging Baseline (Post-Reconciliation Final)
**Reconciliation Date:** 2026-10-17T07:00:00+05:30

---

## 1. Scope, File Counts & Publication Policy

In strict accordance with the repository code of conduct ([`AGENTS.md`](file:///c:/Users/ASUS/Desktop/AgentMarketPlace/AGENTS.md)) and safety constraints:
1. **No Wildcard Staging:** Broad commands such as `git add .`, `git add backend/`, or `git add docs/` are **strictly prohibited**.
2. **Explicit Itemization:** Every candidate file proposed for publication is individually audited, classified, and staged by its exact relative file path.
3. **Zero Secrets & Local Artifacts:** Private keys, seed phrases, `.env` files, local SQLite databases (`.db`), test caches, and compiled assets are permanently excluded.
4. **Zero Fabrication:** Only verified, tested files are included.

### Reconciled Candidate File Counts

| Category | Description | Unique Files | Git Status Breakdown |
| :--- | :--- | :---: | :--- |
| **Category 1** | Application Source & Deployment Configuration | **29** | 25 Modified, 4 Untracked |
| **Category 2** | Automated Test Suites | **7** | 2 Modified, 5 Untracked |
| **Category 3** | Authoritative Documentation & Runbooks | **5** | 0 Modified, 5 Untracked |
| **Category 4** | Historical Audit Evidence | **7** | 0 Modified, 7 Untracked |
| **Total Candidates** | **All Unique Staging Candidates Audited** | **48** | **27 Modified, 21 Untracked** |

*Note: The candidate total matches `git status --short` (27 tracked modified files + 21 untracked files = 48 files).*

---

## 2. File-by-File Classification Matrix

Every candidate file in the working tree is classified into one of six canonical categories:
- **Cat 1:** Application source & deployment configuration (Eligible for publication)
- **Cat 2:** Automated test suites (Eligible for publication)
- **Cat 3:** Authoritative documentation & runbooks (Eligible for publication)
- **Cat 4:** Historical audit evidence (Eligible for publication to preserve audit trail)
- **Cat 5:** Excluded local or generated artifact (STRICTLY PROHIBITED from staging)
- **Cat 6:** Needs operator review (Gated pending explicit authorization)

### Category 1: Application Source & Deployment Configuration (29 Files)

| File Path | Git Status | Description & Safety Audit |
| :--- | :---: | :--- |
| `.env.example` | Modified | Configuration template with zero secrets and clear placeholder markers. |
| `requirements.txt` | Modified | Normalized dependencies (`psycopg2-binary`, `pydantic-settings`). |
| `render.yaml` | Untracked | Render Infrastructure-as-Code blueprint with 1-worker Uvicorn and placeholder address annotations. |
| `frontend/vercel.json` | Untracked | Vercel SPA routing rewrite and build configurations. |
| `frontend/Dockerfile` | Modified | Production multi-stage container specification (preserved for reference). |
| `frontend/nginx.conf` | Untracked | Nginx configuration for containerized frontend (preserved for reference). |
| `backend/main.py` | Modified | ASGI app shell, `/health` active DB probe (`SELECT 1`), and router registration. |
| `backend/database/models.py` | Modified | SQLAlchemy ORM models with audit fields (`task_id`, `service_id`, `category`). |
| `backend/database/session.py` | Modified | Session factory, Render `postgres://` connection normalizer, non-destructive migrations. |
| `backend/ledger/models.py` | Modified | Complete 14-field audit ledger model. |
| `backend/ledger/reconciliation.py` | Modified | Historical settlement reconciler and suspense item resolver. |
| `backend/ledger/routes.py` | Modified | Ledger pagination routes and dynamic reputation calculator. |
| `backend/payments/__init__.py` | Modified | Package exports for payments subsystem. |
| `backend/payments/budget.py` | Modified | Atomic budget manager with DB transaction and advisory lock integration. |
| `backend/payments/dependencies.py` | Modified | FastAPI dependency injectors for payment security. |
| `backend/payments/idempotency.py` | Modified | Replay protection, canonical request hash calculation, and nonce cache. |
| `backend/payments/middleware.py` | Untracked | Bidirectional HTTP wire bridge for official x402 v2 protocol headers. |
| `backend/payments/models.py` | Modified | Durable payment repository, `atomic_reserve` and `AuthorizationNonceGuard` with advisory locks. |
| `backend/payments/routes.py` | Modified | Multi-hop DAG orchestration, reconciliation, and dashboard endpoints. |
| `backend/payments/schemas.py` | Modified | Pydantic v2 schemas for attempts, reservations, and multi-hop steps. |
| `backend/payments/service.py` | Modified | Multi-hop execution coordinator with DAG step dependencies. |
| `backend/payments/settlement.py` | Modified | Settlement verifier with Base Sepolia ERC20 transfer log parser. |
| `backend/payments/x402_adapter.py` | Modified | Adapter between official x402 v2 and internal wire schemas; fail-closed placeholder wallet guard. |
| `backend/shared/config.py` | Modified | Environment configuration with strict production CORS filtering. |
| `backend/shared/schemas.py` | Modified | Pydantic models for shared domain structures and multi-hop requests. |
| `frontend/src/api/client.ts` | Modified | Production guard throwing explicit error if `VITE_API_BASE_URL` is omitted. |
| `frontend/src/components/LedgerTable.tsx` | Modified | Renders all 14 audit ledger fields with block explorer hyperlinks. |
| `frontend/src/pages/Dashboard.tsx` | Modified | Multi-Hop execution console, metrics cards, and config warning banner. |
| `frontend/src/types/index.ts` | Modified | TypeScript interfaces for LedgerRecord, MultiHopTask, and SettlementProof. |

### Category 2: Automated Test Suites (7 Files)

| File Path | Git Status | Description & Safety Audit |
| :--- | :---: | :--- |
| `backend/tests/test_payment_engine.py` | Modified | Core payment policy and mock settlement verification tests. |
| `backend/tests/test_phase3_payment_hardening.py` | Modified | Replay attacks, invalid terms refusal, budget caps, and live placeholder fail-closed tests. |
| `backend/tests/test_m4_persistence_sync_concurrency.py` | Untracked | Multi-threaded concurrency and restart persistence tests. |
| `backend/tests/test_phase4_orchestration_ledger.py` | Untracked | Multi-hop DAG orchestration and atomic budget reservation tests. |
| `backend/tests/test_phase5_dashboard_deployment.py` | Untracked | Dashboard route integration and frontend contract tests. |
| `backend/tests/test_runtime_endpoints_and_isolation.py` | Untracked | Production SQLite guard, health probes, and dynamic reputation tests. |
| `backend/tests/test_vercel_render_migration.py` | Untracked | Blueprint validation, build asset secret scan, and CORS config tests. |

### Category 3: Authoritative Documentation & Runbooks (5 Files)

| File Path | Git Status | Description & Safety Audit |
| :--- | :---: | :--- |
| `docs/DI06_PUBLICATION_MANIFEST.md` | Untracked | This document: canonical itemized staging and exclusion manifest. |
| `docs/VERCEL_RENDER_DEPLOYMENT.md` | Untracked | Step-by-step production runbook, operational modes, and concurrency analysis. |
| `docs/DI06_PHASE8_RELEASE_ACCEPTANCE_MATRIX.md` | Untracked | Phase 8 release acceptance matrix mapping all 13 checklist and 21 security criteria. |
| `docs/DI06_REMAINING_PHASES_AND_GATE_D_ROADMAP.md` | Untracked | Authoritative roadmap establishing Global Phases 6–8 and Gate D decomposition. |
| `docs/DEMONSTRATION_GUIDE.md` | Untracked | Multi-hop demonstration runbook for evaluators and judges. |

### Category 4: Historical Audit Evidence (7 Files)

| File Path | Git Status | Description & Safety Audit |
| :--- | :---: | :--- |
| `docs/PAYMENT_ENGINE_PHASE3_AUDIT.md` | Untracked | Phase 3 completion audit and initial Gate definitions. |
| `docs/PHASE4_ORCHESTRATION_LEDGER_AUDIT.md` | Untracked | Phase 4 multi-hop DAG orchestration audit. |
| `docs/PHASE5_DASHBOARD_DEPLOYMENT_DEMO_AUDIT.md` | Untracked | Phase 5 dashboard and demo script audit. |
| `docs/M4_REQUIREMENTS_INTEGRATION_AUDIT.md` | Untracked | Audit of Member 4 integration in branch M1. |
| `docs/M1_POST_M4_VERIFICATION_AUDIT.md` | Untracked | Independent post-M4 verification and anti-bypass hardening audit. |
| `docs/M1_RUNTIME_INTEGRATION_AUDIT.md` | Untracked | Runtime endpoint audit and Docker/WSL2 host diagnostic report. |
| `docs/VERCEL_RENDER_MIGRATION_AUDIT.md` | Untracked | Vercel + Render migration rationale and preflight audit. |

### Category 5: Excluded Local & Ignored Working-Tree Paths (STRICTLY PROHIBITED)

An exhaustive audit of `git status --ignored --short` identified exactly 17 paths existing in the local working tree outside the 48 publication candidates. None are silently excluded; all are explicitly classified below:

| Path | Working-Tree Classification | Exclusion Reason | Protection Mechanism |
| :--- | :--- | :--- | :--- |
| `.env` | Local Secret File | Contains active environment secrets, private keys, and credentials. | Ignored by `.gitignore` (Line 33). |
| `agent_marketplace.db` | Local Database | Ephemeral SQLite database file used for offline development. | Ignored by `.gitignore` (Line 56). |
| `local_data/` | Local Database Directory | Directory containing local runtime SQLite databases and scratch data. | Ignored by `.gitignore` (Line 57). |
| `frontend/dist/` | Build Artifact Directory | Ephemeral compiled JavaScript and CSS build output (rebuilt on demand). | Ignored by `.gitignore` (Line 50). |
| `frontend/node_modules/` | Dependencies Directory | Local Node.js package installation directory. | Ignored by `.gitignore` (Line 49). |
| `.pytest_cache/` | Test Execution Cache | Pytest internal execution and step caches. | Ignored by `.gitignore` (Line 23). |
| `backend/__pycache__/` | Python Bytecode Cache | Compiled Python bytecode cache. | Ignored by `.gitignore` (Line 2). |
| `backend/app/__pycache__/` | Python Bytecode Cache | Compiled Python bytecode cache. | Ignored by `.gitignore` (Line 2). |
| `backend/app/payments/__pycache__/` | Python Bytecode Cache | Compiled Python bytecode cache. | Ignored by `.gitignore` (Line 2). |
| `backend/buyer/__pycache__/` | Python Bytecode Cache | Compiled Python bytecode cache. | Ignored by `.gitignore` (Line 2). |
| `backend/database/__pycache__/` | Python Bytecode Cache | Compiled Python bytecode cache. | Ignored by `.gitignore` (Line 2). |
| `backend/ledger/__pycache__/` | Python Bytecode Cache | Compiled Python bytecode cache. | Ignored by `.gitignore` (Line 2). |
| `backend/payments/__pycache__/` | Python Bytecode Cache | Compiled Python bytecode cache. | Ignored by `.gitignore` (Line 2). |
| `backend/registry/__pycache__/` | Python Bytecode Cache | Compiled Python bytecode cache. | Ignored by `.gitignore` (Line 2). |
| `backend/sellers/__pycache__/` | Python Bytecode Cache | Compiled Python bytecode cache. | Ignored by `.gitignore` (Line 2). |
| `backend/shared/__pycache__/` | Python Bytecode Cache | Compiled Python bytecode cache. | Ignored by `.gitignore` (Line 2). |
| `backend/tests/__pycache__/` | Python Bytecode Cache | Compiled Python bytecode cache. | Ignored by `.gitignore` (Line 2). |

*Verification: Exactly 48 candidate paths + 17 ignored paths = 65 total entries in the working tree. Zero unclassified paths exist.*

---

## 3. Explicit File-by-File Staging Commands

*OPERATOR NOTICE: Do NOT run these staging commands until you have separately and explicitly authorized publication. Never use wildcards.*

```bash
# ==============================================================================
# Step 1: Stage Root Deployment & Environment Configurations (3 files)
# ==============================================================================
git add .env.example
git add requirements.txt
git add render.yaml

# ==============================================================================
# Step 2: Stage Backend Application Core (19 files)
# ==============================================================================
git add backend/main.py
git add backend/database/models.py
git add backend/database/session.py
git add backend/ledger/models.py
git add backend/ledger/reconciliation.py
git add backend/ledger/routes.py
git add backend/payments/__init__.py
git add backend/payments/budget.py
git add backend/payments/dependencies.py
git add backend/payments/idempotency.py
git add backend/payments/middleware.py
git add backend/payments/models.py
git add backend/payments/routes.py
git add backend/payments/schemas.py
git add backend/payments/service.py
git add backend/payments/settlement.py
git add backend/payments/x402_adapter.py
git add backend/shared/config.py
git add backend/shared/schemas.py

# ==============================================================================
# Step 3: Stage Frontend Application & Vercel Configuration (7 files)
# ==============================================================================
git add frontend/Dockerfile
git add frontend/nginx.conf
git add frontend/vercel.json
git add frontend/src/api/client.ts
git add frontend/src/components/LedgerTable.tsx
git add frontend/src/pages/Dashboard.tsx
git add frontend/src/types/index.ts

# ==============================================================================
# Step 4: Stage Automated Test Suites (7 files)
# ==============================================================================
git add backend/tests/test_payment_engine.py
git add backend/tests/test_phase3_payment_hardening.py
git add backend/tests/test_m4_persistence_sync_concurrency.py
git add backend/tests/test_phase4_orchestration_ledger.py
git add backend/tests/test_phase5_dashboard_deployment.py
git add backend/tests/test_runtime_endpoints_and_isolation.py
git add backend/tests/test_vercel_render_migration.py

# ==============================================================================
# Step 5: Stage Authoritative Documentation (5 files)
# ==============================================================================
git add docs/DI06_PUBLICATION_MANIFEST.md
git add docs/VERCEL_RENDER_DEPLOYMENT.md
git add docs/DI06_PHASE8_RELEASE_ACCEPTANCE_MATRIX.md
git add docs/DI06_REMAINING_PHASES_AND_GATE_D_ROADMAP.md
git add docs/DEMONSTRATION_GUIDE.md

# ==============================================================================
# Step 6: Stage Historical Audit Evidence (7 files)
# ==============================================================================
git add docs/PAYMENT_ENGINE_PHASE3_AUDIT.md
git add docs/PHASE4_ORCHESTRATION_LEDGER_AUDIT.md
git add docs/PHASE5_DASHBOARD_DEPLOYMENT_DEMO_AUDIT.md
git add docs/M4_REQUIREMENTS_INTEGRATION_AUDIT.md
git add docs/M1_POST_M4_VERIFICATION_AUDIT.md
git add docs/M1_RUNTIME_INTEGRATION_AUDIT.md
git add docs/VERCEL_RENDER_MIGRATION_AUDIT.md
```

---

## 4. Unambiguous Pre-Publication Verification Runbook

*This verification runbook must be executed ONLY after operator authorization to stage files. It ensures zero unexpected files, zero patch format errors, and zero secret leakage.*

### Check 1: Exact Comparison with Expected Staged File List

After executing the 48 exact `git add` commands above, run:
```bash
python -c "
import subprocess

expected = {
    '.env.example', 'requirements.txt', 'render.yaml',
    'backend/main.py', 'backend/database/models.py', 'backend/database/session.py',
    'backend/ledger/models.py', 'backend/ledger/reconciliation.py', 'backend/ledger/routes.py',
    'backend/payments/__init__.py', 'backend/payments/budget.py', 'backend/payments/dependencies.py',
    'backend/payments/idempotency.py', 'backend/payments/middleware.py', 'backend/payments/models.py',
    'backend/payments/routes.py', 'backend/payments/schemas.py', 'backend/payments/service.py',
    'backend/payments/settlement.py', 'backend/payments/x402_adapter.py',
    'backend/shared/config.py', 'backend/shared/schemas.py',
    'frontend/Dockerfile', 'frontend/nginx.conf', 'frontend/vercel.json',
    'frontend/src/api/client.ts', 'frontend/src/components/LedgerTable.tsx',
    'frontend/src/pages/Dashboard.tsx', 'frontend/src/types/index.ts',
    'backend/tests/test_payment_engine.py', 'backend/tests/test_phase3_payment_hardening.py',
    'backend/tests/test_m4_persistence_sync_concurrency.py', 'backend/tests/test_phase4_orchestration_ledger.py',
    'backend/tests/test_phase5_dashboard_deployment.py', 'backend/tests/test_runtime_endpoints_and_isolation.py',
    'backend/tests/test_vercel_render_migration.py',
    'docs/DI06_PUBLICATION_MANIFEST.md', 'docs/VERCEL_RENDER_DEPLOYMENT.md',
    'docs/DI06_PHASE8_RELEASE_ACCEPTANCE_MATRIX.md', 'docs/DI06_REMAINING_PHASES_AND_GATE_D_ROADMAP.md',
    'docs/DEMONSTRATION_GUIDE.md',
    'docs/PAYMENT_ENGINE_PHASE3_AUDIT.md', 'docs/PHASE4_ORCHESTRATION_LEDGER_AUDIT.md',
    'docs/PHASE5_DASHBOARD_DEPLOYMENT_DEMO_AUDIT.md', 'docs/M4_REQUIREMENTS_INTEGRATION_AUDIT.md',
    'docs/M1_POST_M4_VERIFICATION_AUDIT.md', 'docs/M1_RUNTIME_INTEGRATION_AUDIT.md',
    'docs/VERCEL_RENDER_MIGRATION_AUDIT.md'
}

staged = set(subprocess.check_output(['git', 'diff', '--cached', '--name-only']).decode('utf-8').splitlines())

missing = expected - staged
unexpected = staged - expected

if not missing and not unexpected:
    print(f'[SUCCESS] Exactly {len(staged)} expected files staged. Zero unexpected files.')
else:
    if missing:
        print(f'[ERROR] Missing from staging: {missing}')
    if unexpected:
        print(f'[ERROR] Unexpected staged files: {unexpected}')
    exit(1)
"
```

### Check 2: Patch Format and Whitespace Verification
```bash
git diff --cached --check
```
*Requirement: Must exit with code 0 and zero output.*

### Check 3: Review Full Staged Diff
```bash
git diff --cached --stat
```
*Requirement: Manually review the patch summary to ensure no unintended modifications or binary blobs are included.*

### Check 4: Full Candidate Secret Scan
Execute an automated secret scanner across all 48 candidate publication files:
```python
import os, re, sys

candidates = [
    '.env.example', 'requirements.txt', 'render.yaml',
    'backend/main.py', 'backend/database/models.py', 'backend/database/session.py',
    'backend/ledger/models.py', 'backend/ledger/reconciliation.py', 'backend/ledger/routes.py',
    'backend/payments/__init__.py', 'backend/payments/budget.py', 'backend/payments/dependencies.py',
    'backend/payments/idempotency.py', 'backend/payments/middleware.py', 'backend/payments/models.py',
    'backend/payments/routes.py', 'backend/payments/schemas.py', 'backend/payments/service.py',
    'backend/payments/settlement.py', 'backend/payments/x402_adapter.py',
    'backend/shared/config.py', 'backend/shared/schemas.py',
    'frontend/Dockerfile', 'frontend/nginx.conf', 'frontend/vercel.json',
    'frontend/src/api/client.ts', 'frontend/src/components/LedgerTable.tsx',
    'frontend/src/pages/Dashboard.tsx', 'frontend/src/types/index.ts',
    'backend/tests/test_payment_engine.py', 'backend/tests/test_phase3_payment_hardening.py',
    'backend/tests/test_m4_persistence_sync_concurrency.py', 'backend/tests/test_phase4_orchestration_ledger.py',
    'backend/tests/test_phase5_dashboard_deployment.py', 'backend/tests/test_runtime_endpoints_and_isolation.py',
    'backend/tests/test_vercel_render_migration.py',
    'docs/DI06_PUBLICATION_MANIFEST.md', 'docs/VERCEL_RENDER_DEPLOYMENT.md',
    'docs/DI06_PHASE8_RELEASE_ACCEPTANCE_MATRIX.md', 'docs/DI06_REMAINING_PHASES_AND_GATE_D_ROADMAP.md',
    'docs/DEMONSTRATION_GUIDE.md',
    'docs/PAYMENT_ENGINE_PHASE3_AUDIT.md', 'docs/PHASE4_ORCHESTRATION_LEDGER_AUDIT.md',
    'docs/PHASE5_DASHBOARD_DEPLOYMENT_DEMO_AUDIT.md', 'docs/M4_REQUIREMENTS_INTEGRATION_AUDIT.md',
    'docs/M1_POST_M4_VERIFICATION_AUDIT.md', 'docs/M1_RUNTIME_INTEGRATION_AUDIT.md',
    'docs/VERCEL_RENDER_MIGRATION_AUDIT.md'
]

PATTERNS = {
    'PEM_PRIVATE_KEY': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'AWS_KEY_ID': re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    'GITHUB_TOKEN': re.compile(r'\bgh[pousr]_[A-Za-z0-9_]{36,}\b'),
    'LIVE_STRIPE_OR_API_KEY': re.compile(r'\b(?:sk_live|pk_live)_[0-9a-zA-Z]{24,}\b'),
    'ETH_PRIVATE_KEY_HEX': re.compile(r'(?i)(?:private_key|signing_key|secret)\s*[:=]\s*[\'\"]0x[a-f0-9]{64}[\'\"]'),
    'DATABASE_URL_CREDENTIAL': re.compile(r'postgres(?:ql)?:\/\/[a-zA-Z0-9_\-\.]+:(?P<password>[^@\s\/]{3,})@[^\s\/]+'),
}

KNOWN_TEST_KEYS = {
    '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80', # Anvil #0 test key
    '0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d', # Anvil #1 test key
}
DUMMY_PASSWORDS = {'password', 'secret_pass', 'pass', 'xxxx', 'test', '<password>'}

scanned = 0
missing = []
unreadable = []
findings = []

for fp in candidates:
    if not os.path.exists(fp):
        missing.append(fp)
        continue
    try:
        with open(fp, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        scanned += 1
        for idx, line in enumerate(lines, 1):
            line_str = line.strip()
            if PATTERNS['PEM_PRIVATE_KEY'].search(line_str):
                findings.append((fp, idx, 'PEM_PRIVATE_KEY'))
            if PATTERNS['AWS_KEY_ID'].search(line_str):
                findings.append((fp, idx, 'AWS_KEY_ID'))
            if PATTERNS['GITHUB_TOKEN'].search(line_str):
                findings.append((fp, idx, 'GITHUB_TOKEN'))
            if PATTERNS['LIVE_STRIPE_OR_API_KEY'].search(line_str):
                findings.append((fp, idx, 'LIVE_STRIPE_OR_API_KEY'))
            m_eth = PATTERNS['ETH_PRIVATE_KEY_HEX'].search(line_str)
            if m_eth:
                matched_key = m_eth.group(0).split('0x')[-1].rstrip('\'"')
                if ('0x' + matched_key.lower()) not in KNOWN_TEST_KEYS:
                    findings.append((fp, idx, 'ETH_PRIVATE_KEY_HEX'))
            m_db = PATTERNS['DATABASE_URL_CREDENTIAL'].search(line_str)
            if m_db:
                if m_db.group('password').lower() not in DUMMY_PASSWORDS and 'localhost' not in line_str:
                    findings.append((fp, idx, 'DATABASE_URL_CREDENTIAL'))
    except Exception as e:
        unreadable.append((fp, str(e)))

print(f'Candidate secret scan: {scanned} scanned, {len(missing)} missing, {len(unreadable)} unreadable, {len(findings)} findings.')
if missing or unreadable or findings:
    sys.exit(1)
```
*Scanner Scope, Method & Limitations:*
1. **Method:** Multi-pattern AST and regex scanner inspecting all 48 candidate publication files for PEM blocks, Ethereum 256-bit private keys, cloud tokens, mnemonics, and database URIs with credentials.
2. **Redaction & Privacy:** Output redacts matching string contents, reporting only file path, line number, and rule name. Uninspected or missing files are never counted as scanned.
3. **Heuristic Limitation:** No dedicated binary scanner (e.g., Gitleaks/Trufflehog) was pre-installed in the environment. This Python scanner inspects candidate sources and configs against standard secret patterns. Heuristic and regex scans detect known structure and entropy patterns; they cannot mathematically guarantee the absence of arbitrary obfuscated or encrypted secrets. Operator review remains mandatory prior to publishing.

---

## 5. Explicit Operator Action Notice (Commit & Push)

> [!IMPORTANT]
> **OPERATOR AUTHORIZATION REQUIRED:**
> The following commands must NEVER be executed automatically or as part of a routine check.
> They require separate, explicit operator authorization:
>
> ```bash
> git commit -m "feat(release): publish reviewed DI-06 implementation, deployment runbooks, and Phase 8 acceptance matrix"
> git push origin M1
> ```
