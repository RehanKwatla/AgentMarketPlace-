"""Unit tests for Phase 1 Step 1 Shared Seller Foundation."""
import asyncio
import pytest
from pydantic import BaseModel, Field

from backend.sellers.common import (
    BaseSellerService,
    SellerExecutionContext,
    ExecutionMetrics,
    SellerInputValidationError,
    SellerExecutionTimeoutError,
    SellerExecutionError,
    SellerOutputValidationError,
)


# Test Schemas
class MockInput(BaseModel):
    query: str = Field(..., min_length=2)
    max_count: int = Field(default=10, ge=1)


class MockOutput(BaseModel):
    result: str
    item_count: int


# Test Service Implementations
class HealthyMockService(BaseSellerService[MockInput, MockOutput]):
    def __init__(self):
        super().__init__(
            service_id="mock_001",
            name="Healthy Mock Service",
            input_model=MockInput,
            output_model=MockOutput,
            default_timeout_seconds=1.0,
        )

    async def _execute_business_logic(
        self, payload: MockInput, context: SellerExecutionContext
    ) -> MockOutput:
        return MockOutput(
            result=f"processed_{payload.query}",
            item_count=payload.max_count,
        )


class TimeoutMockService(BaseSellerService[MockInput, MockOutput]):
    def __init__(self):
        super().__init__(
            service_id="timeout_001",
            name="Timeout Mock Service",
            input_model=MockInput,
            output_model=MockOutput,
            default_timeout_seconds=0.1,
        )

    async def _execute_business_logic(
        self, payload: MockInput, context: SellerExecutionContext
    ) -> MockOutput:
        # Sleep longer than the 0.1s timeout
        await asyncio.sleep(0.3)
        return MockOutput(result="too_late", item_count=1)


class InvalidOutputMockService(BaseSellerService[MockInput, MockOutput]):
    def __init__(self):
        super().__init__(
            service_id="invalid_out_001",
            name="Invalid Output Mock Service",
            input_model=MockInput,
            output_model=MockOutput,
            default_timeout_seconds=1.0,
        )

    async def _execute_business_logic(
        self, payload: MockInput, context: SellerExecutionContext
    ) -> dict:
        # Return missing required field "item_count"
        return {"result": "incomplete"}


class CrashingMockService(BaseSellerService[MockInput, MockOutput]):
    def __init__(self):
        super().__init__(
            service_id="crash_001",
            name="Crashing Mock Service",
            input_model=MockInput,
            output_model=MockOutput,
            default_timeout_seconds=1.0,
        )

    async def _execute_business_logic(
        self, payload: MockInput, context: SellerExecutionContext
    ) -> MockOutput:
        raise ValueError("Simulated unexpected downstream crash")


# Tests
@pytest.mark.asyncio
async def test_seller_lifecycle_success():
    service = HealthyMockService()
    ctx = SellerExecutionContext(service_id="mock_001", idempotency_key="key_123")
    output, metrics = await service.execute_lifecycle(
        {"query": "bitcoin", "max_count": 5}, context=ctx
    )

    assert isinstance(output, MockOutput)
    assert output.result == "processed_bitcoin"
    assert output.item_count == 5

    assert isinstance(metrics, ExecutionMetrics)
    assert metrics.success is True
    assert metrics.timed_out is False
    assert metrics.output_validated is True
    assert metrics.duration_ms > 0
    assert metrics.request_id == ctx.request_id


@pytest.mark.asyncio
async def test_seller_lifecycle_input_validation_error():
    service = HealthyMockService()
    # Missing required query field
    with pytest.raises(SellerInputValidationError) as exc_info:
        await service.execute_lifecycle({"max_count": 5})

    assert exc_info.value.service_id == "mock_001"
    assert exc_info.value.error_code == "SELLER_INPUT_INVALID"


@pytest.mark.asyncio
async def test_seller_lifecycle_timeout_error():
    service = TimeoutMockService()
    with pytest.raises(SellerExecutionTimeoutError) as exc_info:
        await service.execute_lifecycle({"query": "fast", "max_count": 1})

    assert exc_info.value.service_id == "timeout_001"
    assert exc_info.value.error_code == "SELLER_TIMEOUT"


@pytest.mark.asyncio
async def test_seller_lifecycle_output_validation_error():
    service = InvalidOutputMockService()
    with pytest.raises(SellerOutputValidationError) as exc_info:
        await service.execute_lifecycle({"query": "valid_query", "max_count": 2})

    assert exc_info.value.service_id == "invalid_out_001"
    assert exc_info.value.error_code == "SELLER_OUTPUT_INVALID"


