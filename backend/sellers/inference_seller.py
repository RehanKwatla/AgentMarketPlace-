"""[IMPLEMENTED FOUNDATION] Inference Seller Agent inheriting from BaseSellerService."""
from typing import Optional

from backend.sellers.common import BaseSellerService, SellerExecutionContext
from backend.sellers.schemas import InferenceSellerInput, InferenceSellerOutput


class InferenceSellerService(BaseSellerService[InferenceSellerInput, InferenceSellerOutput]):
    """Provides LLM-based reasoning, summarization, and data synthesis."""

    def __init__(self, service_id: str = "inference_001"):
        super().__init__(
            service_id=service_id,
            name="Agent Synthesis & Inference Engine",
            input_model=InferenceSellerInput,
            output_model=InferenceSellerOutput,
            default_timeout_seconds=8.0,
        )

    async def _execute_business_logic(
        self,
        payload: InferenceSellerInput,
        context: SellerExecutionContext
    ) -> InferenceSellerOutput:
        """Synthesize response from input prompt.
        NOTE: Deterministic baseline reasoning for testing.
        Live LLM provider adapter and fallback wired in Phase 4.
        """
        prompt_snippet = payload.prompt[:80] + ("..." if len(payload.prompt) > 80 else "")
        response_text = (
            f"Analytical Synthesis: Based on prompt '{prompt_snippet}', "
            "the system identified high-signal convergence towards autonomous microservice settlements."
        )
        words = response_text.split()
        bounded_words = words[: payload.max_tokens]
        bounded_response = " ".join(bounded_words)
        return InferenceSellerOutput(
            response=bounded_response,
            model_used="agent-economy-reasoner-v1",
            tokens_generated=len(bounded_words)
        )

    async def execute(self, payload: InferenceSellerInput) -> InferenceSellerOutput:
        """Backward-compatible direct execution method for existing routes & tests."""
        output, _ = await self.execute_lifecycle(payload)
        return output

