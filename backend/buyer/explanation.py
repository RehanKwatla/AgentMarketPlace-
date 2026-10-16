"""Purchase Explanation Generator providing transparent spending narratives."""
from typing import List, Optional
from backend.shared.constants import base_units_to_usdc, usdc_to_base_units
from backend.buyer.schemas import (
    CallStatus,
    PurchaseExplanation,
    ServiceCallRecord,
    ServiceSelectionReason,
)


class ExplanationGenerator:
    """Produces structured narratives explaining service selection, validation, and spending."""

    def generate_explanation(
        self,
        task_prompt: str,
        budget_usdc: str,
        calls: List[ServiceCallRecord],
        fallbacks: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ) -> PurchaseExplanation:
        """Construct full PurchaseExplanation."""
        fallbacks = fallbacks or []
        warnings = warnings or []

        reasons: List[ServiceSelectionReason] = []
        accepted: List[str] = []
        rejected: List[str] = []
        tx_refs: List[str] = []
        total_spent_units = 0

        for c in calls:
            spent_units = usdc_to_base_units(c.amount_paid_usdc)
            total_spent_units += spent_units

            reasons.append(ServiceSelectionReason(
                service_id=c.service_id,
                category=c.category.value if hasattr(c.category, "value") else str(c.category),
                reason=f"Selected for {c.category.value if hasattr(c.category, 'value') else str(c.category)} capabilities matching task intent.",
                listed_price_usdc=c.listed_price_usdc,
                amount_paid_usdc=c.amount_paid_usdc
            ))

            if c.status == CallStatus.SUCCEEDED:
                accepted.append(f"{c.service_id} (Call ID: {c.call_id[:8]}) accepted.")
            elif c.status == CallStatus.PAID_OUTPUT_REJECTED:
                rejected.append(f"{c.service_id} (Call ID: {c.call_id[:8]}) settled payment but output rejected: {c.error}")

            if c.transaction_hash:
                tx_refs.append(c.transaction_hash)

        budget_units = usdc_to_base_units(budget_usdc)
        remaining_units = max(0, budget_units - total_spent_units)

        interpretation = (
            f"Buyer interpreted task as multi-stage workflow requiring "
            f"{', '.join(sorted(set(r.category for r in reasons)) or ['service'])} execution "
            f"within {budget_usdc} USDC."
        )

        return PurchaseExplanation(
            task_interpretation=interpretation,
            selected_services=reasons,
            outputs_accepted=accepted,
            outputs_rejected=rejected,
            fallback_attempts=fallbacks,
            verified_total_spend_usdc=base_units_to_usdc(total_spent_units),
            remaining_budget_usdc=base_units_to_usdc(remaining_units),
            transaction_references=tx_refs,
            warnings=warnings
        )