@pytest.mark.asyncio
async def test_seller_lifecycle_crash_handling():
    service = CrashingMockService()
    with pytest.raises(SellerExecutionError) as exc_info:
        await service.execute_lifecycle({"query": "valid_query", "max_count": 2})

    assert exc_info.value.service_id == "crash_001"
    assert exc_info.value.error_code == "SELLER_EXECUTION_FAILED"
    assert "Simulated unexpected downstream crash" in str(exc_info.value)


# ==============================================================================
# Dependency Provider Tests (Phase 1, Step 2)
# ==============================================================================

def test_seller_dependencies_instantiation():
    """Verify dependencies construct expected service instances with correct IDs."""
    from backend.sellers.dependencies import (
        get_data_seller_service,
        get_scraping_seller_service,
        get_inference_seller_service,
    )

    data_svc = get_data_seller_service()
    assert data_svc.service_id == "data_001"

    scraping_svc = get_scraping_seller_service()
    assert scraping_svc.service_id == "scraping_001"

    inference_svc = get_inference_seller_service()
    assert inference_svc.service_id == "inference_001"


def test_seller_execution_context_extractor():
    """Verify context extractor parses request path and idempotency header."""
    from unittest.mock import MagicMock
    from backend.sellers.dependencies import get_seller_execution_context

    mock_request = MagicMock()
    mock_request.url.path = "/api/v1/seller/data"
    mock_request.client.host = "192.168.1.100"

    ctx = get_seller_execution_context(
        request=mock_request,
        idempotency_key="idemp_abc123"
    )

    assert ctx.service_id == "data_001"
    assert ctx.idempotency_key == "idemp_abc123"
    assert ctx.client_ip == "192.168.1.100"
    assert ctx.request_id.startswith("req_")


# ==============================================================================
# Refactored Seller Inheritance Tests (Phase 1, Step 3)
# ==============================================================================

@pytest.mark.asyncio
async def test_data_seller_inheritance_and_lifecycle():
    from backend.sellers.data_seller import DataSellerService
    from backend.sellers.common import BaseSellerService
    from backend.sellers.schemas import DataSellerInput, DataSellerOutput

    service = DataSellerService()
    assert isinstance(service, BaseSellerService)
    assert service.service_id == "data_001"
    assert service.input_model == DataSellerInput
    assert service.output_model == DataSellerOutput

    # Test execution via execute() backward-compatibility wrapper
    res = await service.execute(DataSellerInput(symbol="BTC"))
    assert res.symbol == "BTC"
    assert res.price == 67500.00

    # Test execution via lifecycle
    out, metrics = await service.execute_lifecycle({"symbol": "ETH"})
    assert out.symbol == "ETH"
    assert out.price == 2650.50
    assert metrics.success is True
    assert metrics.duration_ms > 0


@pytest.mark.asyncio
async def test_scraping_seller_inheritance_and_lifecycle():
    from backend.sellers.scraping_seller import ScrapingSellerService
    from backend.sellers.common import BaseSellerService
    from backend.sellers.schemas import ScrapingSellerInput, ScrapingSellerOutput

    service = ScrapingSellerService()
    assert isinstance(service, BaseSellerService)
    assert service.service_id == "scraping_001"
    assert service.input_model == ScrapingSellerInput
    assert service.output_model == ScrapingSellerOutput

    res = await service.execute(ScrapingSellerInput(url="https://base.org"))
    assert res.url == "https://base.org"
    assert "Extracted content" in res.content

    out, metrics = await service.execute_lifecycle({"url": "https://ethereum.org"})
    assert out.url == "https://ethereum.org"
    assert metrics.success is True


@pytest.mark.asyncio
async def test_inference_seller_inheritance_and_lifecycle():
    from backend.sellers.inference_seller import InferenceSellerService
    from backend.sellers.common import BaseSellerService
    from backend.sellers.schemas import InferenceSellerInput, InferenceSellerOutput

    service = InferenceSellerService()
    assert isinstance(service, BaseSellerService)
    assert service.service_id == "inference_001"
    assert service.input_model == InferenceSellerInput
    assert service.output_model == InferenceSellerOutput

    res = await service.execute(InferenceSellerInput(prompt="Analyze gas trends", max_tokens=50))
    assert "Analytical Synthesis" in res.response
    assert res.model_used == "agent-economy-reasoner-v1"

    out, metrics = await service.execute_lifecycle({"prompt": "Summarize market state", "max_tokens": 100})
    assert "Analytical Synthesis" in out.response
    assert metrics.success is True


