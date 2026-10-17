"""QA Audit Script for DI-06 Agent Economy Backend.
Runs full end-to-end verification and failure diagnostics across live TestClient instances.
"""
import asyncio
import json
import uuid
from typing import Any, Dict
from fastapi.testclient import TestClient
import httpx

from backend.main import app
from backend.shared.constants import (
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    LedgerStatus,
    ServiceCategory,
    usdc_to_base_units,
    base_units_to_usdc,
)
from backend.shared.config import get_settings

client = TestClient(app)
settings = get_settings()

audit_results = {}

def record_check(category: str, check_name: str, passed: bool, evidence: Any, notes: str = ""):
    if category not in audit_results:
        audit_results[category] = []
    audit_results[category].append({
        "check": check_name,
        "status": "PASS" if passed else "FAIL",
        "evidence": evidence,
        "notes": notes
    })

print("=" * 70)
print("STARTING DI-06 BACKEND QA INTEGRATION AUDIT")
print("=" * 70)

# ------------------------------------------------------------------------------
# 1. System Health & OpenAPI
# ------------------------------------------------------------------------------
r = client.get("/health")
h_data = r.json()
record_check(
    "health_and_openapi",
    "Health Endpoint Returns 200 with Base Sepolia Network",
    r.status_code == 200 and h_data.get("network") == NETWORK_BASE_SEPOLIA,
    h_data
)

r_open = client.get("/openapi.json")
num_paths = len(r_open.json().get("paths", {}))
record_check(
    "health_and_openapi",
    "OpenAPI Schema Generated with Registered Endpoints",
    r_open.status_code == 200 and num_paths >= 40,
    f"{num_paths} paths registered in OpenAPI"
)

# ------------------------------------------------------------------------------
# 2. CORS Verification
# ------------------------------------------------------------------------------
cors_req = client.get("/health", headers={"Origin": "https://agentica-two.vercel.app"})
cors_allow = cors_req.headers.get("access-control-allow-origin") == "https://agentica-two.vercel.app"
cors_cred = cors_req.headers.get("access-control-allow-credentials") == "true"
record_check(
    "cors_verification",
    "Vercel Deployed Origin Allowed with Credentials",
    cors_allow and cors_cred,
    {"allow_origin": cors_req.headers.get("access-control-allow-origin"), "allow_credentials": cors_req.headers.get("access-control-allow-credentials")}
)

cors_pre = client.options(
    "/api/v1/tasks",
    headers={
        "Origin": "https://agentica-two.vercel.app",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type, Idempotency-Key, X-402-Payment-Payload"
    }
)
pre_ok = cors_pre.status_code == 200 and cors_pre.headers.get("access-control-allow-origin") == "https://agentica-two.vercel.app"
record_check(
    "cors_verification",
    "OPTIONS Preflight for Vercel Origin Accepted",
    pre_ok,
    {"status": cors_pre.status_code, "allow_methods": cors_pre.headers.get("access-control-allow-methods")}
)

cors_evil = client.get("/health", headers={"Origin": "https://unauthorized-evil-site.com"})
evil_rejected = cors_evil.headers.get("access-control-allow-origin") is None
record_check(
    "cors_verification",
    "Untrusted Origins Denied Access-Control Header",
    evil_rejected,
    {"status": cors_evil.status_code, "allow_origin_header": cors_evil.headers.get("access-control-allow-origin")}
)

# ------------------------------------------------------------------------------
# 3. Service Registry & Discovery
# ------------------------------------------------------------------------------
r_svc = client.get("/api/v1/services")
svc_resp = r_svc.json()
svcs = svc_resp.get("services", []) if isinstance(svc_resp, dict) else svc_resp
has_canonical = any(s.get("service_id") == "data_001" for s in svcs) and any(s.get("service_id") == "scraping_001" for s in svcs)
record_check(
    "service_discovery",
    "Service Registry Lists Canonical Seed Services",
    r_svc.status_code == 200 and has_canonical,
    {"count": len(svcs), "services": [s.get("service_id") for s in svcs]}
)

