"""Provider Reputation Calculation Engine and Retryable Telemetry Sync."""
from datetime import datetime, timezone
import logging
import statistics
from typing import Dict, List, Optional, Set
from backend.shared.constants import (
    LedgerStatus,
    base_units_to_usdc,
    usdc_to_base_units,
)
from backend.shared.schemas import LedgerRecordSchema, ReputationMetrics
from backend.ledger.models import LedgerRepository, ledger_repo
from backend.database.session import SessionLocal
from backend.database.models import SellerReputationModel

logger = logging.getLogger(__name__)


class ReputationCalculator:
    """Calculates provider reliability, latency, and volume metrics from canonical ledger records."""

    def __init__(self, repository: LedgerRepository = ledger_repo):
        self.repo = repository
        self._pending_repairs: Set[str] = set()

    def calculate_for_service(self, service_id: str) -> ReputationMetrics:
        """Calculate accurate reputation metrics from canonical ledger records."""
        records = self.repo.list_records(service_id=service_id, limit=10000)
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
                reputation_score=100.0,
                total_volume_units=0,
                total_volume_usdc="0.000000"
            )

        successful = [r for r in records if r.status == LedgerStatus.PAID]
        schema_invalid = [r for r in records if r.status == LedgerStatus.PAID_OUTPUT_REJECTED]
        failed = [
            r for r in records
            if r.status in [LedgerStatus.REFUSED, LedgerStatus.FAILED_AND_NOT_CHARGED]
        ]

        latencies = [r.latency_ms for r in records if r.latency_ms > 0]
        median_lat = float(statistics.median(latencies)) if latencies else 0.0

        # Success rate with clearly defined denominator: successful_calls / total_calls
        success_rate = len(successful) / total_calls

        # Score out of 100: Base success weight 80%, Schema penalty 20%
        base_score = success_rate * 80.0
        schema_fidelity = (1.0 - (len(schema_invalid) / total_calls)) * 20.0
        total_score = max(0.0, min(100.0, base_score + schema_fidelity))

        # Total settled volume strictly from confirmed PAID calls
        total_volume_units = sum(
            r.amount_paid_units or usdc_to_base_units(r.amount_paid)
            for r in successful
        )
        total_volume_usdc = base_units_to_usdc(total_volume_units)

        # Price reference from latest record if available
        listed_price = records[0].listed_price if records else "0.000000"

        return ReputationMetrics(
            service_id=service_id,
            total_calls=total_calls,
            successful_calls=len(successful),
            success_rate=round(success_rate, 4),
            median_latency_ms=round(median_lat, 2),
            failure_counts=len(failed),
            schema_invalid_counts=len(schema_invalid),
            listed_price_usdc=listed_price,
            reputation_score=round(total_score, 1),
            total_volume_units=total_volume_units,
            total_volume_usdc=total_volume_usdc
        )

    def update_for_service(self, service_id: str) -> ReputationMetrics:
        """Calculate metrics and persist them to the durable database telemetry model.
        
        Raises exception if persistence fails so caller can track recovery.
        """
        metrics = self.calculate_for_service(service_id)
        db = None
        try:
            db = SessionLocal()
            model = db.query(SellerReputationModel).filter(
                SellerReputationModel.service_id == service_id
            ).first()
            if not model:
                model = SellerReputationModel(service_id=service_id)
                db.add(model)

            model.total_calls = metrics.total_calls
            model.successful_calls = metrics.successful_calls
            model.success_rate = metrics.success_rate
            model.median_latency_ms = metrics.median_latency_ms
            model.failure_counts = metrics.failure_counts
            model.schema_invalid_counts = metrics.schema_invalid_counts
            model.reputation_score = metrics.reputation_score
            model.total_volume_units = metrics.total_volume_units
            model.total_volume_usdc = metrics.total_volume_usdc
            model.sync_status = "synced"
            model.last_error = None
            model.updated_at = datetime.now(timezone.utc)
            db.commit()
            self._pending_repairs.discard(service_id)
        except Exception as e:
            logger.error(f"Failed to persist reputation metrics for {service_id}: {e}")
            self._pending_repairs.add(service_id)
            if db:
                try:
                    db.rollback()
                except Exception:
                    pass
            raise
        finally:
            if db:
                db.close()

        return metrics

    def repair_service_reputation(self, service_id: str) -> ReputationMetrics:
        """Retryable recovery mechanism: repairs seller metrics from the canonical ledger."""
        logger.info(f"Initiating reputation recovery for service: {service_id}")
        metrics = self.calculate_for_service(service_id)
        db = None
        try:
            db = SessionLocal()
            model = db.query(SellerReputationModel).filter(
                SellerReputationModel.service_id == service_id
            ).first()
            if not model:
                model = SellerReputationModel(service_id=service_id)
                db.add(model)

            model.total_calls = metrics.total_calls
            model.successful_calls = metrics.successful_calls
            model.success_rate = metrics.success_rate
            model.median_latency_ms = metrics.median_latency_ms
            model.failure_counts = metrics.failure_counts
            model.schema_invalid_counts = metrics.schema_invalid_counts
            model.reputation_score = metrics.reputation_score
            model.total_volume_units = metrics.total_volume_units
            model.total_volume_usdc = metrics.total_volume_usdc
            model.sync_status = "synced"
            model.last_error = None
            model.updated_at = datetime.now(timezone.utc)
            db.commit()
            self._pending_repairs.discard(service_id)
            logger.info(f"Successfully repaired reputation for service: {service_id}")
        except Exception as e:
            logger.error(f"Reputation repair failed for {service_id}: {e}")
            self._pending_repairs.add(service_id)
            raise
        finally:
            if db:
                db.close()

        return metrics

    def repair_all_reputations(self) -> Dict[str, ReputationMetrics]:
        """Repairs reputation metrics across all monitored services."""
        all_records = self.repo.list_records(limit=10000)
        service_ids = {r.service_id for r in all_records}
        service_ids.update(["data_001", "scraping_001", "inference_001"])
        service_ids.update(self._pending_repairs)
        results = {}
        for sid in sorted(service_ids):
            results[sid] = self.repair_service_reputation(sid)
        return results

    def get_pending_repairs(self) -> List[str]:
        """Returns list of service IDs that currently require reputation repair."""
        # Check in-memory set and database records marked pending_retry
        pending = set(self._pending_repairs)
        db = None
        try:
            db = SessionLocal()
            models = db.query(SellerReputationModel).filter(
                SellerReputationModel.sync_status != "synced"
            ).all()
            for m in models:
                pending.add(m.service_id)
        except Exception:
            pass
        finally:
            if db:
                db.close()
        return sorted(pending)

    def calculate_all(self) -> Dict[str, ReputationMetrics]:
        """Calculate reputation metrics for all registered services."""
        all_records = self.repo.list_records(limit=10000)
        service_ids = {r.service_id for r in all_records}
        # Include default services even if no calls yet
        service_ids.update(["data_001", "scraping_001", "inference_001"])
        return {sid: self.calculate_for_service(sid) for sid in sorted(service_ids)}
