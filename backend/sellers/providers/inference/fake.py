"""[IMPLEMENTED] Deterministic Offline Inference Provider for Testing & Demo."""
from typing import Dict, Any
from backend.sellers.providers.interfaces import InferenceProviderInterface


class FakeInferenceProvider(InferenceProviderInterface):
    """Deterministic offline AI inference provider."""

    def __init__(self, model_name: str = "agent-economy-reasoner-v1"):
        self.model_name = model_name

    async def generate(self, prompt: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        words = prompt.split()
        estimated_prompt_tokens = len(words)
        
        # Formulate deterministic reasoning summary
        clean_prompt = prompt.strip().replace("\n", " ")
        prompt_snippet = clean_prompt[:80] + ("..." if len(clean_prompt) > 80 else "")
        summary = (
            f"Analytical Synthesis: Based on prompt '{prompt_snippet}', "
            "the system identified high-signal convergence towards autonomous microservice settlements."
        )
        
        # Bound output length by max_tokens
        char_limit = max_tokens * 4
        if len(summary) > char_limit:
            summary = summary[:char_limit]

        tokens_generated = min(len(summary.split()), max_tokens)
        tokens_used = min(estimated_prompt_tokens + tokens_generated, max_tokens)

        return {
            "response": summary,
            "result": summary,
            "model_used": self.model_name,
            "model": self.model_name,
            "tokens_generated": tokens_generated,
            "tokens_used": tokens_used,
        }
