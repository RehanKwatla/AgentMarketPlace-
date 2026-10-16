import React from 'react';
import { 
  ShieldCheck, 
  Code
} from 'lucide-react';

export const SellerToolsView: React.FC = () => {
  return (
    <div className="space-y-8">
      {/* Banner */}
      <div className="glass-panel p-8 rounded-2xl border border-slate-800 relative overflow-hidden">
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 text-xs font-mono mb-3">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Seller Onboarding & Protocol Spec</span>
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight">
            Register Autonomous Services in the Agent Economy
          </h2>
          <p className="text-slate-400 text-sm mt-2 leading-relaxed">
            Sell microservices to autonomous buyer agents using the standardized x402 v2 payment challenge flow. Microservices are invoked with HTTP 402 challenge-response on Base Sepolia.
          </p>
        </div>
      </div>

      {/* Protocol Architecture Specs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-3">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 flex items-center justify-center font-mono font-bold">
            1
          </div>
          <h3 className="text-base font-semibold text-white">HTTP 402 Challenge</h3>
          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            When an unauthenticated buyer agent calls your service endpoint, respond with status <code className="text-blue-400 font-mono">402 Payment Required</code> and header <code className="text-blue-400 font-mono">X-402-Requirement</code>.
          </p>
        </div>

        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-3">
          <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20 flex items-center justify-center font-mono font-bold">
            2
          </div>
          <h3 className="text-base font-semibold text-white">EIP-712 Verification</h3>
          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            The buyer re-submits the call with header <code className="text-blue-400 font-mono">X-402-Payment-Payload</code> containing an EIP-712 typed signature for Base Sepolia USDC.
          </p>
        </div>

        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center font-mono font-bold">
            3
          </div>
          <h3 className="text-base font-semibold text-white">Settlement Proof (200 OK)</h3>
          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            Execute the payload, settle or claim the micropayment receipt, and emit <code className="text-blue-400 font-mono">X-402-Settlement-Proof</code> in your HTTP 200 response.
          </p>
        </div>
      </div>

      {/* Code Snippet for Seller Implementation */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Code className="w-4 h-4 text-blue-400" />
            <h3 className="text-sm font-bold text-white font-mono">FastAPI Seller Endpoint Reference</h3>
          </div>
          <span className="text-[11px] font-mono text-slate-500">Python 3.11+ / FastAPI</span>
        </div>

        <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs font-mono overflow-x-auto text-slate-300">
          <pre>{`@router.post("/my-service")
async def handle_service(
    payload: ServiceInput,
    x_402_payment_payload: Optional[str] = Header(None, alias="X-402-Payment-Payload")
):
    if not x_402_payment_payload:
        challenge = {
            "version": "2.0",
            "network": "eip155:84532",
            "token": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
            "amount": "2000", # 0.002 USDC
            "payTo": "0xYourSellerWalletAddress",
            "nonce": f"nonce_{uuid.uuid4().hex[:16]}"
        }
        return JSONResponse(
            status_code=402,
            content={"detail": "Payment Required via x402 v2 protocol."},
            headers={"X-402-Requirement": json.dumps(challenge)}
        )
    
    # Process valid call
    result = await execute_computation(payload)
    response = JSONResponse(status_code=200, content=result)
    response.headers["X-402-Settlement-Proof"] = f"receipt_{uuid.uuid4().hex[:12]}"
    return response`}</pre>
        </div>
      </div>

      {/* Onboarding Notice */}
      <div className="p-5 rounded-2xl bg-slate-900/40 border border-slate-800 text-xs font-mono text-slate-400 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <span className="text-white font-semibold block">Dynamic Self-Registration Portal</span>
          <p className="text-slate-400 text-xs font-sans">
            Seller catalog self-service registration endpoint is currently staged for the upcoming sprint. In this hackathon release, seller services (Data, Scraping, Inference) are pre-registered via Member 2's catalog registry.
          </p>
        </div>
        <span className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 border border-slate-700 text-xs font-mono whitespace-nowrap">
          Staged for Sprint 2
        </span>
      </div>
    </div>
  );
};
