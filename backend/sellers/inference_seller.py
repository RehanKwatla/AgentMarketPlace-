"""[IMPLEMENTED] Inference Seller Agent with Injected Provider Adapter."""
from typing import Optional

from backend.sellers.common import (
    BaseSellerService,
    SellerExecutionContext,
    SellerExecutionError,
    SellerExecutionTimeoutError,
    SellerInputValidationError,
)
from backend.sellers.schemas import InferenceSellerInput, InferenceSellerOutput
from backend.sellers.providers.interfaces import InferenceProviderInterface
from backend.sellers.providers.inference.fake import FakeInferenceProvider
from backend.sellers.providers.errors import ProviderBaseError


class InferenceSellerService(BaseSellerService[InferenceSellerInput, InferenceSellerOutput]):
    """Provides LLM-based reasoning, summarization, and data synthesis."""

    def __init__(
        self,
        service_id: str = "inference_001",
        provider: Optional[InferenceProviderInterface] = None,
        default_timeout_seconds: float = 15.0,
    ):
        super().__init__(
            service_id=service_id,
            name="Agent Synthesis & Inference Engine",
            input_model=InferenceSellerInput,
            output_model=InferenceSellerOutput,
            default_timeout_seconds=default_timeout_seconds,
        )
        self.provider = provider or FakeInferenceProvider()

    async def _execute_business_logic(
        self,
        payload: InferenceSellerInput,
        context: SellerExecutionContext
    ) -> InferenceSellerOutput:
        """Synthesize response from input prompt via injected provider adapter."""
        try:
            result = await self.provider.generate(
                prompt=payload.prompt,
                max_tokens=payload.max_tokens,
                temperature=payload.temperature,
            )
        except ProviderBaseError as prov_err:
            if prov_err.status_code == 400:
                raise SellerInputValidationError(details=prov_err.message, service_id=self.service_id)
            if prov_err.status_code == 504:
                raise SellerExecutionTimeoutError(timeout_seconds=self.default_timeout_seconds, service_id=self.service_id)
            raise SellerExecutionError(details=prov_err.message, service_id=self.service_id)
        except Exception as exc:
            raise SellerExecutionError(details=f"Inference provider failure: {exc}", service_id=self.service_id)

        response_text = result.get("response") or result.get("result", "")
        # Bounded response safeguarding
        words = response_text.split()
        bounded_words = words[: payload.max_tokens]
        bounded_response = " ".join(bounded_words) if len(words) > payload.max_tokens else response_text

        model_name = result.get("model_used") or result.get("model", "mock-reasoner-v1")
        tokens_generated = result.get("tokens_generated") or len(bounded_response.split())

        return InferenceSellerOutput(
            response=bounded_response,
            model_used=model_name,
            tokens_generated=tokens_generated,
        )

    async def execute(self, payload: InferenceSellerInput) -> InferenceSellerOutput:
        """Backward-compatible direct execution method for existing routes & tests."""
        output, _ = await self.execute_lifecycle(payload)
        return output
