"""Tests for Nonce Replay Protection and Idempotency Cache."""
import pytest
from backend.shared.errors import ReplayAttackDetectedError
from backend.payments.idempotency import IdempotencyStore


def test_nonce_replay_detection():
    store = IdempotencyStore()
    nonce = "nonce_abc_12345"

    # First use must succeed
    store.record_and_verify_nonce(nonce)

    # Second use of identical nonce must raise ReplayAttackDetectedError
    with pytest.raises(ReplayAttackDetectedError):
        store.record_and_verify_nonce(nonce)


def test_idempotency_cache():
    store = IdempotencyStore()
    key = "idem_key_uuid_888"

    assert store.get_idempotent_result(key) is None

    result_payload = {"status": "success", "result": 42}
    store.store_idempotent_result(key, result_payload)

    cached = store.get_idempotent_result(key)
    assert cached == result_payload
