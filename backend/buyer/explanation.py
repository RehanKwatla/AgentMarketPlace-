"""Purchase Explanation Generator providing transparent spending narratives and authoritative ledger reconciliation."""
from typing import Any, List, Optional
from backend.shared.constants import (
    base_units_to_usdc,
    usdc_to_base_units,
)
from backend.buyer.schemas import (
    CallExecutionSummary,
    CallStatus,
    PurchaseExplanation,
    ServiceCallRecord,
    ServiceSelectionReason,
    SpendingSummary,
)
from backend.registry.service import RegistryService, registry_service
from backend.ledger.models import LedgerRepository, ledger_repo


class ExplanationGenerator:
    """Produces structured narratives explaining service selection, validation, and spending
    backed by Member 4's authoritative audit ledger.
    """

    def __init__(
        self,
        registry: Optional[RegistryService] = None,
        ledger: Optional[LedgerRepository] = None,
    ):
        self.registry = registry or registry_service
        self.ledger = ledger or ledger_repo

    @staticmethod
    def _format_explorer_url(tx_hash: Optional[str]) -> Optional[str]:
        """Construct Base Sepolia explorer link only when a verified transaction hash is present.
        Do NOT fabricate links for non-hash tokens, receipts, or empty values.
        """
        if not tx_hash or not isinstance(tx_hash, str):
            return None
        cleaned = tx_hash.strip()
        # Official Base Sepolia transaction hashes are 66 hex characters starting with '0x'
        if cleaned.startswith("0x") and len(cleaned) == 66:
            try:
                int(cleaned[2:], 16)
                return f"https://sepolia.basescan.org/tx/{cleaned}"
            except ValueError:
                return None
        return None

    def generate_explanation(
        self,
        task_prompt: str,
        budget_usdc: str,
        calls: List[ServiceCallRecord],
        fallbacks: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        planned_calls: Optional[List[Any]] = None,
    ) -> PurchaseExplanation:
        """Construct full PurchaseExplanation backed by Member 4's ledger records."""
        fallbacks = fallbacks or []
        warnings = list(warnings or [])

        budget_units = usdc_to_base_units(budget_usdc)

        # 1. Compute estimated cost from planned or requested calls
        if planned_calls:
            estimated_cost_units = sum(
                getattr(p, "estimated_price_units", usdc_to_base_units(getattr(p, "price_usdc", "0.000000")))
                for p in planned_calls
            )
        else:
            estimated_cost_units = sum(usdc_to_base_units(c.listed_price_usdc) for c in calls)

        # 2. Authoritative Ledger Verification & Execution Accounting
        verified_spent_units = 0
        uncertain_pending_units = 0
        reasons: List[ServiceSelectionReason] = []
        call_executions: List[CallExecutionSummary] = []
        accepted: List[str] = []
        rejected: List[str] = []
        tx_refs: List[str] = []
        explorer_links: List[str] = []

        for c in calls:
            category_str = c.category.value if hasattr(c.category, "value") else str(c.category)
            is_fallback = any(c.service_id in fb for fb in fallbacks)

            # Query authoritative ledger record from Member 4's ledger
            ledger_entry = self.ledger.get_record(c.call_id)

            call_verified_paid_str = "0.000000"
            is_settlement_verified = False
            tx_hash = None

            if ledger_entry:
                tx_hash = ledger_entry.tx_hash or c.transaction_hash
                ls_raw = ledger_entry.status.value if hasattr(ledger_entry.status, "value") else str(ledger_entry.status)
                ls_clean = ls_raw.lower()

                # Check settlement proof: tx_hash or receipt
                has_settlement_evidence = bool(tx_hash and str(tx_hash).strip())
                amt_units = usdc_to_base_units(ledger_entry.amount_paid)

                if "paid output rejected" in ls_clean:
                    if has_settlement_evidence:
                        verified_spent_units += amt_units
                        call_verified_paid_str = ledger_entry.amount_paid
                        is_settlement_verified = True
                    else:
                        uncertain_pending_units += amt_units
                        warnings.append(
                            f"Call '{c.call_id}' ({c.service_id}) recorded as paid output rejected but lacks settlement evidence. Not certified as verified spend."
                        )
                elif "paid" in ls_clean or "succeeded" in ls_clean:
                    if has_settlement_evidence:
                        verified_spent_units += amt_units
                        call_verified_paid_str = ledger_entry.amount_paid
                        is_settlement_verified = True
                    else:
                        uncertain_pending_units += amt_units
                        warnings.append(
                            f"Call '{c.call_id}' ({c.service_id}) marked as paid in ledger without verified settlement proof. Counted as pending reconciliation."
                        )
                elif "pending" in ls_clean or c.status == CallStatus.PENDING_RECONCILIATION:
                    uncertain_pending_units += usdc_to_base_units(c.listed_price_usdc)
                else:
                    # Refused or failed and not charged
                    pass
            else:
                # Missing ledger entry!
                warnings.append(
                    f"Authoritative ledger record missing for call '{c.call_id}' ({c.service_id}). Payment cannot be certified from ledger."
                )
                if c.status == CallStatus.PENDING_RECONCILIATION:
                    uncertain_pending_units += usdc_to_base_units(c.listed_price_usdc)
                tx_hash = c.transaction_hash

            # Explorer URL handling (strict no-fabrication check)
            explorer_url = self._format_explorer_url(tx_hash) if is_settlement_verified else None

            if is_settlement_verified and tx_hash:
                tx_refs.append(tx_hash)
            if explorer_url:
                explorer_links.append(explorer_url)

            # Outputs classification
            output_accepted = (c.status == CallStatus.SUCCEEDED and c.validation_status in ["valid", "accepted"])
            if output_accepted:
                accepted.append(f"{c.service_id} (Call ID: {c.call_id[:8]}): output verified against schema")
            elif c.status == CallStatus.PAID_OUTPUT_REJECTED:
                rejected.append(
                    f"{c.service_id} (Call ID: {c.call_id[:8]}): paid {call_verified_paid_str} USDC, output rejected ({c.error or 'schema mismatch'})"
                )
            elif c.error:
                rejected.append(f"{c.service_id} (Call ID: {c.call_id[:8]}): execution failed ({c.error})")

            # Call execution summary item
            call_status_str = c.status.value if hasattr(c.status, "value") else str(c.status)
            call_executions.append(CallExecutionSummary(
                call_id=c.call_id,
                step_id=c.step_id,
                service_id=c.service_id,
                category=category_str,
                status=call_status_str,
                listed_price_usdc=c.listed_price_usdc,
                verified_paid_usdc=call_verified_paid_str,
                is_settlement_verified=is_settlement_verified,
                transaction_hash=tx_hash if is_settlement_verified else None,
                explorer_url=explorer_url,
                validation_status=c.validation_status,
                output_accepted=output_accepted,
                rejection_or_failure_reason=c.error,
                is_fallback=is_fallback
            ))

            # Service selection reason using actual factors without fabricating reputation
            svc_record = self.registry.get_service(c.service_id)
            if svc_record and getattr(svc_record, "reputation", None) and svc_record.reputation.total_calls > 0:
                rep = svc_record.reputation
                rep_score = rep.reputation_score
                lat_ms = rep.median_latency_ms
                sel_reason = (
                    f"Selected for {category_str} capability matching task intent. "
                    f"Reputation: {rep_score:.1f}/100 based on {rep.total_calls} verified ledger calls; "
                    f"Median latency: {lat_ms:.0f}ms; Listed price: {c.listed_price_usdc} USDC."
                )
            else:
                rep_score = None
                lat_ms = None
                sel_reason = (
                    f"Selected for {category_str} capability matching task intent. "
                    f"Listed price: {c.listed_price_usdc} USDC; No prior reputation history in ledger."
                )

            reasons.append(ServiceSelectionReason(
                service_id=c.service_id,
                category=category_str,
                reason=sel_reason,
                listed_price_usdc=c.listed_price_usdc,
                amount_paid_usdc=call_verified_paid_str,
                reputation_score=rep_score,
                median_latency_ms=lat_ms,
                relevance=1.0
            ))

        # 3. Budget & Spending Summary Calculation (Atomic integer math)
        remaining_units = max(0, budget_units - verified_spent_units - uncertain_pending_units)
        refunded_units = remaining_units
        reserved_units = uncertain_pending_units

        spending = SpendingSummary(
            budget_allocated_usdc=base_units_to_usdc(budget_units),
            estimated_cost_usdc=base_units_to_usdc(estimated_cost_units),
            verified_spent_usdc=base_units_to_usdc(verified_spent_units),
            reserved_budget_usdc=base_units_to_usdc(reserved_units),
            uncertain_pending_usdc=base_units_to_usdc(uncertain_pending_units),
            refunded_amount_usdc=base_units_to_usdc(refunded_units),
            remaining_budget_usdc=base_units_to_usdc(remaining_units)
        )

        categories_str = ", ".join(sorted(set(r.category for r in reasons))) or "service"
        interpretation = (
            f"Buyer interpreted task as multi-step workflow requiring {categories_str} execution "
            f"within budget of {budget_usdc} USDC. "
            f"Authoritative verified expenditure: {spending.verified_spent_usdc} USDC; "
            f"Remaining available budget: {spending.remaining_budget_usdc} USDC."
        )
        if uncertain_pending_units > 0:
            interpretation += f" (Note: {spending.uncertain_pending_usdc} USDC held pending settlement reconciliation.)"

        return PurchaseExplanation(
            task_interpretation=interpretation,
            selected_services=reasons,
            call_executions=call_executions,
            outputs_accepted=accepted,
            outputs_rejected=rejected,
            fallback_attempts=fallbacks,
            spending_summary=spending,
            verified_total_spend_usdc=spending.verified_spent_usdc,
            remaining_budget_usdc=spending.remaining_budget_usdc,
            transaction_references=tx_refs,
            explorer_links=explorer_links,
            warnings=warnings
        )

