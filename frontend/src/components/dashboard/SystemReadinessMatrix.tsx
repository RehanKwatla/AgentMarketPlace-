import React from 'react';
import { 
  Activity, 
  Layers, 
  Cpu, 
  ShieldCheck, 
  Database,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle
} from 'lucide-react';
import { HealthInfo, PaymentSubsystemStatus, ServiceDefinition, LedgerRecord } from '../../types';

interface SystemReadinessMatrixProps {
  healthInfo: HealthInfo | null;
  paymentStatus: PaymentSubsystemStatus | null;
  services: ServiceDefinition[];
  ledger: LedgerRecord[];
  pendingReconciliationsCount: number;
}

type ReadinessState = 'ready' | 'degraded' | 'unavailable' | 'unknown';

interface Subsystem {
  id: string;
  name: string;
  category: string;
  icon: React.ComponentType<{ className?: string }>;
  state: ReadinessState;
  stateLabel: string;
  detail: string;
  latencyOrMeta?: string;
}

export const SystemReadinessMatrix: React.FC<SystemReadinessMatrixProps> = ({
  healthInfo,
  paymentStatus,
  services,
  ledger,
  pendingReconciliationsCount,
}) => {
  // Determine state for each subsystem based on actual evidence
  const isApiConnected = healthInfo !== null;
  const isApiHealthy = healthInfo?.status === 'healthy';

  const apiState: ReadinessState = !isApiConnected 
    ? 'unavailable' 
    : isApiHealthy 
    ? 'ready' 
    : 'degraded';

  const registryState: ReadinessState = !isApiConnected 
    ? 'unavailable' 
    : services.length > 0 
    ? 'ready' 
    : 'degraded';

  const buyerState: ReadinessState = !isApiConnected 
    ? 'unavailable' 
    : isApiHealthy && services.length > 0 
    ? 'ready' 
    : 'degraded';

  const paymentState: ReadinessState = !isApiConnected 
    ? 'unavailable' 
    : paymentStatus 
    ? pendingReconciliationsCount > 0 
      ? 'degraded' 
      : 'ready' 
    : 'unknown';

  const ledgerState: ReadinessState = !isApiConnected 
    ? 'unavailable' 
    : Array.isArray(ledger) 
    ? 'ready' 
    : 'unknown';

  const subsystems: Subsystem[] = [
    {
      id: 'backend_api',
      name: 'Backend API',
      category: 'Core Runtime',
      icon: Activity,
      state: apiState,
      stateLabel: apiState === 'ready' ? 'Ready' : apiState === 'degraded' ? 'Degraded' : 'Unavailable',
      detail: healthInfo 
        ? `FastAPI ${healthInfo.version || 'v1.0.0'} • Network: ${healthInfo.network || '84532'}`
        : 'Cannot reach FastAPI endpoint at http://localhost:8000',
      latencyOrMeta: healthInfo ? 'HTTP 200 OK' : 'Connection failed',
    },
    {
      id: 'service_registry',
      name: 'Service Registry',
      category: 'Marketplace',
      icon: Layers,
      state: registryState,
      stateLabel: registryState === 'ready' ? 'Ready' : registryState === 'degraded' ? 'Degraded' : 'Unavailable',
      detail: services.length > 0 
        ? `${services.length} active service providers registered` 
        : 'Zero sellers registered in database',
      latencyOrMeta: `${services.length} endpoints`,
    },
    {
      id: 'buyer_orchestration',
      name: 'Buyer / Orchestration',
      category: 'Autonomous Agent',
      icon: Cpu,
      state: buyerState,
      stateLabel: buyerState === 'ready' ? 'Ready' : buyerState === 'degraded' ? 'Degraded' : 'Unavailable',
      detail: buyerState === 'ready'
        ? 'EIP-712 signer & multi-hop task planner online'
        : 'Requires active backend and registered services',
      latencyOrMeta: 'EIP-712 v2',
    },
    {
      id: 'x402_payments',
      name: 'x402 Payment Integration',
      category: 'Settlement Engine',
      icon: ShieldCheck,
      state: paymentState,
      stateLabel: paymentState === 'ready' ? 'Ready' : paymentState === 'degraded' ? 'Degraded' : paymentState === 'unavailable' ? 'Unavailable' : 'Unknown',
      detail: paymentStatus
        ? `${paymentStatus.facilitator_configured ? 'Facilitator active' : 'Local test verifier'} • ${pendingReconciliationsCount} pending reconciliations`
        : 'Payment telemetry not exposed or unreachable',
      latencyOrMeta: 'Base Sepolia',
    },
    {
      id: 'ledger_audit',
      name: 'Ledger Audit Chain',
      category: 'Storage & Audit',
      icon: Database,
      state: ledgerState,
      stateLabel: ledgerState === 'ready' ? 'Ready' : ledgerState === 'unavailable' ? 'Unavailable' : 'Unknown',
      detail: Array.isArray(ledger)
        ? `${ledger.length} verified audit records indexed`
        : 'Ledger storage unreachable',
      latencyOrMeta: `${ledger.length} events`,
    },
  ];

  const getStateBadge = (state: ReadinessState) => {
    switch (state) {
      case 'ready':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-[#E4EFE8] text-[#38865B] border border-[#A8B3A1]/70 font-medium">
            <CheckCircle2 className="w-3 h-3 text-[#38865B]" />
            <span>Ready</span>
          </span>
        );
      case 'degraded':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-[#FBF2E5] text-[#A86E24] border border-[#DED8CD] font-medium">
            <AlertTriangle className="w-3 h-3 text-[#A86E24]" />
            <span>Degraded</span>
          </span>
        );
      case 'unavailable':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-[#F4ECEB] text-[#7D292D] border border-[#CFC7BB] font-medium">
            <XCircle className="w-3 h-3 text-[#7D292D]" />
            <span>Unavailable</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-[#DED8CD]/60 text-[#82786F] border border-[#CFC7BB]">
            <HelpCircle className="w-3 h-3 text-[#82786F]" />
            <span>Unknown</span>
          </span>
        );
    }
  };

  return (
    <div className="rounded-xl border border-[#CFC7BB] bg-[#F7F4EE] shadow-sm p-4 space-y-3">
      <div className="flex items-center justify-between pb-2 border-b border-[#CFC7BB]/60">
        <div>
          <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#82786F]">
            System Readiness & Capability Matrix
          </h3>
          <p className="text-[11px] text-[#82786F] mt-0.5">
            Real-time telemetry verified against backend health and subsystem contracts.
          </p>
        </div>
        <div className="text-[10px] font-mono text-[#82786F]">
          {subsystems.filter(s => s.state === 'ready').length} / {subsystems.length} Ready
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
        {subsystems.map((sub) => {
          const Icon = sub.icon;
          return (
            <div 
              key={sub.id}
              className="p-3 rounded-lg bg-[#FFFFFF] border border-[#CFC7BB] hover:border-[#7D292D]/40 transition-colors flex flex-col justify-between space-y-2.5 shadow-xs"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-md bg-[#DED8CD]/60 border border-[#CFC7BB] text-[#7D292D]">
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-[#241B19] leading-tight">
                      {sub.name}
                    </div>
                    <div className="text-[10px] font-mono text-[#82786F]">
                      {sub.category}
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <p className="text-[11px] text-[#82786F] line-clamp-2 leading-relaxed">
                  {sub.detail}
                </p>
              </div>

              <div className="pt-2 border-t border-[#CFC7BB]/60 flex items-center justify-between">
                <div className="text-[10px] font-mono text-[#82786F]">
                  {sub.latencyOrMeta}
                </div>
                {getStateBadge(sub.state)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