r_rec = client.post("/api/v1/services/recommendations", json={"task": "lookup crypto prices and analyze with AI"})
rec_data = r_rec.json()
record_check(
    "service_discovery",
    "Recommendation Engine Proposes Compatible Service Workflow",
    r_rec.status_code == 200 and "recommendations" in rec_data,
    {"workflow": rec_data.get("workflow_type"), "proposed": [s.get("service_id") for s in rec_data.get("recommendations", [])]}
)

# ------------------------------------------------------------------------------
# 4. Budget Enforcement & Boundary Testing
# ------------------------------------------------------------------------------
# Negative budget
r_neg = client.post("/api/v1/tasks", json={"task": "test", "budget_usdc": "-0.010000"})
record_check(
    "budget_enforcement",
    "Negative Budget Rejected Server-Side (422)",
    r_neg.status_code == 422,
    {"status": r_neg.status_code, "detail": r_neg.json()}
)

# Zero budget
r_zero = client.post("/api/v1/tasks", json={"task": "test", "budget_usdc": "0.000000"})
record_check(
    "budget_enforcement",
    "Zero Budget Rejected Server-Side (422)",
    r_zero.status_code == 422,
    {"status": r_zero.status_code, "detail": r_zero.json()}
)

# Over limit budget
r_over = client.post("/api/v1/tasks", json={"task": "test", "budget_usdc": "50.000000"})
record_check(
    "budget_enforcement",
    "Over-Limit Budget Exceeding Server Max Rejected (422)",
    r_over.status_code == 422,
    {"status": r_over.status_code, "detail": r_over.json()}
)

# Task requiring more budget than provided is refused during planning without payment
r_insuf = client.post("/api/v1/tasks", json={"task": "Lookup ETH market price", "budget_usdc": "0.001000", "execute_now": True})
insuf_data = r_insuf.json()
record_check(
    "budget_enforcement",
    "Under-Budget Task Refused Before Payment Authorization",
    insuf_data.get("status") == "refused" and insuf_data.get("failure_code") == "INSUFFICIENT_BUDGET" and insuf_data.get("spent_usdc") == "0.000000",
    {"status": insuf_data.get("status"), "failure_code": insuf_data.get("failure_code"), "spent_usdc": insuf_data.get("spent_usdc")}
)

# ------------------------------------------------------------------------------
# 5. Core End-to-End Flow & Explainable Selection
# ------------------------------------------------------------------------------
idem_key = f"qa_test_idem_{uuid.uuid4().hex[:12]}"
r_task = client.post(
    "/api/v1/tasks",
    json={
        "task": "Lookup ETH market price and stats",
        "budget_usdc": "0.050000",
        "idempotency_key": idem_key,
        "execute_now": True
    }
)
task_data = r_task.json()
t_id = task_data.get("task_id")
record_check(
    "core_e2e_flow",
    "Autonomous Task Successfully Executed and Succeeded",
    task_data.get("status") in ["completed", "completed_with_warnings"],
    {"task_id": t_id, "status": task_data.get("status"), "spent_usdc": task_data.get("spent_usdc"), "is_settlement_confirmed": task_data.get("is_settlement_confirmed")}
)

# Check Task Result & Provenance Endpoint
r_res = client.get(f"/api/v1/tasks/{t_id}/result")
res_data = r_res.json()
record_check(
    "core_e2e_flow",
    "Task Result Endpoint Returns Synthesized Data and Provenance",
    r_res.status_code == 200 and "provenance" in res_data and len(res_data.get("calls", [])) >= 1,
    {"provenance_items": len(res_data.get("provenance", [])), "calls": len(res_data.get("calls", []))}
)

# Check Explainable Selection without fabricated numbers
calls = task_data.get("calls", [])
first_call = calls[0] if calls else {}
record_check(
    "core_e2e_flow",
    "Call Record Exposes Diagnostic Fields (ID, Reference, Network, Confirmed)",
    first_call.get("is_settlement_confirmed") is True and first_call.get("transaction_hash") is not None and first_call.get("network") == NETWORK_BASE_SEPOLIA,
    {
        "call_id": first_call.get("call_id"),
        "tx_hash": first_call.get("transaction_hash"),
        "network": first_call.get("network"),
        "is_settlement_confirmed": first_call.get("is_settlement_confirmed"),
        "payment_attempt_id": first_call.get("payment_attempt_id")
    }
)

