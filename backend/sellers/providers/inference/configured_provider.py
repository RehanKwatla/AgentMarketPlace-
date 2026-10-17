"""[IMPLEMENTED] Configured Upstream LLM / Inference Provider Adapter (Gemini & Groq)."""
import logging
import os
from typing import Dict, Any, Optional
import httpx

from backend.sellers.providers.interfaces import InferenceProviderInterface
from backend.sellers.providers.config import (
    ProviderSettings,
    ProviderMode,
    InferenceProviderType,
    get_provider_settings,
)
from backend.sellers.providers.errors import (
    ProviderConfigurationError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderUpstreamError,
    ProviderRequestRejectedError,
    ProviderResponseInvalidError,
    ProviderOutputLimitExceededError,
)
from backend.sellers.providers.inference.fake import FakeInferenceProvider

logger = logging.getLogger(__name__)


class ConfiguredInferenceProvider(InferenceProviderInterface):
    """External provider adapter supporting Google Gemini, Groq, and OpenAI LLM backends."""

    def __init__(
        self,
        settings: Optional[ProviderSettings] = None,
        client: Optional[httpx.AsyncClient] = None,
        fallback_fake: Optional[FakeInferenceProvider] = None,
    ):
        self.settings = settings or get_provider_settings()
        self._client = client
        self._fake = fallback_fake or FakeInferenceProvider()

    async def generate(self, prompt: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Generate text in LIVE mode via external API, or in FAKE mode via deterministic engine."""
        if self.settings.mode == ProviderMode.FAKE:
            return await self._fake.generate(prompt, max_tokens, temperature)

        # LIVE MODE: Route according to configured inference provider
        provider_type = self.settings.inference_provider

        if provider_type == InferenceProviderType.GEMINI:
            return await self._generate_gemini(prompt, max_tokens, temperature)
        elif provider_type == InferenceProviderType.GROQ:
            return await self._generate_groq(prompt, max_tokens, temperature)
        else:
            return await self._generate_openai_compatible(prompt, max_tokens, temperature)

    async def _generate_gemini(self, prompt: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Call Google Gemini generateContent REST endpoint using header-based authentication."""
        api_key = self.settings.gemini_api_key
        if not api_key or not api_key.strip():
            raise ProviderConfigurationError(
                "Live Gemini inference provider requires GEMINI_API_KEY (or requires GROQ_API_KEY if using Groq).",
                provider_name="gemini_inference_provider",
            )

        model = self.settings.gemini_model or "gemini-2.5-flash"
        api_url = (
            self.settings.inference_provider_url
            or f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        )

        headers = {
            "x-goog-api-key": api_key.strip(),
            "Content-Type": "application/json",
            "User-Agent": "AgenticaInference/2.0 (Gemini)",
        }

        generation_config: Dict[str, Any] = {
            "maxOutputTokens": min(max_tokens, self.settings.inference_max_tokens),
            "temperature": max(0.0, min(1.0, temperature)),
        }
        if "flash" in model.lower():
            generation_config["thinkingConfig"] = {"thinkingBudget": 0}

        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": generation_config,
        }

        timeout = httpx.Timeout(self.settings.inference_timeout_seconds, connect=5.0)

        try:
            if self._client is not None:
                res = await self._client.post(api_url, json=body, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    res = await client.post(api_url, json=body, headers=headers)
        except httpx.ConnectTimeout as exc:
            raise ProviderTimeoutError(f"Connection to Gemini API timed out: {exc}", provider_name="gemini_inference_provider")
        except httpx.ReadTimeout as exc:
            raise ProviderTimeoutError(f"Gemini API response timed out: {exc}", provider_name="gemini_inference_provider")
        except httpx.RequestError as exc:
            raise ProviderUpstreamError(f"Gemini API request failed: {exc}", provider_name="gemini_inference_provider")

        self._check_status_code(res, "gemini_inference_provider")

        try:
            payload = res.json()
        except Exception:
            raise ProviderResponseInvalidError("Gemini API returned non-JSON response.", provider_name="gemini_inference_provider")

        candidates = payload.get("candidates")
        if not candidates or not isinstance(candidates, list):
            raise ProviderResponseInvalidError("Gemini API response missing candidates.", provider_name="gemini_inference_provider")

        first_candidate = candidates[0]
        content_obj = first_candidate.get("content", {})
        parts = content_obj.get("parts", [])
        if not parts or not isinstance(parts, list):
            raise ProviderResponseInvalidError("Gemini API candidate missing content parts.", provider_name="gemini_inference_provider")

        content = parts[0].get("text", "").strip()
        if not content:
            raise ProviderResponseInvalidError("Gemini API returned empty text.", provider_name="gemini_inference_provider")

        # Bounded response length
        if len(content) > 50_000:
            content = content[:50_000]

        usage = payload.get("usageMetadata", {})
        tokens_generated = usage.get("candidatesTokenCount", len(content.split()))
        tokens_used = usage.get("totalTokenCount", tokens_generated)

        return {
            "response": content,
            "result": content,
            "model_used": payload.get("modelVersion", model),
            "model": payload.get("modelVersion", model),
            "tokens_generated": tokens_generated,
            "tokens_used": tokens_used,
        }

    async def _generate_groq(self, prompt: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Call Groq Cloud chat completions REST API using OpenAI-compatible format."""
        api_key = self.settings.groq_api_key or self.settings.inference_provider_api_key
        if not api_key or not api_key.strip():
            raise ProviderConfigurationError(
                "Live Groq inference provider requires GROQ_API_KEY.",
                provider_name="groq_inference_provider",
            )

        model = self.settings.groq_model or "llama-3.3-70b-versatile"
        api_url = self.settings.inference_provider_url or "https://api.groq.com/openai/v1/chat/completions"

        return await self._post_openai_format(
            api_url=api_url,
            api_key=api_key,
            model=model,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            provider_name="groq_inference_provider",
        )

    async def _generate_openai_compatible(self, prompt: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Fallback adapter for generic OpenAI-compatible chat completion endpoints."""
        api_key = (
            self.settings.openai_api_key
            or self.settings.groq_api_key
            or self.settings.inference_provider_api_key
        )
        if not api_key or not api_key.strip():
            raise ProviderConfigurationError(
                "Live inference provider requires GROQ_API_KEY, OPENAI_API_KEY, or INFERENCE_PROVIDER_API_KEY.",
                provider_name="configured_inference_provider",
            )

        model = self.settings.inference_default_model or "gpt-4o-mini"
        api_url = self.settings.inference_provider_url or "https://api.openai.com/v1/chat/completions"

        return await self._post_openai_format(
            api_url=api_url,
            api_key=api_key,
            model=model,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            provider_name="configured_inference_provider",
        )

    async def _post_openai_format(
        self,
        api_url: str,
        api_key: str,
        model: str,
        prompt: str,
        max_tokens: int,
        temperature: float,
        provider_name: str,
    ) -> Dict[str, Any]:
        """Shared implementation for OpenAI-compatible chat completion endpoints."""
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
            "User-Agent": f"AgenticaInference/2.0 ({provider_name})",
        }

        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a concise, helpful analytical agent."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": min(max_tokens, self.settings.inference_max_tokens),
            "temperature": max(0.0, min(1.0, temperature)),
        }

        timeout = httpx.Timeout(self.settings.inference_timeout_seconds, connect=5.0)

        try:
            if self._client is not None:
                res = await self._client.post(api_url, json=body, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    res = await client.post(api_url, json=body, headers=headers)
        except httpx.ConnectTimeout as exc:
            raise ProviderTimeoutError(f"Connection to inference provider timed out: {exc}", provider_name=provider_name)
        except httpx.ReadTimeout as exc:
            raise ProviderTimeoutError(f"Inference provider response timed out: {exc}", provider_name=provider_name)
        except httpx.RequestError as exc:
            raise ProviderUpstreamError(f"Inference network request failed: {exc}", provider_name=provider_name)

        self._check_status_code(res, provider_name)

        try:
            payload = res.json()
        except Exception:
            raise ProviderResponseInvalidError(
                "Inference provider returned non-JSON response.",
                provider_name=provider_name,
            )

        choices = payload.get("choices")
        if not choices or not isinstance(choices, list):
            raise ProviderResponseInvalidError(
                "Inference provider response missing valid choices.",
                provider_name=provider_name,
            )

        first_choice = choices[0]
        message = first_choice.get("message", {})
        content = message.get("content", "").strip()

        if not content:
            raise ProviderResponseInvalidError(
                "Inference provider returned empty content.",
                provider_name=provider_name,
            )

        if len(content) > 50_000:
            content = content[:50_000]

        usage = payload.get("usage", {})
        tokens_generated = usage.get("completion_tokens", len(content.split()))
        tokens_used = usage.get("total_tokens", tokens_generated)

        return {
            "response": content,
            "result": content,
            "model_used": payload.get("model", model),
            "model": payload.get("model", model),
            "tokens_generated": tokens_generated,
            "tokens_used": tokens_used,
        }

    def _check_status_code(self, res: httpx.Response, provider_name: str) -> None:
        """Validate HTTP response status code and raise appropriate normalized provider error."""
        if res.status_code == 429:
            retry_after = None
            if "Retry-After" in res.headers:
                try:
                    retry_after = float(res.headers["Retry-After"])
                except ValueError:
                    pass
            raise ProviderRateLimitError(
                f"{provider_name} rate limit exceeded.",
                provider_name=provider_name,
                retry_after_seconds=retry_after,
            )
        if res.status_code >= 500:
            raise ProviderUpstreamError(
                f"{provider_name} returned HTTP {res.status_code}.",
                provider_name=provider_name,
            )
        if res.status_code >= 400:
            raise ProviderRequestRejectedError(
                f"{provider_name} rejected request with HTTP {res.status_code}.",
                provider_name=provider_name,
            )
