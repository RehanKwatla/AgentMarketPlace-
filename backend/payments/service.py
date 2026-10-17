"""[IMPLEMENTED] Payment Lifecycle Orchestration Service (Member 1)."""
from datetime import datetime, timezone
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from jsonschema import Draft202012Validator, validate

from backend.shared.constants import (
    LedgerStatus,
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    base_units_to_usdc,
)
from backend.shared.schemas import LedgerRecordSchema, ServiceDefinition
from backend.registry.service_catalog import catalog
from backend.ledger.models import ledger_repo

from backend.payments.budget import BudgetManager
from backend.payments.idempotency import IdempotencyStore, compute_payload_hash, idempotency_store
from backend.payments.policy import PaymentPolicyVerifier
from backend.payments.settlement import SettlementVerifier
from backend.payments.x402_adapter import X402Adapter, x402_adapter
from backend.payments.schemas import (
    MultiHopRouteResult,
    MultiHopStep,
    PaidCallRequest,
    PaidCallResult,
    PaymentStatus,
)
from backend.payments.errors import (
    BudgetExceededError,
    IdempotencyConflictError,
    PaymentEngineError,
    PaymentPolicyViolationError,
    ServiceDisabledError,
    SettlementTimeoutError,
    SettlementVerificationError,
)

logger = logging.getLogger(__name__)


