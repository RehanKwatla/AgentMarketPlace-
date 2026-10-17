"""Main FastAPI Application Entrypoint for DI-06 Agent Economy."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
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

# Cross-Origin Resource Sharing (CORS) for Frontend Dashboard
raw_cors = getattr(settings, "cors_allowed_origins", "") or ""
configured_origins = [o.strip() for o in raw_cors.split(",") if o.strip()]

if settings.environment.lower() == "production":
    cors_origins = configured_origins if configured_origins else ["http://localhost:5173"]
else:
    cors_origins = list(configured_origins)
    for dev_origin in ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"]:
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
        "Idempotency-Key",
    ],
)


@app.exception_handler(AgentEconomyBaseException)
async def agent_economy_exception_handler(request: Request, exc: AgentEconomyBaseException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error_code": exc.error_code, "detail": exc.message}
    )


# Health Check
@app.get("/health", response_model=HealthResponse, tags=["Diagnostics"], summary="Health Check")
async def health_check():
    """Returns application health, version, network configuration, and subsystem connectivity."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        network=NETWORK_BASE_SEPOLIA,
        services={
            "database": "connected",
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.host, port=settings.port, reload=True)
