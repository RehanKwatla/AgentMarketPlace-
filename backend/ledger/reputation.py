"""[IMPLEMENTED FOUNDATION] Provider Reputation Calculation Engine."""
import statistics
from typing import Dict, List
from backend.shared.constants import LedgerStatus
from backend.shared.schemas import LedgerRecordSchema, ReputationMetrics
from backend.ledger.models import LedgerRepository, ledger_repo


class ReputationCalculator:
    """Calculates provider reliability, latency, and schema fidelity metrics."""

    def __init__(self, repository: LedgerRepository = ledger_repo):
        self.repo = repository

    def calculate_for_service(self, service_id: str) -> ReputationMetrics:
        records = self.repo.list_records(service_id=service_id, limit=5000)
        total_calls = len(records)
        if total_calls == 0:
            return ReputationMetrics(
                service_id=service_id,
                total_calls=0,
                successful_calls=0,
                success_rate=1.0,
                median_latency_ms=0.0,
                failure_counts=0,
                schema_invalid_counts=0,
                reputation_score=100.0
            )

        successful = [r for r in records if r.status == LedgerStatus.PAID]
        schema_invalid = [r for r in records if r.status == LedgerStatus.PAID_OUTPUT_REJECTED]
        failed = [
            r for r in records
            if r.status in [LedgerStatus.REFUSED, LedgerStatus.FAILED_AND_NOT_CHARGED]
        ]

        latencies = [r.latency_ms for r in records if r.latency_ms > 0]
        median_lat = float(statistics.median(latencies)) if latencies else 0.0

        success_rate = len(successful) / total_calls

        # Score out of 100: Base success weight 80%, Schema penalty 20%
        base_score = success_rate * 80.0
        schema_fidelity = (1.0 - (len(schema_invalid) / total_calls)) * 20.0
        total_score = max(0.0, min(100.0, base_score + schema_fidelity))

        return ReputationMetrics(
            service_id=service_id,
            total_calls=total_calls,
            successful_calls=len(successful),
            success_rate=round(success_rate, 4),
            median_latency_ms=round(median_lat, 2),
            failure_counts=len(failed),
            schema_invalid_counts=len(schema_invalid),
            reputation_score=round(total_score, 1)
        )

    def calculate_all(self) -> Dict[str, ReputationMetrics]:
        all_records = self.repo.list_records(limit=10000)
        service_ids = {r.service_id for r in all_records}
        # Include default three services even if no calls yet
        service_ids.update(["data_001", "scraping_001", "inference_001"])
        return {sid: self.calculate_for_service(sid) for sid in sorted(service_ids)}
