"""Purchase Explanation generator producing transparent audit narratives."""
from typing import List
from backend.shared.constants import base_units_to_usdc, usdc_to_base_units
from backend.buyer.schemas import (
    CallStatus,
    ServiceCallRecord,
    PurchaseExplanation,
    ServiceSelectionReason,
)


class ExplanationGenerator:
    """Generates detailed, verified purchase explanations following DI-06 standards."""

    def generate_explanation(
        self,
        task_prompt: str,
        budget_usdc: str,
        calls: List[ServiceCallRecord],
        fallbacks: List[str],
        warnings: List[str],
    ) -> PurchaseExplanation:
        budget_units = usdc_to_base_units(budget_usdc)
        total_spent_units = sum(
            usdc_to_base_units(c.amount_paid_usdc)
            for c in calls
            if c.status in [CallStatus.SUCCEEDED, CallStatus.PAID_OUTPUT_REJECTED]
        )
        remaining_units = max(0, budget_units - total_spent_units)

        selected_services = []
        outputs_accepted = []
        outputs_rejected = []
        tx_references = []

        for c in calls:
            reason_text = f"Selected for {c.category.value} capabilities"
            selected_services.append(ServiceSelectionReason(
                service_id=c.service_id,
                category=c.category.value,
                reason=reason_text,
                listed_price_usdc=c.listed_price_usdc,
                amount_paid_usdc=c.amount_paid_usdc,
            ))

            if c.status == CallStatus.SUCCEEDED:
                outputs_accepted.append(f"{c.service_id} (Call ID: {c.call_id[:8]}) accepted.")
            elif c.status == CallStatus.PAID_OUTPUT_REJECTED:
                outputs_rejected.append(
                    f"{c.service_id} (Call ID: {c.call_id[:8]}) paid but rejected: {c.error or 'Invalid schema'}"
                )

            if c.transaction_hash:
                tx_references.append(f"Base Sepolia: {c.transaction_hash}")

        # Meaningful interpretation
        interpretation = (
            f"Buyer interpreted task as multi-stage workflow requiring "
            f"{', '.join(sorted({c.category.value for c in calls}))} execution within {budget_usdc} USDC."
        )

        return PurchaseExplanation(
            task_interpretation=interpretation,
            selected_services=selected_services,
            outputs_accepted=outputs_accepted,
            outputs_rejected=outputs_rejected,
            fallback_attempts=fallbacks,
            verified_total_spend_usdc=base_units_to_usdc(total_spent_units),
            remaining_budget_usdc=base_units_to_usdc(remaining_units),
            transaction_references=tx_references,
            warnings=warnings
        )
