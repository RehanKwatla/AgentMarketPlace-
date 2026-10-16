"""FastAPI Router for the Buyer Agent Subsystem."""
from fastapi import APIRouter, Header, HTTPException, Query, status
from fastapi.responses import JSONResponse
from backend.buyer.schemas import (
    TaskCreationRequest,
    TaskCreationResponse,
    TaskDetailResponse,
    TaskCallsResponse,
)
from backend.buyer.service import buyer_service

router = APIRouter(prefix="/api/v1", tags=["Buyer Agent"])


@router.post(
    "/tasks",
    response_model=TaskCreationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Buyer Task with Spending Budget",
    description="Accept natural language task and explicit budget; validates plan and executes paid microservices."
)
async def create_task(
    request: TaskCreationRequest,
    idempotency_key: str = Header(None, alias="Idempotency-Key")
):
    task_record = await buyer_service.submit_and_execute_task(request)

    response_data = TaskCreationResponse(
        task_id=task_record.task_id,
        status=task_record.status,
        budget_usdc=task_record.budget_usdc,
        reserved_usdc=task_record.reserved_usdc,
        spent_usdc=task_record.spent_usdc,
        max_concurrency=task_record.max_concurrency,
        created_at=task_record.created_at,
        status_url=f"/api/v1/tasks/{task_record.task_id}"
    )

    return JSONResponse(status_code=status.HTTP_201_CREATED, content=response_data.model_dump())


# Backward compatibility route for /api/v1/buyer/tasks
@router.post(
    "/buyer/tasks",
    status_code=status.HTTP_200_OK,
    summary="Legacy Buyer Task Submission"
)
async def create_buyer_task_legacy(request: TaskCreationRequest):
    task_record = await buyer_service.submit_and_execute_task(request)
    
    # Map to legacy TaskResponse format for existing callers
    legacy_executions = [
        {
            "step": idx + 1,
            "service_id": c.service_id,
            "request_id": c.call_id,
            "price_paid_usdc": c.amount_paid_usdc,
            "tx_hash": c.transaction_hash,
            "status": "paid" if c.status.value == "succeeded" else c.status.value,
            "latency_ms": c.latency_ms,
            "output": c.output,
            "error": c.error
        }
        for idx, c in enumerate(task_record.calls)
    ]
    
    if str(task_record.status.value) == "refused" or str(task_record.status) == "refused":
        final_text = "Task refused: Insufficient budget allocated."
    elif task_record.result and task_record.result.get("summary"):
        final_text = task_record.result["summary"]
    else:
        final_text = "Task completed."
    
    legacy_payload = {
        "task_id": task_record.task_id,
        "status": task_record.status.value,
        "budget_allocated_usdc": task_record.budget_usdc,
        "total_cost_usdc": task_record.spent_usdc,
        "cost_explanation": task_record.explanation.task_interpretation if task_record.explanation else "",
        "selected_services": [c.service_id for c in task_record.calls],
        "executions": legacy_executions,
        "final_result": final_text,
        "errors_and_fallbacks": task_record.explanation.warnings if task_record.explanation else []
    }
    return JSONResponse(status_code=status.HTTP_200_OK, content=legacy_payload)


@router.get(
    "/tasks/{task_id}",
    response_model=TaskDetailResponse,
    summary="Get Task Status and Details",
    description="Retrieve live progress, budget spend, service calls, and explanation for a task."
)
async def get_task_status(task_id: str):
    task = buyer_service.get_task(task_id)
    if not task:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Task with ID '{task_id}' was not found.",
                    "details": {"task_id": task_id}
                }
            }
        )
    return JSONResponse(status_code=status.HTTP_200_OK, content=task.model_dump())


@router.get(
    "/tasks/{task_id}/result",
    summary="Get Final Task Result and Purchase Explanation",
    description="Retrieve combined synthesized output and verified purchase explanation with provenance."
)
async def get_task_result(task_id: str):
    task = buyer_service.get_task(task_id)
    if not task:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Task with ID '{task_id}' was not found.",
                    "details": {"task_id": task_id}
                }
            }
        )

    final_summary = ""
    if task.result and isinstance(task.result, dict):
        final_summary = task.result.get("summary", "")
    cost_explanation = task.explanation.task_interpretation if task.explanation else ""

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "task_id": task.task_id,
            "status": task.status.value if hasattr(task.status, "value") else str(task.status),
            "result": task.result,
            "final_result": final_summary or str(task.result),
            "explanation": task.explanation.model_dump() if task.explanation else None,
            "cost_explanation": cost_explanation,
            "spent_usdc": task.spent_usdc,
            "remaining_usdc": task.remaining_usdc
        }
    )


@router.get(
    "/tasks/{task_id}/calls",
    response_model=TaskCallsResponse,
    summary="Get Service Calls for Task",
    description="List all attempted and executed microservice calls for a task with latency and verification status."
)
async def get_task_calls(task_id: str):
    calls = buyer_service.get_task_calls(task_id)
    if calls is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Task with ID '{task_id}' was not found.",
                    "details": {"task_id": task_id}
                }
            }
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=TaskCallsResponse(task_id=task_id, items=calls).model_dump()
    )
