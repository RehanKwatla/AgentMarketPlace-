# Seller Payment Verification Integration Guide (Member 1 -> Member 2)

**Owner:** Member 1 — Payment Engine & Security  
**Target Consumer:** Member 2 — Seller Subsystem (`backend/sellers/`)  
**Status:** [IMPLEMENTED] Available on branch `M1` via `backend/payments/dependencies.py`  

---

## 1. Executive Summary

Under the **DI-06 Code of Conduct & Binding Rules (`AGENTS.md`)**, Section 2 explicitly mandates:
> **Never Fabricate Payment Evidence:**
> - DO NOT create dummy responses claiming successful payment unless verified against the actual x402 payment lifecycle or genuine testnet receipt.
> - DO NOT mock fake transaction hashes or synthetic receipts (`receipt_{uuid}`).
> - HTTP 200 DOES NOT prove settlement without on-chain or facilitator evidence.

Currently, `backend/sellers/routes.py` lines 82, 105, and 128 emit synthetic `receipt_{uuid.uuid4().hex[:12]}`. To enable Member 2 to replace this with real on-chain/facilitator verified settlement proofs while strictly respecting code ownership boundaries, Member 1 provides the turnkey helper `verify_seller_payment`.

---

## 2. Available Interface Contract

From `backend.payments`:

```python
from backend.payments import verify_seller_payment, get_seller_payment_verifier
```

### Signature:

```python
async def verify_seller_payment(
    service_id: str,
    amount_units: int,
    pay_to: str,
    payment_payload_header: Optional[str],
    verifier: Optional[SellerPaymentVerifierInterface] = None,
) -> Optional[str]:
    """Turnkey verification helper for Member 2 seller endpoints.

    Behavior:
    1. If payment_payload_header is None or empty:
       Returns None so the seller endpoint can issue a standard HTTP 402 challenge.
    2. If payment_payload_header is provided:
       Parses the payload, issues requirement, and verifies payment.
       - Valid: Returns the settlement proof string (facilitator receipt ID or on-chain tx hash).
       - Invalid / Unsettled: Raises HTTPException(status_code=402, detail=...) failing closed.
    """
```

---

## 3. Drop-in Replacement for Member 2

In `backend/sellers/routes.py`, Member 2 can wire up the verification in 3 lines per endpoint:

### Example: `/data` Endpoint Integration

```python
from backend.payments import verify_seller_payment

@router.post("/data", summary="Data Seller Endpoint")
async def handle_data_service(
    payload: DataSellerInput,
    x_402_payment_payload: Optional[str] = Header(None, alias=HEADER_X402_PAYMENT_PAYLOAD),
    idempotency_key: Optional[str] = Header(None, alias=HEADER_IDEMPOTENCY_KEY),
):
    settings = get_settings()

    # Step 1: Verify incoming x402 payment (or detect need for 402 challenge)
    settlement_proof = await verify_seller_payment(
        service_id="data_001",
        amount_units=2000,  # 0.002 USDC in base units
        pay_to=settings.data_seller_pay_to,
        payment_payload_header=x_402_payment_payload,
    )

    # Step 2: If no payment header was provided, issue challenge
    if settlement_proof is None:
        return _build_402_challenge(
            service_id="data_001",
            amount_units=2000,
            pay_to=settings.data_seller_pay_to,
        )

    # Step 3: Execute service business logic
    result = await data_service.execute(payload)
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content=result.model_dump()
    )

    # Step 4: Attach genuine verified settlement proof (NOT synthetic uuid)
    response.headers[HEADER_X402_SETTLEMENT_PROOF] = settlement_proof
    return response
```

Apply the identical 3-line pattern to `/scraping` (`scraping_001`, 3000 units) and `/inference` (`inference_001`, 4000 units).

---

## 4. Testnet Verification Guarantees

When Member 2 uses `verify_seller_payment`:
1. **Network Enforcement:** Verifies payments are on `eip155:84532` (Base Sepolia).
2. **Token Enforcement:** Verifies payment token matches Base Sepolia USDC (`0x036CbD53842c5426634e7929541eC2318f3dCF7e`).
3. **Recipient Enforcement:** Asserts the recipient matches the seller's registered `pay_to` address.
4. **Amount Enforcement:** Checks integer base units without floating-point errors.
5. **Fail-Closed Protection:** Reverts or malformed payloads immediately raise HTTP 402, preventing free service execution.
