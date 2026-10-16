"""Tests for Ledger Audit Records and Provider Reputation Metrics."""
from fastapi import status
from backend.shared.constants import LedgerStatus
from backend.shared.schemas import LedgerRecordSchema
from backend.ledger.models import ledger_repo
from backend.ledger.reputation import ReputationCalculator


def test_ledger_status_enum_values():
    expected = {
        "paid",
        "paid output rejected",
        "refused",
        "failed and not charged"
    }
    actual = {s.value for s in LedgerStatus}
    assert actual == expected


def test_ledger_insertion_and_query(client):
    # Insert test record
    record = LedgerRecordSchema(
        request_id="req_test_ledger_001",
        buyer_id="buyer_001",
        seller_id="seller_001",
        service_id="data_001",
        listed_price="0.002",
        amount_paid="0.002",
        tx_hash="0xabcd1234ef",
        status=LedgerStatus.PAID,
        latency_ms=150.0
    )
    ledger_repo.record_transaction(record)

    # Query via API
    response = client.get("/api/v1/ledger")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] >= 1

    # Query specific record
    rec_res = client.get("/api/v1/ledger/req_test_ledger_001")
    assert rec_res.status_code == status.HTTP_200_OK
    assert rec_res.json()["request_id"] == "req_test_ledger_001"
    assert rec_res.json()["status"] == "paid"


def test_reputation_metrics_computation(client):
    record = LedgerRecordSchema(
        request_id="req_test_rep_001",
        buyer_id="buyer_001",
        seller_id="seller_001",
        service_id="data_001",
        listed_price="0.002",
        amount_paid="0.002",
        tx_hash="0xabcd1234ef",
        status=LedgerStatus.PAID,
        latency_ms=150.0
    )
    ledger_repo.record_transaction(record)
    calc = ReputationCalculator(ledger_repo)
    metrics = calc.calculate_for_service("data_001")
    assert metrics.service_id == "data_001"
    assert metrics.total_calls >= 1
    assert metrics.successful_calls >= 1
    assert metrics.success_rate > 0.0
    assert metrics.reputation_score > 0.0

    # API route
    response = client.get("/api/v1/reputation/data_001")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["service_id"] == "data_001"
