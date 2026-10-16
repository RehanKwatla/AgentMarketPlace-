"""Phase 3 Orchestration Tests for BuyerAgent Multi-Hop Tool-Calling Flows.

Validates that BuyerAgent interfaces with BuyerPaymentClientInterface and handles
official x402 headers (X-402-Requirement, X-402-Payment-Payload, X-402-Settlement-Proof)
across sequential and concurrent multi-hop tool invocations.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from typing import Optional

from backend.shared.constants import (
    HEADER_IDEMPOTENCY_KEY,
    HEADER_X402_PAYMENT_PAYLOAD,
    HEADER_X402_REQUIREMENT,
    HEADER_X402_SETTLEMENT_PROOF,
    NETWORK_BASE_SEPOLIA,
    USDC_BASE_SEPOLIA,
    LedgerStatus,
)
from backend.shared.schemas import (
    PaymentPayload,
    PaymentRequirement,
    SettlementReceipt,
    TaskRequest,
    TaskResponse,
)
from backend.payments.budget import BudgetManager
from backend.payments.interfaces import BuyerPaymentClientInterface
from backend.registry.service import registry_service
from backend.buyer.buyer_agent import BuyerAgent
from backend.buyer.payment_client import BuyerPaymentClient
from backend.buyer.schemas import CallStatus


class MockSpyPaymentClient(BuyerPaymentClientInterface):
    """Spy payment client tracking x402 lifecycle interactions."""

    def __init__(self):
        self.payload_creations: list[PaymentRequirement] = []
        self.settlement_verifications: list[str] = []

    async def create_payment_payload(
        self,
        requirement: PaymentRequirement,
        idempotency_key: str = "",
    ) -> PaymentPayload:
        self.payload_creations.append(requirement)
        return PaymentPayload(
            authorization={
                "network": requirement.network,
                "token": requirement.token,
                "amount": requirement.amount,
                "payTo": requirement.payTo,
                "nonce": requirement.nonce,
            },
            signature="0x" + "7" * 130,
            buyer_address="0x1000000000000000000000000000000000000001",
        )

    async def verify_settlement(
        self,
        receipt_header: Optional[str],
    ) -> Optional[SettlementReceipt]:
        self.settlement_verifications.append(receipt_header or "")
        if not receipt_header:
            return None
        return SettlementReceipt(
            tx_hash="0x" + "f" * 64,
            facilitator_receipt_id="fac_receipt_multihop_test",
            settled_amount_units=int(2000),
        )


def test_buyer_agent_conforms_to_buyer_payment_client_interface():
    """Verify BuyerAgent explicitly interfaces with BuyerPaymentClientInterface."""
    spy = MockSpyPaymentClient()
    agent = BuyerAgent(payment_client=spy)

    assert isinstance(agent.payment_client, BuyerPaymentClientInterface)

    # Default construction also satisfies interface
    default_agent = BuyerAgent()
    assert isinstance(default_agent.payment_client, BuyerPaymentClientInterface)
    assert isinstance(default_agent.payment_client, BuyerPaymentClient)


@pytest.mark.asyncio
async def test_buyer_agent_multi_hop_flow_with_x402_headers():
    """Verify 3-hop tool-calling flow (Data -> Scraping -> Inference) handling official x402 headers."""
    spy = MockSpyPaymentClient()
    agent = BuyerAgent(payment_client=spy)

    data_svc = registry_service.get_service("data_001")
    scrape_svc = registry_service.get_service("scraping_001")
    infer_svc = registry_service.get_service("inference_001")

    # Mock seller responses across the multi-hop sequence:
    # Hop 1 (Data): 402 Challenge -> 200 Paid
    # Hop 2 (Scraping): 402 Challenge -> 200 Paid
    # Hop 3 (Inference): 402 Challenge -> 200 Paid
    async def dynamic_post(url, *args, **kwargs):
        headers = kwargs.get("headers", {})
        json_data = kwargs.get("json", {})
        has_payment = HEADER_X402_PAYMENT_PAYLOAD in headers

        if "data" in url or "symbol" in json_data:
            if not has_payment:
                return MagicMock(
                    status_code=402,
                    headers={
                        HEADER_X402_REQUIREMENT: json.dumps({
                            "version": "2.0",
                            "network": NETWORK_BASE_SEPOLIA,
                            "token": USDC_BASE_SEPOLIA,
                            "amount": str(data_svc.price_atomic),
                            "payTo": data_svc.pay_to,
                            "nonce": "nonce_data_hop1",
                            "service_id": "data_001",
                        })
                    },
                )
            else:
                return MagicMock(
                    status_code=200,
                    headers={
                        HEADER_X402_SETTLEMENT_PROOF: "proof_hop1_receipt",
                        "content-type": "application/json",
                    },
                    json=MagicMock(return_value={
                        "symbol": "ETH",
                        "price": 3500.50,
                        "volume_24h": 12500000.0,
                        "timestamp": "2026-10-16T12:00:00Z",
                    }),
                )
        elif "scrap" in url or "url" in json_data:
            if not has_payment:
                return MagicMock(
                    status_code=402,
                    headers={
                        HEADER_X402_REQUIREMENT: json.dumps({
                            "version": "2.0",
                            "network": NETWORK_BASE_SEPOLIA,
                            "token": USDC_BASE_SEPOLIA,
                            "amount": str(scrape_svc.price_atomic),
                            "payTo": scrape_svc.pay_to,
                            "nonce": "nonce_scrape_hop2",
                            "service_id": "scraping_001",
                        })
                    },
                )
            else:
                return MagicMock(
                    status_code=200,
                    headers={
                        HEADER_X402_SETTLEMENT_PROOF: "proof_hop2_receipt",
                        "content-type": "application/json",
                    },
                    json=MagicMock(return_value={
                        "url": "https://ethereum.org",
                        "title": "Ethereum Ecosystem Overview",
                        "content": "Ethereum is a decentralized global software platform powered by ether.",
                        "word_count": 12,
                    }),
                )
        elif "infer" in url or "prompt" in json_data:
            if not has_payment:
                return MagicMock(
                    status_code=402,
                    headers={
                        HEADER_X402_REQUIREMENT: json.dumps({
                            "version": "2.0",
                            "network": NETWORK_BASE_SEPOLIA,
                            "token": USDC_BASE_SEPOLIA,
                            "amount": str(infer_svc.price_atomic),
                            "payTo": infer_svc.pay_to,
                            "nonce": "nonce_infer_hop3",
                            "service_id": "inference_001",
                        })
                    },
                )
            else:
                return MagicMock(
                    status_code=200,
                    headers={
                        HEADER_X402_SETTLEMENT_PROOF: "proof_hop3_receipt",
                        "content-type": "application/json",
                    },
                    json=MagicMock(return_value={
                        "response": "Market Synthesis: ETH price is $3500.50 with solid momentum based on ecosystem updates.",
                        "model_used": "meta-llama/Llama-3-70b-Instruct",
                        "tokens_generated": 24,
                    }),
                )
        return MagicMock(status_code=404)

    with patch("httpx.AsyncClient.post", side_effect=dynamic_post) as mock_post:
        req = TaskRequest(
            task="Lookup Ethereum price, scrape ethereum.org, and synthesize market summary",
            budget_usdc="0.050000",
        )
        response: TaskResponse = await agent.execute_task(req)

    # 1. Assert TaskResponse completion
    assert response.status == "completed"
    assert response.budget_allocated_usdc == "0.050000"
    assert response.total_cost_usdc == "0.009000"  # 2000 + 3000 + 4000 = 9000 base units
    assert len(response.executions) == 3

    # 2. Assert multi-hop steps executed and status
    step_services = [e.service_id for e in response.executions]
    assert "data_001" in step_services
    assert "scraping_001" in step_services
    assert "inference_001" in step_services
    for step in response.executions:
        assert step.status == LedgerStatus.PAID
        assert step.tx_hash is not None

    # 3. Assert x402 headers were routed to Member 1 payment interface
    assert len(spy.payload_creations) == 3
    assert len(spy.settlement_verifications) == 3
    assert set(spy.settlement_verifications) == {"proof_hop1_receipt", "proof_hop2_receipt", "proof_hop3_receipt"}

    # 4. Assert multi-hop context forwarding to Hop 3 (Inference prompt received Hop 1 & Hop 2 data)
    # The final call was Hop 3 paid request
    hop3_call_args = mock_post.call_args_list[-1]
    hop3_payload = hop3_call_args.kwargs.get("json", {})
    hop3_prompt = hop3_payload.get("prompt", "")
    assert "3500.5" in hop3_prompt or "Market Data" in hop3_prompt
    assert "Ethereum Ecosystem Overview" in hop3_prompt or "Scraped Article" in hop3_prompt


@pytest.mark.asyncio
async def test_buyer_agent_multi_hop_budget_refusal_before_payment():
    """Verify multi-hop plan is refused before payment if budget cannot afford all required hops."""
    spy = MockSpyPaymentClient()
    agent = BuyerAgent(payment_client=spy)

    # 3 hops cost 2000 + 3000 + 4000 = 9000 atomic units (0.009 USDC).
    # Providing 0.004 USDC (4000 units) must refuse without calling payment interface.
    req = TaskRequest(
        task="Lookup Ethereum price, scrape ethereum.org, and synthesize market summary",
        budget_usdc="0.004000",
    )
    response = await agent.execute_task(req)

    assert response.status == "refused"
    assert response.total_cost_usdc == "0.000000"
    assert len(spy.payload_creations) == 0
    assert len(spy.settlement_verifications) == 0


@pytest.mark.asyncio
async def test_buyer_agent_multi_hop_safe_halt_on_uncertain_payment():
    """Verify multi-hop execution halts on uncertain settlement without running subsequent hops."""
    spy = MockSpyPaymentClient()
    agent = BuyerAgent(payment_client=spy)

    data_svc = registry_service.get_service("data_001")

    # Hop 1 returns 200 but lacks X-402-Settlement-Proof header -> uncertain settlement
    mock_responses = [
        MagicMock(
            status_code=402,
            headers={
                HEADER_X402_REQUIREMENT: json.dumps({
                    "version": "2.0",
                    "network": NETWORK_BASE_SEPOLIA,
                    "token": USDC_BASE_SEPOLIA,
                    "amount": str(data_svc.price_atomic),
                    "payTo": data_svc.pay_to,
                    "nonce": "nonce_data_hop1",
                    "service_id": "data_001",
                })
            },
        ),
        # 200 without settlement proof
        MagicMock(
            status_code=200,
            headers={"content-type": "application/json"},
            json=MagicMock(return_value={"symbol": "ETH"}),
        ),
    ]

    with patch("httpx.AsyncClient.post", side_effect=mock_responses):
        req = TaskRequest(
            task="Lookup Ethereum price and synthesize market summary",
            budget_usdc="0.050000",
        )
        response = await agent.execute_task(req)

    assert response.status in ["pending_reconciliation", "pending reconciliation", "failed"]
    # Downstream inference hop was blocked from running
    assert "inference_001" not in [e.service_id for e in response.executions if e.status == LedgerStatus.PAID]


@pytest.mark.asyncio
async def test_buyer_agent_call_tool_direct():
    """Verify call_tool_direct invokes a discrete tool with x402 payment headers."""
    spy = MockSpyPaymentClient()
    agent = BuyerAgent(payment_client=spy)
    budget_mgr = BudgetManager(initial_budget_units=10000)
    data_svc = registry_service.get_service("data_001")

    with patch("httpx.AsyncClient.post", side_effect=[
        MagicMock(
            status_code=402,
            headers={
                HEADER_X402_REQUIREMENT: json.dumps({
                    "version": "2.0",
                    "network": NETWORK_BASE_SEPOLIA,
                    "token": USDC_BASE_SEPOLIA,
                    "amount": str(data_svc.price_atomic),
                    "payTo": data_svc.pay_to,
                    "nonce": "direct_tool_nonce",
                    "service_id": "data_001",
                })
            },
        ),
        MagicMock(
            status_code=200,
            headers={
                HEADER_X402_SETTLEMENT_PROOF: "proof_direct_tool",
                "content-type": "application/json",
            },
            json=MagicMock(return_value={
                "symbol": "BTC",
                "price": 68000.0,
                "volume_24h": 25000000.0,
                "timestamp": "2026-10-16T12:00:00Z",
            }),
        ),
    ]):
        record = await agent.call_tool_direct(
            service_id="data_001",
            input_payload={"symbol": "BTC"},
            budget_mgr=budget_mgr,
        )

    assert record.status == CallStatus.SUCCEEDED
    assert record.service_id == "data_001"
    assert record.amount_paid_usdc in ["0.002", "0.002000"]
    assert len(spy.payload_creations) == 1
    assert len(spy.settlement_verifications) == 1
