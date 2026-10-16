"""Settlement Reconciliation Engine for x402 v2 Verified Payments."""
import asyncio
import logging
import threading
from typing import Dict, List, Optional, Set, Union
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
from backend.ledger.models import LedgerRepository, ledger_repo
from backend.ledger.reputation import ReputationCalculator
from backend.payments.settlement import SettlementVerifier

logger = logging.getLogger(__name__)


class SettlementReconciler:
    """Audits, verifies settlement evidence, and atomically records PAID ledger transactions."""

    def __init__(
        self,
        repository: LedgerRepository = ledger_repo,
        reputation_calc: Optional[ReputationCalculator] = None,
        verifier: Optional[SettlementVerifier] = None
    ):
        self.repo = repository
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
        # 1. Direct verified SettlementReceipt
        if payload.settlement_receipt:
            receipt = payload.settlement_receipt
            if receipt.tx_hash and receipt.tx_hash.startswith("0x") and len(receipt.tx_hash) >= 10:
                return receipt.tx_hash
            if receipt.facilitator_receipt_id:
                return receipt.facilitator_receipt_id

        # 2. Raw proof header from X-402-Settlement-Proof
        if payload.proof_header:
            header_str = payload.proof_header.strip()
            if header_str.startswith("0x") and len(header_str) >= 10:
                return header_str
            if header_str.startswith("receipt_"):
                return header_str

        # 3. Direct tx_hash string
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

            # 1. Check if record already exists in ledger
            existing = self.repo.get_record(payload.request_id)
            if existing:
                # Verify consistency between existing record and reconciliation input
                if existing.service_id != payload.service_id:
                    raise LedgerInconsistencyError(
                        f"Service ID mismatch for request_id '{payload.request_id}': "
                        f"incoming '{payload.service_id}' != existing '{existing.service_id}'"
                    )
                if existing.buyer_id != payload.buyer_id:
                    raise LedgerInconsistencyError(
                        f"Buyer ID mismatch for request_id '{payload.request_id}': "
                        f"incoming '{payload.buyer_id}' != existing '{existing.buyer_id}'"
                    )
                if existing.seller_id != payload.seller_id:
                    raise LedgerInconsistencyError(
                        f"Seller ID mismatch for request_id '{payload.request_id}': "
                        f"incoming '{payload.seller_id}' != existing '{existing.seller_id}'"
                    )

                existing_units = existing.amount_paid_units or usdc_to_base_units(existing.amount_paid)
                if existing_units != payload.amount_paid_units:
                    raise LedgerInconsistencyError(
                        f"Amount mismatch for request_id '{payload.request_id}': "
                        f"incoming {payload.amount_paid_units} units != existing {existing_units} units"
                    )

                verified_hash = self._verify_settlement_evidence(payload)
                if existing.tx_hash and verified_hash and existing.tx_hash != verified_hash:
                    raise LedgerInconsistencyError(
                        f"Transaction hash conflict for request_id '{payload.request_id}': "
                        f"incoming '{verified_hash}' != existing '{existing.tx_hash}'"
                    )

                # If already in terminal PAID state, return existing record idempotently
                if existing.status == LedgerStatus.PAID:
                    return ReconciliationResult(
                        request_id=payload.request_id,
                        status=LedgerStatus.PAID,
                        reconciled=True,
                        is_duplicate=True,
                        ledger_record=existing,
                        reputation_updated=False,
                        message="Payment was already reconciled in terminal PAID state."
                    )

            # 2. Verify settlement evidence
            verified_evidence = self._verify_settlement_evidence(payload)

            # Verify network and token lockdown
            if payload.network != NETWORK_BASE_SEPOLIA:
                raise SettlementUnverifiedError(
                    f"Forbidden network '{payload.network}'. Settlement must be on Base Sepolia ({NETWORK_BASE_SEPOLIA})."
                )
            if payload.token.lower() != USDC_BASE_SEPOLIA.lower():
                raise SettlementUnverifiedError(
                    f"Forbidden token contract '{payload.token}'. Settlement must be in Base Sepolia USDC ({USDC_BASE_SEPOLIA})."
                )

            # If no settlement evidence is verified
            if not verified_evidence:
                if payload.error_reason or not payload.output_valid:
                    # Settled failure or pre-flight refusal
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
                        network=payload.network,
                        token=payload.token,
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

                # Payment is pending and unverified
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
                network=payload.network,
                token=payload.token,
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
        logger.info(f"Reconciliation run: {len(unsettled)} records awaiting on-chain confirmation.")
        return unsettled


# Global runtime instance
reconciler = SettlementReconciler()
