"""[IMPLEMENTED FOUNDATION] Replay Protection and Idempotency Store."""
import time
from typing import Any, Dict, Optional, Set
from backend.shared.errors import ReplayAttackDetectedError


class IdempotencyStore:
    """Stores used nonces and caches idempotency keys to protect against replay attacks."""

    def __init__(self, ttl_seconds: int = 3600):
        self._ttl_seconds = ttl_seconds
        self._used_nonces: Dict[str, float] = {}
        self._idempotency_cache: Dict[str, Dict[str, Any]] = {}

    def record_and_verify_nonce(self, nonce: str) -> None:
        """Record a challenge nonce. Raises ReplayAttackDetectedError if nonce is re-used."""
        self._cleanup_expired()
        now = time.time()
        if nonce in self._used_nonces:
            raise ReplayAttackDetectedError(nonce)
        self._used_nonces[nonce] = now

    def get_idempotent_result(self, key: str) -> Optional[Dict[str, Any]]:
        """Return cached response for a previously executed idempotency key."""
        return self._idempotency_cache.get(key)

    def store_idempotent_result(self, key: str, result: Dict[str, Any]) -> None:
        """Store the computed result for an idempotency key."""
        self._idempotency_cache[key] = result

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = [n for n, ts in self._used_nonces.items() if now - ts > self._ttl_seconds]
        for n in expired:
            del self._used_nonces[n]
