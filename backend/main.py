"""Main FastAPI Application Entrypoint for DI-06 Agent Economy."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.shared.config import get_settings
from backend.shared.constants import NETWORK_BASE_SEPOLIA
from backend.shared.errors import AgentEconomyBaseException
from backend.shared.schemas import HealthResponse
from backend.database.session import init_db

# Subsystem routers
from backend.registry.routes import router as registry_router
from backend.buyer.routes import router as buyer_router
from backend.sellers.routes import router as sellers_router
from backend.ledger.routes import router as ledger_router
from backend.payments.routes import router as payments_router
from backend.auth.routes import router as auth_router
from backend.auth.policy_routes import router as policy_router
from backend.wallets.routes import router as wallets_router
from backend.kyc.routes import router as kyc_router

settings = get_settings()



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_db()
    yield


app = FastAPI(
    title="DI-06: Pay-Per-Call Agent Economy",
    description=(
        "Autonomous agent marketplace featuring x402 v2 payment lifecycle "
        "denominated in USDC on Base Sepolia (eip155:84532)."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

from backend.payments.middleware import X402ProtocolMiddleware

# Cross-Origin Resource Sharing (CORS) for Frontend Dashboard
raw_cors = getattr(settings, "cors_allowed_origins", "") or ""
configured_origins = [o.strip() for o in raw_cors.split(",") if o.strip()]

default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "https://agentica-two.vercel.app",
]

if settings.environment.lower() == "production":
    cors_origins = [o for o in configured_origins if o != "*"] if configured_origins else ["https://agentica-two.vercel.app", "http://localhost:5173"]
    if "https://agentica-two.vercel.app" not in cors_origins:
        cors_origins.append("https://agentica-two.vercel.app")
else:
    cors_origins = list(configured_origins)
    for dev_origin in default_origins:
        if dev_origin not in cors_origins:
            cors_origins.append(dev_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-402-Requirement",
        "X-402-Payment-Payload",
        "X-402-Settlement-Proof",
        "Payment-Required",
        "Payment-Signature",
        "Payment-Response",
        "X-Payment",
        "X-Payment-Response",
        "Idempotency-Key",
    ],
)

# Bidirectional bridge for official x402 v2 protocol wire headers
app.add_middleware(X402ProtocolMiddleware)


@app.exception_handler(AgentEconomyBaseException)
async def agent_economy_exception_handler(request: Request, exc: AgentEconomyBaseException):
    origin = request.headers.get("origin")
    headers = {}
    if origin and (origin in cors_origins or "*" in cors_origins):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error_code": exc.error_code, "detail": exc.message},
        headers=headers
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    origin = request.headers.get("origin")
    headers = {}
    if origin and (origin in cors_origins or "*" in cors_origins):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error_code": "INTERNAL_SERVER_ERROR", "detail": str(exc)},
        headers=headers
    )


# Health Check
@app.get("/health", response_model=HealthResponse, tags=["Diagnostics"], summary="Health Check")
async def health_check(response: Response):
    """Returns application health, version, network configuration, and verifies database readiness."""
    db_status = "connected"
    is_healthy = True
    try:
        from backend.database.session import SessionLocal
        from sqlalchemy import text
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"
        is_healthy = False
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="healthy" if is_healthy else "unhealthy",
        version="0.1.0",
        network=NETWORK_BASE_SEPOLIA,
        services={
            "database": db_status,
            "registry": "active",
            "payment_engine": "configured"
        }
    )


# Mount Subsystem Routers
app.include_router(registry_router)
app.include_router(buyer_router)
app.include_router(sellers_router)
app.include_router(ledger_router)
app.include_router(payments_router)
app.include_router(auth_router)
app.include_router(policy_router)
app.include_router(wallets_router)
app.include_router(kyc_router)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.host, port=settings.port, reload=True)
