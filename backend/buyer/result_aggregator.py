"""[IMPLEMENTED FOUNDATION] Result Aggregation & Cost Explanation."""
from typing import List
from backend.shared.constants import base_units_to_usdc, usdc_to_base_units
from backend.shared.schemas import ExecutionStep, TaskResponse


class ResultAggregator:
    """Combines outputs from executed seller microservices into a coherent synthesis."""

    def aggregate(
        self,
        task_id: str,
        budget_allocated_usdc: str,
        executions: List[ExecutionStep],
        fallbacks: List[str]
    ) -> TaskResponse:
        total_spent_units = sum(
            usdc_to_base_units(step.price_paid_usdc)
            for step in executions
            if step.status.value in ["paid", "paid output rejected"]
        )

        cost_parts = [
            f"Step {s.step} ({s.service_id}): {s.price_paid_usdc} USDC"
            for s in executions
        ]
        cost_explanation = ", ".join(cost_parts) if cost_parts else "No services executed."

        # Synthesize final result
        outputs = []
        for s in executions:
            if s.output:
                if "response" in s.output:
                    outputs.append(str(s.output["response"]))
                elif "content" in s.output:
                    outputs.append(f"Scraped Content: {s.output['content'][:120]}...")
                elif "price" in s.output:
                    outputs.append(f"Asset Price: {s.output.get('symbol')} = ${s.output.get('price')}")

        final_text = " | ".join(outputs) if outputs else "No data produced."

        return TaskResponse(
            task_id=task_id,
            status="completed" if executions else "failed",
            budget_allocated_usdc=budget_allocated_usdc,
            total_cost_usdc=base_units_to_usdc(total_spent_units),
            cost_explanation=cost_explanation,
            selected_services=[s.service_id for s in executions],
            executions=executions,
            final_result=final_text,
            errors_and_fallbacks=fallbacks
        )
