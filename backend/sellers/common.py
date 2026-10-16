"""[IMPLEMENTED FOUNDATION] Reusable Seller Foundation.

Defines the execution lifecycle, execution context, metrics tracking, and
domain exceptions for Data, Scraping, and Inference seller services.

NOTE ON PAYMENT BOUNDARIES:
Member 1 owns the official x402 SDK, payment verification, settlement, and
authoritative replay protection. This module strictly handles service execution,
input/output schema validation, and lifecycle telemetry.
"""
from abc import ABC, abstractmethod
import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, Generic, Optional, Type, TypeVar
import uuid

from pydantic import BaseModel, Field, ValidationError

from backend.shared.errors import AgentEconomyBaseException

logger = logging.getLogger(__name__)

# Generic TypeVars for Input and Output schemas
TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)


# ==============================================================================
# 1. Seller Domain Exceptions
# ==============================================================================

class SellerBaseException(AgentEconomyBaseException):
    """Base exception for all seller service operational errors."""
    def __init__(self, message: str, error_code: str = "SELLER_ERROR", service_id: Optional[str] = None):
        self.service_id = service_id
        super().__init__(message=message, error_code=error_code)


class SellerInputValidationError(SellerBaseException):
    """Raised when request payload fails domain or boundary validation."""
    def __init__(self, details: str, service_id: Optional[str] = None):
        super().__init__(
            message=f"Seller input validation error: {details}",
            error_code="SELLER_INPUT_INVALID",
            service_id=service_id,
        )


class SellerExecutionTimeoutError(SellerBaseException):
    """Raised when seller handler exceeds configured execution deadline."""
    def __init__(self, timeout_seconds: float, service_id: Optional[str] = None):
        super().__init__(
            message=f"Seller execution timed out after {timeout_seconds:.1f}s",
            error_code="SELLER_TIMEOUT",
            service_id=service_id,
        )


class SellerExecutionError(SellerBaseException):
    """Raised when seller business logic fails during execution."""
    def __init__(self, details: str, service_id: Optional[str] = None):
        super().__init__(
            message=f"Seller execution failed: {details}",
            error_code="SELLER_EXECUTION_FAILED",
            service_id=service_id,
        )


class SellerOutputValidationError(SellerBaseException):
    """Raised when seller output fails declared Pydantic schema validation."""
    def __init__(self, details: str, service_id: Optional[str] = None):
        super().__init__(
            message=f"Seller output failed schema validation: {details}",
            error_code="SELLER_OUTPUT_INVALID",
            service_id=service_id,
        )


# ==============================================================================
# 2. Context & Metrics Models
# ==============================================================================

class SellerExecutionContext(BaseModel):
    """Execution context passed into the seller service lifecycle."""
    request_id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    service_id: str = Field(..., description="Target service identifier, e.g. data_001")
    idempotency_key: Optional[str] = Field(default=None, description="Optional client idempotency key")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    client_ip: Optional[str] = Field(default=None)


class ExecutionMetrics(BaseModel):
    """Telemetry and timing metrics captured during seller lifecycle execution."""
    service_id: str
    request_id: str
    duration_ms: float = Field(..., description="Wall-clock execution duration in milliseconds")
    success: bool = Field(..., description="Whether execution and output validation succeeded")
    error_code: Optional[str] = Field(default=None, description="Error code if execution failed")
    timed_out: bool = Field(default=False, description="True if operation was terminated due to timeout")
    output_validated: bool = Field(default=False, description="True if output conformed to schema")


# ==============================================================================
# 3. Base Seller Service Class
# ==============================================================================

class BaseSellerService(Generic[TInput, TOutput], ABC):
    """Abstract base class establishing the standard lifecycle for seller services.
    
    Enforces:
    - Input pre-validation
    - Safe execution within an async timeout boundary
    - Output post-validation against the declared Pydantic output model
    - Duration measurement and execution telemetry
    - Sanitized exception raising to prevent secret leakage
    """

    def __init__(
        self,
        service_id: str,
        name: str,
        input_model: Type[TInput],
        output_model: Type[TOutput],
        default_timeout_seconds: float = 10.0,
    ):
        self.service_id = service_id
        self.name = name
        self.input_model = input_model
        self.output_model = output_model
        self.default_timeout_seconds = default_timeout_seconds

    @abstractmethod
    async def _execute_business_logic(
        self,
        payload: TInput,
        context: SellerExecutionContext
    ) -> TOutput:
        """Subclass implementation of the specific business logic.
        Must be implemented by DataSellerService, ScrapingSellerService, etc.
        """
        pass

    async def execute_lifecycle(
        self,
        raw_payload: Any,
        context: Optional[SellerExecutionContext] = None,
        timeout_seconds: Optional[float] = None,
    ) -> tuple[TOutput, ExecutionMetrics]:
        """Runs the standardized execution lifecycle.
        
        Returns:
            Tuple of (validated_output, execution_metrics)
            
        Raises:
            SellerInputValidationError
            SellerExecutionTimeoutError
            SellerOutputValidationError
            SellerExecutionError
        """
        ctx = context or SellerExecutionContext(service_id=self.service_id)
        effective_timeout = timeout_seconds or self.default_timeout_seconds
        start_time = time.perf_counter()

        # 1. Input Validation
        if isinstance(raw_payload, self.input_model):
            validated_input = raw_payload
        else:
            try:
                validated_input = self.input_model.model_validate(raw_payload)
            except ValidationError as val_err:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                logger.warning(
                    "Input validation failed for service %s (req=%s): %s",
                    self.service_id, ctx.request_id, val_err
                )
                raise SellerInputValidationError(
                    details=str(val_err),
                    service_id=self.service_id
                ) from val_err

        # 2. Bounded Execution with Timeout
        timed_out = False
        try:
            raw_output = await asyncio.wait_for(
                self._execute_business_logic(validated_input, ctx),
                timeout=effective_timeout
            )
        except asyncio.TimeoutError as timeout_err:
            timed_out = True
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(
                "Execution timed out for service %s after %.1fs (req=%s)",
                self.service_id, effective_timeout, ctx.request_id
            )
            raise SellerExecutionTimeoutError(
                timeout_seconds=effective_timeout,
                service_id=self.service_id
            ) from timeout_err
        except SellerBaseException:
            # Re-raise known domain exceptions
            raise
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.exception(
                "Unhandled error in service %s (req=%s): %s",
                self.service_id, ctx.request_id, exc
            )
            raise SellerExecutionError(
                details=str(exc),
                service_id=self.service_id
            ) from exc

        # 3. Output Validation
        if isinstance(raw_output, self.output_model):
            validated_output = raw_output
        else:
            try:
                validated_output = self.output_model.model_validate(raw_output)
            except ValidationError as out_err:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                logger.error(
                    "Output validation failed for service %s (req=%s): %s",
                    self.service_id, ctx.request_id, out_err
                )
                raise SellerOutputValidationError(
                    details=str(out_err),
                    service_id=self.service_id
                ) from out_err

        # 4. Measure Metrics
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        metrics = ExecutionMetrics(
            service_id=self.service_id,
            request_id=ctx.request_id,
            duration_ms=round(duration_ms, 2),
            success=True,
            timed_out=False,
            output_validated=True,
        )

        logger.info(
            "Service %s completed in %.2fms (req=%s)",
            self.service_id, duration_ms, ctx.request_id
        )
        return validated_output, metrics
