"""Buyer Subsystem FastAPI Router implementing canonical Task APIs."""
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from backend.buyer.schemas import (
    TaskCallsResponse,
    TaskCreationRequest,
    TaskDetailResponse,
    TaskResultResponse,
)
from backend.buyer.service import buyer_service

router = APIRouter(tags=["Buyer Tasks"])


@router.post(
    "/api/v1/tasks",
    response_model=TaskDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit and Create Autonomous Buyer Task",
    description="Validate natural language prompt and budget, persist task session, and orchestrate execution."
)
async def create_task(request: TaskCreationRequest):
    """Create task record in 'accepted' state, persist it, and execute planned workflow."""
    task_response = await buyer_service.submit_and_execute_task(request)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=task_response.model_dump())


# Legacy endpoint for backward compatibility with earlier tests
@router.post(
    "/api/v1/buyer/tasks",
    status_code=status.HTTP_200_OK,
    summary="Legacy Buyer Task Submission Endpoint",
    description="Maintains backward compatibility for /api/v1/buyer/tasks callers."
)
async def legacy_create_task(request: TaskCreationRequest):
    task_record = await buyer_service.submit_and_execute_task(request)

    legacy_executions = []
    for step_idx, call in enumerate(task_record.calls, start=1):
        legacy_executions.append({
            "step": step_idx,
            "service_id": call.service_id,
            "request_id": f"req_{call.call_id[:8]}",
            "price_paid_usdc": call.amount_paid_usdc,
            "tx_hash": call.transaction_hash,
            "status": call.status.value if hasattr(call.status, "value") else str(call.status),
            "latency_ms": call.latency_ms,
            "output": call.output,
            "error": call.error
        })

    final_text = task_record.final_result or ""
    if not final_text and task_record.result and isinstance(task_record.result, dict):
        final_text = task_record.result.get("summary", "")
    if not final_text and task_record.status == "refused":
        final_text = f"Task refused: Insufficient budget allocated."

    legacy_payload = {
        "task_id": task_record.task_id,
        "status": task_record.status,
        "budget_allocated_usdc": task_record.budget_usdc,
        "total_cost_usdc": task_record.spent_usdc,
        "cost_explanation": task_record.cost_explanation or "",
        "selected_services": [c.service_id for c in task_record.calls],
        "executions": legacy_executions,
        "final_result": final_text or str(task_record.result or ""),
        "errors_and_fallbacks": task_record.explanation.warnings if task_record.explanation else []
    }
    return JSONResponse(status_code=status.HTTP_200_OK, content=legacy_payload)


@router.get(
    "/api/v1/tasks/{task_id}",
    response_model=TaskDetailResponse,
    summary="Get Task Status and Execution Progress",
    description="Retrieve live status, plan summary, budget spend, and service calls."
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
    "/api/v1/buyer/tasks/{task_id}",
    response_model=TaskDetailResponse,
    summary="Legacy Task Detail Endpoint",
    description="Maintains backward compatibility for /api/v1/buyer/tasks/{task_id} callers."
)
async def legacy_get_task_status(task_id: str):
    return await get_task_status(task_id)


@router.get(
    "/api/v1/tasks/{task_id}/result",
    response_model=TaskResultResponse,
    summary="Get Final Result and Provenance",
    description="Retrieve combined synthesized output, source provenance, and purchase explanation."
)
async def get_task_result(task_id: str):
    result = buyer_service.get_task_result(task_id)
    if not result:
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
    return JSONResponse(status_code=status.HTTP_200_OK, content=result.model_dump())


@router.get(
    "/api/v1/tasks/{task_id}/calls",
    response_model=TaskCallsResponse,
    summary="Get Service Calls for Task",
    description="Retrieve all granular service invocation records for a task."
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
        content={"task_id": task_id, "items": [c.model_dump() for c in calls], "calls": [c.model_dump() for c in calls]}
    )