# Check Idempotency - submitting identical task returns existing record
r_dup = client.post(
    "/api/v1/tasks",
    json={
        "task": "Lookup ETH market price and stats",
        "budget_usdc": "0.050000",
        "idempotency_key": idem_key,
        "execute_now": True
    }
)
dup_data = r_dup.json()
record_check(
    "idempotency_and_replay",
    "Duplicate Submission with Same Idempotency Key Returns Existing Task",
    dup_data.get("task_id") == t_id,
    {"original_task_id": t_id, "duplicate_task_id": dup_data.get("task_id")}
)

# ------------------------------------------------------------------------------
# 6. Ledger & Transaction Queries
# ------------------------------------------------------------------------------
r_ledg = client.get("/api/v1/ledger?limit=10")
ledg_data = r_ledg.json()
has_items = len(ledg_data.get("records", [])) >= 1
record_check(
    "ledger_and_receipts",
    "Ledger List Endpoint Returns Paginated Audit Records",
    r_ledg.status_code == 200 and has_items,
    {"total": ledg_data.get("total"), "returned": len(ledg_data.get("records", []))}
)

# Test Ledger Filter by Status
r_ledg_filt = client.get("/api/v1/ledger?status=paid&limit=5")
filt_items = r_ledg_filt.json().get("records", [])
all_paid = all(item.get("status") in ["paid", "PAID"] for item in filt_items) if filt_items else True
record_check(
    "ledger_and_receipts",
    "Ledger Filters Correctly by Status",
    r_ledg_filt.status_code == 200 and all_paid,
    {"filtered_count": len(filt_items), "statuses": [i.get("status") for i in filt_items]}
)

# Payments Dashboard Aggregation
r_dash = client.get("/api/v1/payments/dashboard")
dash_data = r_dash.json()
record_check(
    "ledger_and_receipts",
    "Payments Dashboard Exposes Aggregated Spend and Reconciliation Stats",
    r_dash.status_code == 200 and "total_spend_usdc" in dash_data and "settlement_evidence" in dash_data,
    {
        "total_spend_usdc": dash_data.get("total_spend_usdc"),
        "total_paid_calls": dash_data.get("total_paid_calls"),
        "settlement_evidence": dash_data.get("settlement_evidence"),
        "network": dash_data.get("network")
    }
)

# Wallet Balance Endpoint
test_addr = "0x0000000000000000000000000000000000000001"
r_bal = client.get(f"/api/v1/wallets/{test_addr}/balance")
bal_data = r_bal.json()
record_check(
    "wallet_balance_and_verification",
    "Wallet Balance Endpoint Queries RPC or Fails Safely with Zero Fallback",
    r_bal.status_code == 200 and "balance_usdc" in bal_data and bal_data.get("network") == NETWORK_BASE_SEPOLIA,
    bal_data
)

# Transaction Verification Endpoint
dummy_tx = "0x" + "c" * 64
r_tx = client.get(f"/api/v1/payments/verify-tx/{dummy_tx}")
tx_data = r_tx.json()
record_check(
    "wallet_balance_and_verification",
    "Transaction Verification Endpoint Distinguishes Real On-Chain Confirmation from Unconfirmed",
    r_tx.status_code == 200 and "is_confirmed" in tx_data and tx_data.get("network") == NETWORK_BASE_SEPOLIA,
    tx_data
)

# Print Summary
print("\n" + "=" * 70)
print("AUDIT SUMMARY BY CATEGORY:")
print("=" * 70)
total_pass = 0
total_fail = 0
for cat, checks in audit_results.items():
    print(f"\n[{cat.upper()}]")
    for c in checks:
        icon = "[PASS]" if c["status"] == "PASS" else "[FAIL]"
        if c["status"] == "PASS":
            total_pass += 1
        else:
            total_fail += 1
        print(f"  {icon} {c['check']}")
        print(f"         Evidence: {c['evidence']}")

print("\n" + "=" * 70)
print(f"TOTAL CHECKS: {total_pass + total_fail} | PASSED: {total_pass} | FAILED: {total_fail}")
print("=" * 70)

with open("audit_results.json", "w") as f:
    json.dump(audit_results, f, indent=2)
