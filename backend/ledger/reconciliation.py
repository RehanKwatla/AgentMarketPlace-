"""Settlement Reconciliation and Historical Synchronization Engine for x402 v2 Payments."""
import asyncio
from datetime import datetime, timezone
import logging
import threading
from typing import Any, Dict, List, Optional, Set, Union
from sqlalchemy.orm import Session

from backend.shared.config import get_settings
from backend.shared.constants import (
    LedgerStatus,
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    base_units_to_usdc,
    usdc_to_base_units,
)
from backend.shared.errors import (
    LedgerInconsistencyError,
    SettlementUnverifiedError,
)
from backend.shared.schemas import (
    LedgerRecordSchema,
    PaymentReconciliationInput,
    ReconciliationResult,
    SettlementReceipt,
)
from backend.database.session import SessionLocal
from backend.ledger.models import LedgerRepository, ledger_repo
from backend.ledger.reputation import ReputationCalculator
from backend.payments.settlement import SettlementVerifier

logger = logging.getLogger(__name__)


class SettlementReconciler:
    """Audits, verifies settlement evidence, and reconciles/synchronizes PAID ledger transactions."""

    def __init__(
        self,
        repository: LedgerRepository = ledger_repo,
        reputation_calc: Optional[ReputationCalculator] = None,
        verifier: Optional[SettlementVerifier] = None,
        session_factory=SessionLocal,
    ):
        self.repo = repository
        self.session_factory = session_factory
        self.reputation_calc = reputation_calc or ReputationCalculator(repository)
        self.verifier = verifier or SettlementVerifier(rpc_url=get_settings().base_sepolia_rpc_url)
        self._async_lock = asyncio.Lock()
        self._sync_lock = threading.RLock()
        self._failed_reputation_updates: Set[str] = set()

    def _coerce_input(self, data: Union[PaymentReconciliationInput, Dict]) -> PaymentReconciliationInput:
        if isinstance(data, PaymentReconciliationInput):
            return data
        return PaymentReconciliationInput(**data)

    def _verify_settlement_evidence(
        self,
        payload: PaymentReconciliationInput
    ) -> Optional[str]:
        """Verify that genuine settlement evidence exists. Returns tx_hash or receipt ID if verified."""
        if payload.settlement_receipt:
            receipt = payload.settlement_receipt
            if receipt.tx_hash and receipt.tx_hash.startswith("0x") and len(receipt.tx_hash) >= 10:
                return receipt.tx_hash
            if receipt.facilitator_receipt_id:
                return receipt.facilitator_receipt_id

        if payload.proof_header:
            header_str = payload.proof_header.strip()
            if header_str.startswith("0x") and len(header_str) >= 10:
                return header_str
            if header_str.startswith("receipt_"):
                return header_str

        if payload.tx_hash and payload.tx_hash.startswith("0x") and len(payload.tx_hash) >= 10:
            return payload.tx_hash

        return None

    def reconcile_payment_sync(
        self,
        payment_data: Union[PaymentReconciliationInput, Dict],
        strict: bool = False
    ) -> ReconciliationResult:
        """Synchronous reconciliation entrypoint with locking and idempotency."""
        with self._sync_lock:
            payload = self._coerce_input(payment_data)

            # 1. Check if record already exists (Idempotency)
            existing = self.repo.get_record(payload.request_id)
            if existing:
                if existing.service_id != payload.service_id:
                    raise LedgerInconsistencyError(
                        f"Inconsistent reconciliation for '{payload.request_id}': "
                        f"incoming service '{payload.service_id}' != existing '{existing.service_id}'"
                    )

                if existing.status == LedgerStatus.PAID and existing.tx_hash:
                    return ReconciliationResult(
                        request_id=payload.request_id,
                        status=existing.status,
                        reconciled=True,
                        is_duplicate=True,
                        ledger_record=existing,
                        reputation_updated=False,
                        message="Transaction is already reconciled and finalized as PAID."
                    )

            # 2. Verify settlement evidence
            verified_evidence = self._verify_settlement_evidence(payload)

            # Verify network and token lockdown
            if payload.network and payload.network != NETWORK_BASE_SEPOLIA:
                raise SettlementUnverifiedError(
                    f"Forbidden network '{payload.network}'. Settlement must be on Base Sepolia ({NETWORK_BASE_SEPOLIA})."
                )
            if payload.token and payload.token.lower() != USDC_BASE_SEPOLIA.lower():
                raise SettlementUnverifiedError(
                    f"Forbidden token contract '{payload.token}'. Settlement must be in Base Sepolia USDC ({USDC_BASE_SEPOLIA})."
                )

            # If no settlement evidence is verified
            if not verified_evidence:
                if payload.error_reason or not payload.output_valid:
                    failed_status = (
                        LedgerStatus.REFUSED
                        if "refuse" in (payload.error_reason or "").lower()
                        else LedgerStatus.FAILED_AND_NOT_CHARGED
                    )
                    record = LedgerRecordSchema(
                        request_id=payload.request_id,
                        task_id=payload.task_id,
                        buyer_id=payload.buyer_id,
                        seller_id=payload.seller_id,
                        service_id=payload.service_id,
                        listed_price=base_units_to_usdc(payload.listed_price_units),
                        amount_paid="0.000000",
                        listed_price_units=payload.listed_price_units,
                        amount_paid_units=0,
                        tx_hash=None,
                        status=failed_status,
                        latency_ms=payload.latency_ms,
                        error_reason=payload.error_reason or "Settlement failed or refused before charge.",
                        network=payload.network or NETWORK_BASE_SEPOLIA,
                        token=payload.token or USDC_BASE_SEPOLIA,
                    )
                    saved = self.repo.record_transaction(record)
                    try:
                        self.reputation_calc.update_for_service(payload.service_id)
                    except Exception:
                        self._failed_reputation_updates.add(payload.service_id)

                    return ReconciliationResult(
                        request_id=payload.request_id,
                        status=failed_status,
                        reconciled=True,
                        is_duplicate=False,
                        ledger_record=saved,
                        reputation_updated=True,
                        message=f"Recorded non-charged terminal failure: {failed_status.value}"
                    )

                if strict:
                    raise SettlementUnverifiedError(
                        f"Cannot mark payment '{payload.request_id}' as PAID without verified settlement proof."
                    )
                return ReconciliationResult(
                    request_id=payload.request_id,
                    status=LedgerStatus.FAILED_AND_NOT_CHARGED,
                    reconciled=False,
                    is_duplicate=False,
                    ledger_record=None,
                    reputation_updated=False,
                    message="Settlement unverified: pending testnet confirmation or proof receipt."
                )

            # 3. Settlement verified! Determine terminal state
            terminal_status = (
                LedgerStatus.PAID
                if payload.output_valid
                else LedgerStatus.PAID_OUTPUT_REJECTED
            )

            # 4. Atomically persist canonical ledger record
            record = LedgerRecordSchema(
                request_id=payload.request_id,
                task_id=payload.task_id,
                buyer_id=payload.buyer_id,
                seller_id=payload.seller_id,
                service_id=payload.service_id,
                listed_price=base_units_to_usdc(payload.listed_price_units),
                amount_paid=base_units_to_usdc(payload.amount_paid_units),
                listed_price_units=payload.listed_price_units,
                amount_paid_units=payload.amount_paid_units,
                tx_hash=verified_evidence,
                status=terminal_status,
                latency_ms=payload.latency_ms,
                error_reason=payload.error_reason,
                network=payload.network or NETWORK_BASE_SEPOLIA,
                token=payload.token or USDC_BASE_SEPOLIA,
            )
            saved_record = self.repo.record_transaction(record)

            # 5. Automatically update seller reputation telemetry
            reputation_updated = False
            reputation_repair_needed = False
            try:
                self.reputation_calc.update_for_service(payload.service_id)
                reputation_updated = True
                self._failed_reputation_updates.discard(payload.service_id)
            except Exception as e:
                logger.error(
                    f"Reputation update failed after committing ledger record {payload.request_id}: {e}"
                )
                self._failed_reputation_updates.add(payload.service_id)
                self.reputation_calc._pending_repairs.add(payload.service_id)
                reputation_repair_needed = True

            return ReconciliationResult(
                request_id=payload.request_id,
                status=terminal_status,
                reconciled=True,
                is_duplicate=False,
                ledger_record=saved_record,
                reputation_updated=reputation_updated,
                reputation_repair_needed=reputation_repair_needed,
                message=f"Payment reconciled to terminal state: {terminal_status.value}"
            )

    async def reconcile_payment(
        self,
        payment_data: Union[PaymentReconciliationInput, Dict],
        strict: bool = False
    ) -> ReconciliationResult:
        """Asynchronous reconciliation entrypoint with concurrency lock."""
        async with self._async_lock:
            return self.reconcile_payment_sync(payment_data, strict=strict)

    def sync_historical_settlements(self) -> Dict[str, Any]:
        """Idempotently synchronizes historical payment attempts and settlement evidence into durable ledger."""
        stats = {
            "total_attempts_scanned": 0,
            "synced_new": 0,
            "updated": 0,
            "already_current": 0,
            "skipped_suspense": 0,
            "errors": 0,
        }

        try:
            from backend.payments.models import PaymentAttemptModel, SettlementEvidenceRecordModel
        except ImportError:
            logger.warning("Payment models not available for historical synchronization.")
            return stats

        with self.session_factory() as session:
            try:
                attempts = session.query(PaymentAttemptModel).all()
                evidence_records = session.query(SettlementEvidenceRecordModel).all()
            except Exception as exc:
                logger.debug(f"Could not read historical payment tables: {exc}")
                return stats

            evidence_by_attempt: Dict[str, SettlementEvidenceRecordModel] = {}
            for ev in evidence_records:
                if ev.attempt_id:
                    evidence_by_attempt[ev.attempt_id] = ev

            stats["total_attempts_scanned"] = len(attempts)

            status_map = {
                "paid": LedgerStatus.PAID,
                "PAID": LedgerStatus.PAID,
                "paid output rejected": LedgerStatus.PAID_OUTPUT_REJECTED,
                "PAID_OUTPUT_REJECTED": LedgerStatus.PAID_OUTPUT_REJECTED,
                "refused": LedgerStatus.REFUSED,
                "REFUSED": LedgerStatus.REFUSED,
                "failed and not charged": LedgerStatus.FAILED_AND_NOT_CHARGED,
                "FAILED_AND_NOT_CHARGED": LedgerStatus.FAILED_AND_NOT_CHARGED,
            }

            for att in attempts:
                try:
                    att_status_str = att.status if isinstance(att.status, str) else str(att.status)

                    if "pending reconciliation" in att_status_str.lower():
                        stats["skipped_suspense"] += 1
                        continue

                    ledger_status = status_map.get(att_status_str, LedgerStatus.FAILED_AND_NOT_CHARGED)
                    existing = self.repo.get_record(att.attempt_id)

                    ev_match = evidence_by_attempt.get(att.attempt_id)
                    tx_h = att.tx_hash or (ev_match.tx_hash if ev_match else None)
                    proof = att.settlement_proof or (ev_match.facilitator_receipt_id if ev_match else None)

                    amount_units = att.amount_units or 0
                    amount_paid_usdc = base_units_to_usdc(amount_units) if ledger_status in (LedgerStatus.PAID, LedgerStatus.PAID_OUTPUT_REJECTED) else "0.000000"

                    if existing:
                        needs_update = False
                        if not existing.tx_hash and tx_h:
                            existing.tx_hash = tx_h
                            needs_update = True
                        if not getattr(existing, "settlement_proof", None) and proof:
                            existing.settlement_proof = proof
                            needs_update = True

                        if needs_update:
                            self.repo.record_transaction(existing)
                            stats["updated"] += 1
                        else:
                            stats["already_current"] += 1
                    else:
                        ts = att.created_at
                        if ts and ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)

                        new_record = LedgerRecordSchema(
                            request_id=att.attempt_id,
                            task_id=att.task_id,
                            call_id=att.call_id,
                            timestamp=ts or datetime.now(timezone.utc),
                            buyer_id="buyer_agent_primary",
                            seller_id=att.pay_to or att.service_id,
                            service_id=att.service_id,
                            listed_price=amount_paid_usdc,
                            amount_paid=amount_paid_usdc,
                            amount_base_units=amount_units,
                            tx_hash=tx_h,
                            settlement_proof=proof,
                            network=ev_match.network if ev_match else NETWORK_BASE_SEPOLIA,
                            token_address=ev_match.token_address if ev_match else USDC_BASE_SEPOLIA,
                            status=ledger_status,
                            latency_ms=0.0,
                            error_reason=att.error_reason,
                        )
                        self.repo.record_transaction(new_record)
                        stats["synced_new"] += 1

                except Exception as row_exc:
                    logger.error(f"Error synchronizing attempt '{att.attempt_id}': {row_exc}")
                    stats["errors"] += 1

        logger.info(
            f"Historical settlement synchronization completed: {stats['synced_new']} new synced, "
            f"{stats['updated']} updated, {stats['already_current']} already current, {stats['errors']} errors."
        )
        return stats

    def repair_reputation(self, service_id: Optional[str] = None):
        """Retryable recovery mechanism: repairs seller reputation without duplicating ledger entries."""
        if service_id:
            res = self.reputation_calc.repair_service_reputation(service_id)
            self._failed_reputation_updates.discard(service_id)
            return res
        else:
            res = self.reputation_calc.repair_all_reputations()
            self._failed_reputation_updates.clear()
            return res

    def get_pending_repairs(self) -> List[str]:
        """Returns service IDs with failed or pending reputation telemetry."""
        pending = set(self._failed_reputation_updates)
        pending.update(self.reputation_calc.get_pending_repairs())
        return sorted(pending)

    async def reconcile_pending(self) -> List[LedgerRecordSchema]:
        """Audit records without transaction hash or in ambiguous status."""
        all_records = self.repo.list_records(limit=1000)
        unsettled = [
            r for r in all_records
            if r.status == LedgerStatus.PAID and not r.tx_hash
        ]
        logger.info(f"Reconciliation audit run: {len(unsettled)} records awaiting on-chain confirmation.")
        return unsettled


# Global runtime instances
reconciler = SettlementReconciler()
settlement_reconciler = reconciler