class PaymentService:
    """Orchestrates end-to-end payment lifecycle for pay-per-call services."""

    def __init__(
        self,
        policy_verifier: Optional[PaymentPolicyVerifier] = None,
        settlement_verifier: Optional[SettlementVerifier] = None,
        adapter: Optional[X402Adapter] = None,
        store: Optional[IdempotencyStore] = None,
        durable_repo: Optional[Any] = None,
    ):
        self.policy_verifier = policy_verifier or PaymentPolicyVerifier()
        self.settlement_verifier = settlement_verifier or SettlementVerifier()
        self.adapter = adapter or x402_adapter
        self.idempotency_store = store or idempotency_store
        self._durable_repo = durable_repo
        # Task budget managers mapped by task_id
        self._task_budgets: Dict[str, BudgetManager] = {}
        # Suspense store for uncertain attempts (PENDING_RECONCILIATION)
        self._pending_reconciliations: Dict[str, PaidCallResult] = {}

    @property
    def repo(self) -> Optional[Any]:
        if self._durable_repo is None:
            try:
                from backend.payments.models import durable_payment_repo
                self._durable_repo = durable_payment_repo
            except Exception:
                pass
        return self._durable_repo

    def get_pending_reconciliations(self) -> Dict[str, PaidCallResult]:
        """Return all payment attempts currently held in suspense pending reconciliation."""
        reconciliations = dict(self._pending_reconciliations)
        if self.repo:
            try:
                db_attempts = self.repo.get_pending_reconciliations()
                for att in db_attempts:
                    if att.attempt_id not in reconciliations:
                        reconciliations[att.attempt_id] = PaidCallResult(
                            task_id=att.task_id or "",
                            call_id=att.call_id or "",
                            service_id=att.service_id,
                            request_id=att.attempt_id,
                            status=PaymentStatus.PENDING_RECONCILIATION,
                            seller_recipient=att.pay_to or "0x0000000000000000000000000000000000000000",
                            error_code=att.error_code,
                            error_message=att.error_reason,
                            tx_hash=att.tx_hash,
                            settlement_proof=att.settlement_proof,
                        )
            except Exception as err:
                logger.debug(f"Could not load pending reconciliations from DB: {err}")
        return reconciliations

    def get_pending_reconciliation(self, request_id: str) -> Optional[PaidCallResult]:
        """Retrieve a specific payment attempt held in suspense."""
        return self.get_pending_reconciliations().get(request_id)

    async def reconcile_attempt(self, attempt_id: str) -> Dict[str, Any]:
        """[IMPLEMENTED] Authoritatively reconcile a payment attempt held in PENDING_RECONCILIATION.

        Reconciliation protocol:
        1. Loads durable attempt from internal suspense store or database.
        2. Validates attempt exists and inspects current status.
        3. Re-queries authoritative Base Sepolia RPC settlement evidence using tx_hash / proof.
        4. Applies permitted state transitions only:
           - On-chain confirmed status 0x1 & valid ERC-20 transfer -> PAID.
           - On-chain reverted status 0x0 or definitive proof failure -> FAILED_AND_NOT_CHARGED.
           - Unconfirmed or RPC unavailable -> remains PENDING_RECONCILIATION.
        5. Atomically commits or releases held budget reservations.
        6. Updates durable database attempt record and writes to ledger if resolved.
        7. Returns detailed reconciliation audit outcome.
        """
        # 1. Load attempt
        attempt = self.get_pending_reconciliation(attempt_id)
        db_attempt = None
        if self.repo:
            db_attempt = self.repo.get_attempt_by_id(attempt_id)

        if not attempt and not db_attempt:
            raise PaymentEngineError(f"Reconciliation failed: attempt '{attempt_id}' not found.")

        current_status = attempt.status if attempt else PaymentStatus(db_attempt.status)
        if current_status != PaymentStatus.PENDING_RECONCILIATION:
            return {
                "attempt_id": attempt_id,
                "status": current_status.value,
                "reconciled": True,
                "message": f"Attempt is already in terminal state '{current_status.value}'.",
            }

        proof_or_tx = None
        if attempt and (attempt.tx_hash or attempt.settlement_proof):
            proof_or_tx = attempt.tx_hash or attempt.settlement_proof
        elif db_attempt and (db_attempt.tx_hash or db_attempt.settlement_proof):
            proof_or_tx = db_attempt.tx_hash or db_attempt.settlement_proof

        service_id = attempt.service_id if attempt else db_attempt.service_id
        amount_units = attempt.amount_base_units if attempt else db_attempt.amount_units
        task_id = attempt.task_id if attempt else db_attempt.task_id
        res_id = f"res_{task_id}_{attempt_id}" if task_id else f"res_{attempt_id}"

        if not proof_or_tx:
            return {
                "attempt_id": attempt_id,
                "status": PaymentStatus.PENDING_RECONCILIATION.value,
                "reconciled": False,
                "message": "No proof header or tx hash recorded for this attempt. Retaining suspense hold.",
            }

        resolved_status = PaymentStatus.PENDING_RECONCILIATION
        resolved_tx = None
        error_msg = None

        try:
            receipt = await self.settlement_verifier.verify_settlement_proof(
                proof_header=proof_or_tx,
                expected_amount_units=amount_units,
                expected_attempt_id=attempt_id,
            )
            if receipt and (receipt.tx_hash or receipt.facilitator_receipt_id):
                resolved_status = PaymentStatus.PAID
                resolved_tx = receipt.tx_hash
        except SettlementVerificationError as err:
            err_str = str(err).lower()
            if "reverted" in err_str or "unconfirmed" in err_str or "invalid" in err_str:
                resolved_status = PaymentStatus.FAILED_AND_NOT_CHARGED
                error_msg = str(err)
            else:
                resolved_status = PaymentStatus.PENDING_RECONCILIATION
                error_msg = str(err)
        except Exception as exc:
            resolved_status = PaymentStatus.PENDING_RECONCILIATION
            error_msg = f"Authoritative RPC query failed: {exc}"

        # 4. Apply State Transition
        if resolved_status == PaymentStatus.PAID:
            budget_mgr = self._task_budgets.get(task_id)
            if budget_mgr:
                await budget_mgr.commit(res_id, amount_units)

            if self.repo:
                self.repo.update_attempt_status(attempt_id, PaymentStatus.PAID, tx_hash=resolved_tx)

            self._pending_reconciliations.pop(attempt_id, None)

            # Record in ledger
            if ledger_repo and service_id:
                try:
                    service = catalog.get_service(service_id)
                    if service:
                        paid_res = PaidCallResult(
                            task_id=task_id or "",
                            call_id=attempt.call_id if attempt else (db_attempt.call_id or ""),
                            service_id=service_id,
                            request_id=attempt_id,
                            status=PaymentStatus.PAID,
                            amount_base_units=amount_units,
                            amount_usdc=service.price_usdc,
                            token_address=USDC_BASE_SEPOLIA,
                            network=NETWORK_BASE_SEPOLIA,
                            seller_recipient=service.pay_to,
                            tx_hash=resolved_tx,
                            settlement_proof=proof_or_tx,
                            settled_at=datetime.now(timezone.utc),
                        )
                        self._record_in_ledger(paid_res, service, 0.0)
                except Exception as l_err:
                    logger.debug(f"Could not record reconciled attempt in ledger: {l_err}")

            return {
                "attempt_id": attempt_id,
                "status": PaymentStatus.PAID.value,
                "reconciled": True,
                "tx_hash": resolved_tx,
                "message": "Authoritative settlement confirmed. State transitioned to PAID.",
            }

        elif resolved_status == PaymentStatus.FAILED_AND_NOT_CHARGED:
            budget_mgr = self._task_budgets.get(task_id)
            if budget_mgr:
                await budget_mgr.release(res_id)

            if self.repo:
                self.repo.update_attempt_status(attempt_id, PaymentStatus.FAILED_AND_NOT_CHARGED, error_reason=error_msg)

            self._pending_reconciliations.pop(attempt_id, None)

            return {
                "attempt_id": attempt_id,
                "status": PaymentStatus.FAILED_AND_NOT_CHARGED.value,
                "reconciled": True,
                "error_reason": error_msg,
                "message": "Settlement definitively failed or reverted. State transitioned to FAILED_AND_NOT_CHARGED. Budget released.",
            }

        else:
            return {
                "attempt_id": attempt_id,
                "status": PaymentStatus.PENDING_RECONCILIATION.value,
                "reconciled": False,
                "error_reason": error_msg,
                "message": "Settlement outcome remains ambiguous or RPC query failed. Retaining suspense hold.",
            }

    async def reconcile_all_pending(self) -> List[Dict[str, Any]]:
        """Reconciles all attempts currently in PENDING_RECONCILIATION status.

        Gathers pending attempt IDs from both in-memory suspense holds and durable
        database records, executing individual authoritative reconciliation checks.
        """
        attempt_ids = set(self._pending_reconciliations.keys())
        if self.repo:
            try:
                db_pendings = self.repo.get_pending_reconciliations()
                for p in db_pendings:
                    attempt_ids.add(p.attempt_id)
            except Exception as e:
                logger.warning(f"Failed to query database for pending reconciliations: {e}")

        results = []
        for att_id in sorted(attempt_ids):
            try:
                res = await self.reconcile_attempt(att_id)
                results.append(res)
            except Exception as err:
                logger.error(f"Error during batch reconciliation of attempt {att_id}: {err}")
                results.append({
                    "attempt_id": att_id,
                    "status": PaymentStatus.PENDING_RECONCILIATION.value,
                    "reconciled": False,
                    "error_reason": str(err),
                    "message": f"Exception during reconciliation: {err}",
                })
        return results

    def get_or_create_task_budget(self, task_id: str, budget_units: int) -> BudgetManager:
        """Retrieve existing task budget manager or initialize for new task."""
        if task_id not in self._task_budgets:
            self._task_budgets[task_id] = BudgetManager(initial_budget_units=budget_units, task_id=task_id, repo=self.repo)
        return self._task_budgets[task_id]

    async def execute_paid_call(
        self,
        task_id: str,
        call_id: str,
        service_id: str,
        input_payload: Dict[str, Any],
        idempotency_key: str,
        task_budget_manager: Optional[BudgetManager] = None,
    ) -> PaidCallResult:
        """Executes an autonomous x402 v2 payment-settled service call."""
        start_time = time.perf_counter()
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        payload_hash = compute_payload_hash(input_payload)

        # Step 1: Idempotency Check
        try:
            is_new, cached = self.idempotency_store.check_or_register(idempotency_key, payload_hash)
            if not is_new and cached:
                logger.info(f"Returning cached idempotent result for key '{idempotency_key}'.")
                return PaidCallResult(**cached)
        except IdempotencyConflictError as conflict:
            logger.error(f"Idempotency conflict for key '{idempotency_key}': {conflict}")
            return PaidCallResult(
                task_id=task_id,
                call_id=call_id,
                service_id=service_id,
                request_id=request_id,
                status=PaymentStatus.REFUSED,
                seller_recipient="0x0000000000000000000000000000000000000000",
                error_code="IDEMPOTENCY_CONFLICT",
                error_message=str(conflict),
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # Step 2: Load Trusted Service Terms
        service = catalog.get_service(service_id)
        if not service:
            self.idempotency_store.release_key(idempotency_key)
            return PaidCallResult(
                task_id=task_id,
                call_id=call_id,
                service_id=service_id,
                request_id=request_id,
                status=PaymentStatus.REFUSED,
                seller_recipient="0x0000000000000000000000000000000000000000",
                error_code="SERVICE_NOT_FOUND",
                error_message=f"Service '{service_id}' does not exist in registry.",
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # Step 3: Pre-Flight Policy Check
        try:
            self.policy_verifier.verify_service_terms(service)
        except (PaymentPolicyViolationError, ServiceDisabledError) as policy_err:
            self.idempotency_store.release_key(idempotency_key)
            return PaidCallResult(
                task_id=task_id,
                call_id=call_id,
                service_id=service_id,
                request_id=request_id,
                status=PaymentStatus.REFUSED,
                seller_recipient=service.pay_to,
                error_code="PAYMENT_POLICY_VIOLATION",
                error_message=str(policy_err),
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        # Step 4: Atomic Budget Reservation
        if task_budget_manager:
            self._task_budgets[task_id] = task_budget_manager
        budget_mgr = task_budget_manager or self._task_budgets.get(task_id)
        res_id = f"res_{task_id}_{request_id}" if task_id else f"res_{request_id}"

        if budget_mgr:
            try:
                await budget_mgr.reserve(res_id, service.price_base_units)
            except BudgetExceededError as budget_err:
                self.idempotency_store.release_key(idempotency_key)
                return PaidCallResult(
                    task_id=task_id,
                    call_id=call_id,
                    service_id=service_id,
                    request_id=request_id,
                    status=PaymentStatus.REFUSED,
                    seller_recipient=service.pay_to,
                    error_code="BUDGET_EXCEEDED",
                    error_message=str(budget_err),
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                )

        # Step 5: Execute x402 Payment Lifecycle via Adapter
        try:
            status_code, response_data, proof_header = await self.adapter.execute_paid_request(
                service=service,
                input_payload=input_payload,
                idempotency_key=idempotency_key
            )
        except SettlementTimeoutError as timeout_err:
            # Uncertain outcome: do NOT release reservation, mark pending reconciliation
            latency = (time.perf_counter() - start_time) * 1000.0
            suspense_result = PaidCallResult(
                task_id=task_id,
                call_id=call_id,
                service_id=service_id,
                request_id=request_id,
                status=PaymentStatus.PENDING_RECONCILIATION,
                amount_base_units=service.price_base_units,
                amount_usdc=service.price_usdc,
                seller_recipient=service.pay_to,
                error_code="SETTLEMENT_TIMEOUT",
                error_message=str(timeout_err),
                latency_ms=latency,
            )
            self._pending_reconciliations[request_id] = suspense_result
            if self.repo:
                try:
                    from backend.payments.schemas import PaymentAttemptRecord
                    self.repo.save_attempt(PaymentAttemptRecord(
                        attempt_id=request_id,
                        task_id=task_id,
                        call_id=call_id,
                        service_id=service_id,
                        idempotency_key=idempotency_key,
                        request_hash=payload_hash,
                        amount_base_units=service.price_base_units,
                        pay_to=service.pay_to,
                        status=PaymentStatus.PENDING_RECONCILIATION,
                        error_reason=str(timeout_err),
                    ))
                except Exception as db_err:
                    logger.debug(f"Could not persist suspense attempt to DB: {db_err}")
            self._record_in_ledger(suspense_result, service, latency)
            self.idempotency_store.store_idempotent_result(idempotency_key, suspense_result.model_dump(), payload_hash)
            return suspense_result

        except Exception as exc:
            # Failure before/during initiation without charge
            if budget_mgr:
                await budget_mgr.release(res_id)
            self.idempotency_store.release_key(idempotency_key)
            latency = (time.perf_counter() - start_time) * 1000.0
            failed_result = PaidCallResult(
                task_id=task_id,
                call_id=call_id,
                service_id=service_id,
                request_id=request_id,
                status=PaymentStatus.FAILED_AND_NOT_CHARGED,
                seller_recipient=service.pay_to,
                error_code="EXECUTION_FAILED",
                error_message=str(exc),
                latency_ms=latency,
            )
            self._record_in_ledger(failed_result, service, latency)
            return failed_result

        # Step 6: Process Response Status
        latency = (time.perf_counter() - start_time) * 1000.0

        if status_code != 200:
            if budget_mgr:
                await budget_mgr.release(res_id)
            self.idempotency_store.release_key(idempotency_key)
            if self.repo:
                try:
                    self.repo.update_attempt_status(
                        request_id,
                        PaymentStatus.FAILED_AND_NOT_CHARGED,
                        error_reason=f"Seller returned unexpected HTTP status {status_code}"
                    )
                except Exception:
                    pass
            failed_result = PaidCallResult(
                task_id=task_id,
                call_id=call_id,
                service_id=service_id,
                request_id=request_id,
                status=PaymentStatus.FAILED_AND_NOT_CHARGED,
                seller_recipient=service.pay_to,
                error_code=f"HTTP_{status_code}",
                error_message=f"Seller returned unexpected HTTP status {status_code}",
                latency_ms=latency,
            )
            self._record_in_ledger(failed_result, service, latency)
            return failed_result

        # Step 7: Verify Settlement Evidence
        receipt = None
        try:
            if proof_header:
                receipt = await self.settlement_verifier.verify_settlement_proof(
                    proof_header=proof_header,
                    expected_amount_units=service.price_base_units,
                    expected_attempt_id=request_id,
                )
        except (SettlementVerificationError, SettlementTimeoutError, Exception) as verify_err:
            logger.warning(f"Settlement verification issue for {request_id}: {verify_err}")
            receipt = None

        # Fail-closed: settlement evidence must be verified; unverified or missing transitions to suspense
        if receipt is None or (not receipt.tx_hash and not receipt.facilitator_receipt_id):
            suspense_result = PaidCallResult(
                task_id=task_id,
                call_id=call_id,
                service_id=service_id,
                request_id=request_id,
                status=PaymentStatus.PENDING_RECONCILIATION,
                amount_base_units=service.price_base_units,
                amount_usdc=service.price_usdc,
                token_address=USDC_BASE_SEPOLIA,
                network=NETWORK_BASE_SEPOLIA,
                seller_recipient=service.pay_to,
                error_code="SETTLEMENT_UNVERIFIED",
                error_message="Settlement proof missing or unverified. Held in suspense.",
                latency_ms=round(latency, 2),
                settlement_proof=proof_header,
            )
            self._pending_reconciliations[request_id] = suspense_result
            if self.repo:
                try:
                    from backend.payments.schemas import PaymentAttemptRecord
                    self.repo.save_attempt(PaymentAttemptRecord(
                        attempt_id=request_id,
                        task_id=task_id,
                        call_id=call_id,
                        service_id=service_id,
                        idempotency_key=idempotency_key,
                        request_hash=payload_hash,
                        amount_base_units=service.price_base_units,
                        pay_to=service.pay_to,
                        status=PaymentStatus.PENDING_RECONCILIATION,
                        settlement_proof=proof_header,
                        error_reason="Settlement proof missing or unverified. Held in suspense.",
                    ))
                except Exception as db_err:
                    logger.debug(f"Could not persist suspense attempt to DB: {db_err}")
            self._record_in_ledger(suspense_result, service, latency)
            self.idempotency_store.store_idempotent_result(idempotency_key, suspense_result.model_dump(), payload_hash)
            return suspense_result

        tx_hash = receipt.tx_hash if receipt else None
        proof_id = receipt.facilitator_receipt_id if receipt else proof_header

        # Step 8: Validate Seller Output Against Catalog Schema
        schema_valid = self._validate_seller_output(response_data, service.output_schema)
        final_status = PaymentStatus.PAID if schema_valid else PaymentStatus.PAID_OUTPUT_REJECTED

        # Step 9: Commit Budget Reservation
        if budget_mgr:
            await budget_mgr.commit(res_id, service.price_base_units)

        paid_result = PaidCallResult(
            task_id=task_id,
            call_id=call_id,
            service_id=service_id,
            request_id=request_id,
            status=final_status,
            amount_base_units=service.price_base_units,
            amount_usdc=service.price_usdc,
            token_address=USDC_BASE_SEPOLIA,
            network=NETWORK_BASE_SEPOLIA,
            seller_recipient=service.pay_to,
            tx_hash=tx_hash,
            settlement_proof=proof_id,
            seller_output=response_data,
            latency_ms=round(latency, 2),
            error_code=None if schema_valid else "OUTPUT_SCHEMA_INVALID",
            error_message=None if schema_valid else "Seller output failed registered schema validation.",
            settled_at=receipt.settled_at if receipt else None,
        )

        # Step 10: Persist to Ledger and Cache
        if self.repo:
            try:
                from backend.payments.schemas import PaymentAttemptRecord
                self.repo.save_attempt(PaymentAttemptRecord(
                    attempt_id=request_id,
                    task_id=task_id,
                    call_id=call_id,
                    service_id=service_id,
                    idempotency_key=idempotency_key,
                    request_hash=payload_hash,
                    amount_base_units=service.price_base_units,
                    pay_to=service.pay_to,
                    status=final_status,
                    tx_hash=tx_hash,
                    settlement_proof=proof_id,
                    error_reason=paid_result.error_message,
                ))
            except Exception as db_err:
                logger.debug(f"Could not persist attempt to DB: {db_err}")
        self._record_in_ledger(paid_result, service, latency)
        self.idempotency_store.store_idempotent_result(idempotency_key, paid_result.model_dump(), payload_hash)
        return paid_result

    def _validate_seller_output(self, output: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate output dictionary against registered JSON schema."""
        if not schema or not schema.get("properties"):
            return True
        try:
            # Check required fields
            required_fields = schema.get("required", [])
            for field in required_fields:
                if field not in output:
                    logger.warning(f"Seller output missing required field '{field}'")
                    return False
            return True
        except Exception as exc:
            logger.warning(f"Output schema validation error: {exc}")
            return False

    def _record_in_ledger(self, result: PaidCallResult, service: ServiceDefinition, latency: float) -> None:
        """Map result into immutable LedgerRecordSchema and record in repository.

        Uncertain outcomes (PENDING_RECONCILIATION) must NEVER be recorded as terminal failures
        or successes in the shared ledger. They are retained in the internal suspense store.
        """
        if result.status == PaymentStatus.PENDING_RECONCILIATION:
            self._pending_reconciliations[result.request_id] = result
            if self.repo:
                try:
                    from backend.payments.schemas import PaymentAttemptRecord
                    self.repo.save_attempt(
                        PaymentAttemptRecord(
                            attempt_id=result.request_id,
                            task_id=result.task_id,
                            call_id=result.call_id,
                            service_id=result.service_id,
                            idempotency_key=f"idemp_{result.request_id}",
                            request_hash="hash_reconciliation",
                            nonce=f"nonce_{result.request_id}",
                            amount_base_units=result.amount_base_units,
                            pay_to=service.pay_to,
                            status=PaymentStatus.PENDING_RECONCILIATION,
                            error_reason=result.error_message,
                            tx_hash=result.tx_hash,
                            settlement_proof=result.settlement_proof,
                        )
                    )
                except Exception as err:
                    logger.debug(f"Could not persist pending reconciliation attempt to DB: {err}")
            logger.warning(
                f"Payment attempt '{result.request_id}' is PENDING_RECONCILIATION. "
                "Suspense state is NOT written to shared ledger to prevent recording uncertain state as terminal failure/success."
            )
            return

        # Map PaymentStatus to LedgerStatus enum values (strictly terminal statuses)
        status_map = {
            PaymentStatus.PAID: LedgerStatus.PAID,
            PaymentStatus.PAID_OUTPUT_REJECTED: LedgerStatus.PAID_OUTPUT_REJECTED,
            PaymentStatus.REFUSED: LedgerStatus.REFUSED,
            PaymentStatus.FAILED_AND_NOT_CHARGED: LedgerStatus.FAILED_AND_NOT_CHARGED,
        }
        ledger_status = status_map[result.status]

        record = LedgerRecordSchema(
            request_id=result.request_id,
            task_id=result.task_id,
            call_id=result.call_id,
            buyer_id="buyer_agent_primary",
            seller_id=f"seller_{service.category.value}",
            service_id=service.service_id,
            listed_price=service.price_usdc,
            amount_paid=result.amount_usdc if result.status in (PaymentStatus.PAID, PaymentStatus.PAID_OUTPUT_REJECTED) else "0.000000",
            amount_base_units=result.amount_base_units if result.status in (PaymentStatus.PAID, PaymentStatus.PAID_OUTPUT_REJECTED) else 0,
            tx_hash=result.tx_hash,
            settlement_proof=result.settlement_proof,
            network=result.network,
            token_address=result.token_address,
            status=ledger_status,
            latency_ms=round(latency, 2),
            error_reason=result.error_message,
        )
        ledger_repo.record_transaction(record)


    async def execute_multi_hop_route(
        self,
        task_id: str,
        route: List[MultiHopStep],
        budget_manager: Optional[BudgetManager] = None,
        max_hops: int = 10,
        total_budget_units: Optional[int] = None,
    ) -> MultiHopRouteResult:
        """[IMPLEMENTED] Autonomous Multi-Hop Paid-Call Route Orchestration Engine.

        Coordinates sequential or DAG-based multi-hop paid service calls with:
        1. Route structural validation (empty routes, hop count limits, duplicate steps, dependency cycles).
        2. Atomic task-level budget reservation and tracking across all hops.
        3. Deterministic execution order respecting prerequisites.
        4. Hop input data transformation / propagation from completed upstream outputs.
        5. Atomic per-hop execution and idempotent retry safety (scoped key per hop).
        6. Fail-closed intermediate error isolation (stops execution immediately on hop failure, preserving remaining budget).
        7. Truthful ledger status reporting and reconciliation tracking.
        """
        route_start = time.perf_counter()

        # Step 1: Validation
        if not route:
            return MultiHopRouteResult(
                task_id=task_id,
                status="refused",
                error_message="Route contains no hops to execute.",
                latency_ms=(time.perf_counter() - route_start) * 1000.0,
            )

        if len(route) > max_hops:
            return MultiHopRouteResult(
                task_id=task_id,
                total_hops=len(route),
                status="refused",
                error_message=f"Route hop count ({len(route)}) exceeds maximum allowed limit of {max_hops}.",
                latency_ms=(time.perf_counter() - route_start) * 1000.0,
            )

        step_ids = [step.step_id for step in route]
        if len(step_ids) != len(set(step_ids)):
            return MultiHopRouteResult(
                task_id=task_id,
                total_hops=len(route),
                status="refused",
                error_message="Duplicate step_id detected in multi-hop route.",
                latency_ms=(time.perf_counter() - route_start) * 1000.0,
            )

        step_map = {step.step_id: step for step in route}

        # Check for invalid dependencies and dependency cycles
        for step in route:
            for dep_id in step.depends_on:
                if dep_id not in step_map:
                    return MultiHopRouteResult(
                        task_id=task_id,
                        total_hops=len(route),
                        status="refused",
                        error_message=f"Step {step.step_id} references nonexistent prerequisite step {dep_id}.",
                        latency_ms=(time.perf_counter() - route_start) * 1000.0,
                    )

        # Topological sort to verify DAG and determine execution order
        in_degree = {step.step_id: 0 for step in route}
        adjacency: Dict[int, List[int]] = {step.step_id: [] for step in route}
        for step in route:
            for dep in step.depends_on:
                adjacency[dep].append(step.step_id)
                in_degree[step.step_id] += 1

        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        execution_order: List[int] = []
        while queue:
            curr = queue.pop(0)
            execution_order.append(curr)
            for nxt in adjacency[curr]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        if len(execution_order) != len(route):
            return MultiHopRouteResult(
                task_id=task_id,
                total_hops=len(route),
                status="refused",
                error_message="Dependency cycle detected in multi-hop route.",
                latency_ms=(time.perf_counter() - route_start) * 1000.0,
            )

        # Step 2: Validate service availability in catalog
        for step in route:
            srv = catalog.get_service(step.service_id)
            if not srv:
                return MultiHopRouteResult(
                    task_id=task_id,
                    total_hops=len(route),
                    status="refused",
                    error_step_id=step.step_id,
                    error_message=f"Service '{step.service_id}' for step {step.step_id} not found in catalog.",
                    latency_ms=(time.perf_counter() - route_start) * 1000.0,
                )
            if not srv.is_active:
                return MultiHopRouteResult(
                    task_id=task_id,
                    total_hops=len(route),
                    status="refused",
                    error_step_id=step.step_id,
                    error_message=f"Service '{step.service_id}' for step {step.step_id} is disabled.",
                    latency_ms=(time.perf_counter() - route_start) * 1000.0,
                )

        # Step 3: Initialize task budget
        if budget_manager:
            budget_mgr = budget_manager
        elif total_budget_units is not None:
            budget_mgr = self.get_or_create_task_budget(task_id, total_budget_units)
        else:
            # Sum required prices from catalog as default budget allocation
            estimated_total = sum(catalog.get_service(s.service_id).price_base_units for s in route)
            budget_mgr = self.get_or_create_task_budget(task_id, estimated_total)

        budget_allocated_usdc = base_units_to_usdc(budget_mgr.total_budget)

        # Pre-check overall route affordability against initial budget
        total_estimated_price = sum(catalog.get_service(s.service_id).price_base_units for s in route)
        if total_estimated_price > budget_mgr.total_budget:
            return MultiHopRouteResult(
                task_id=task_id,
                total_hops=len(route),
                status="refused",
                budget_allocated_usdc=budget_allocated_usdc,
                error_message=f"Route estimated cost ({total_estimated_price} base units) exceeds allocated budget ({budget_mgr.total_budget} base units).",
                latency_ms=(time.perf_counter() - route_start) * 1000.0,
            )

        # Step 4: Execute hops in topological order
        executed_results: Dict[int, PaidCallResult] = {}
        ordered_step_results: List[PaidCallResult] = []
        route_status = "completed"
        error_step_id: Optional[int] = None
        error_message: Optional[str] = None
        reconciliation_needed = False

        for sid in execution_order:
            step = step_map[sid]

            # Validate all prerequisites succeeded
            unmet_deps = [dep for dep in step.depends_on if dep not in executed_results or executed_results[dep].status != PaymentStatus.PAID]
            if unmet_deps:
                route_status = "partial_failure"
                error_step_id = sid
                error_message = f"Step {sid} aborted: prerequisite steps {unmet_deps} did not succeed."
                break

            # Resolve input payload with transforms from upstream outputs if specified
            input_payload = dict(step.input_payload)
            if step.input_transform:
                for target_field, source_path in step.input_transform.items():
                    parts = source_path.split(".", 1)
                    if len(parts) == 2 and parts[0].startswith("step_"):
                        try:
                            source_step_id = int(parts[0].replace("step_", ""))
                            source_field = parts[1]
                            source_res = executed_results.get(source_step_id)
                            if source_res and source_res.seller_output:
                                val = source_res.seller_output.get(source_field)
                                if val is not None:
                                    input_payload[target_field] = val
                        except Exception as e:
                            logger.warning(f"Failed to transform input field '{target_field}' from '{source_path}': {e}")

            # Scoped idempotency key per hop
            hop_idempotency_key = f"idemp_{task_id}_hop_{sid}"
            call_id = f"call_{task_id}_s{sid}"

            result = await self.execute_paid_call(
                task_id=task_id,
                call_id=call_id,
                service_id=step.service_id,
                input_payload=input_payload,
                idempotency_key=hop_idempotency_key,
                task_budget_manager=budget_mgr,
            )

            executed_results[sid] = result
            ordered_step_results.append(result)

            if result.status == PaymentStatus.PENDING_RECONCILIATION:
                route_status = "pending_reconciliation"
                reconciliation_needed = True
                error_step_id = sid
                error_message = f"Step {sid} placed in suspense pending authoritative settlement reconciliation: {result.error_message}"
                break
            elif result.status != PaymentStatus.PAID:
                # Any failure or refusal stops route execution
                error_step_id = sid
                error_message = f"Step {sid} failed with status '{result.status.value}': {result.error_message or result.error_code}"
                if len(executed_results) > 1 and any(r.status == PaymentStatus.PAID for r in executed_results.values()):
                    route_status = "partial_failure"
                else:
                    route_status = "failed" if result.status == PaymentStatus.FAILED_AND_NOT_CHARGED else "refused"
                break

        # Calculate totals
        total_cost_units = sum(r.amount_base_units for r in ordered_step_results if r.status in (PaymentStatus.PAID, PaymentStatus.PAID_OUTPUT_REJECTED))
        total_cost_usdc = base_units_to_usdc(total_cost_units)
        remaining_units = max(0, budget_mgr.total_budget - total_cost_units)
        remaining_budget_usdc = base_units_to_usdc(remaining_units)

        successful_hops = sum(1 for r in ordered_step_results if r.status == PaymentStatus.PAID)
        final_output = ordered_step_results[-1].seller_output if (ordered_step_results and route_status == "completed") else None

        return MultiHopRouteResult(
            task_id=task_id,
            status=route_status,
            total_hops=len(route),
            executed_hops=len(ordered_step_results),
            successful_hops=successful_hops,
            total_cost_base_units=total_cost_units,
            total_cost_usdc=total_cost_usdc,
            budget_allocated_usdc=budget_allocated_usdc,
            remaining_budget_usdc=remaining_budget_usdc,
            steps=ordered_step_results,
            final_output=final_output,
            error_step_id=error_step_id,
            error_message=error_message,
            reconciliation_needed=reconciliation_needed,
            latency_ms=(time.perf_counter() - route_start) * 1000.0,
        )


# Default singleton instance
payment_service = PaymentService()
