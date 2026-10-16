"""Buyer Agent API Routes."""
from fastapi import APIRouter, status
from backend.shared.schemas import TaskRequest, TaskResponse
from backend.buyer.buyer_agent import BuyerAgent

router = APIRouter(prefix="/api/v1/buyer", tags=["Buyer Agent"])
buyer = BuyerAgent()


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_200_OK, summary="Submit Buyer Task")
async def create_buyer_task(request: TaskRequest):
    """Submit a complex goal for the autonomous buyer agent to plan, budget, and execute."""
    return await buyer.execute_task(request)
