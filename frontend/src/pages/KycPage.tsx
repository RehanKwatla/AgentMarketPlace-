import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  ShieldAlert, 
  ShieldX, 
  Clock, 
  CheckCircle2, 
  AlertTriangle,
  History,
  Lock,
  ArrowRight
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const KycPage: React.FC = () => {
  const { kycStatus, initiateKyc, simulateKycDecision, isAuthenticated } = useAuth();

  const [country, setCountry] = useState('US');
  const [accountType, setAccountType] = useState('individual');
  const [intendedUse, setIntendedUse] = useState('Autonomous agent marketplace testing');
  const [loading, setLoading] = useState(false);
  const [simLoading, setSimLoading] = useState(false);
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  if (!isAuthenticated) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-4 space-y-6">
        <div className="bg-[#FFFFFF] border border-[#CFC7BB] rounded-xl p-8 text-center space-y-4 shadow-sm">
          <Lock className="w-10 h-10 text-[#7D292D] mx-auto" />
          <h2 className="text-xl font-bold font-serif text-[#241B19]">Authentication Required</h2>
          <p className="text-xs text-[#82786F] max-w-md mx-auto">
            You must be signed in to manage your identity verification and access KYC-gated features.
          </p>
          <div className="pt-2 flex justify-center gap-3">
            <Link to="/login" className="px-4 py-2 bg-[#7D292D] text-[#F7F4EE] rounded-lg text-xs font-semibold hover:bg-[#612024] transition-colors">
              Sign In
            </Link>
            <Link to="/signup" className="px-4 py-2 border border-[#CFC7BB] text-[#241B19] rounded-lg text-xs font-semibold hover:bg-[#DED8CD]/60 transition-colors">
              Create Account
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const status = kycStatus?.status || 'NOT_STARTED';

  const getStatusBadge = () => {
    switch (status) {
      case 'VERIFIED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#38865B]/15 text-[#38865B] border border-[#38865B]/30">
            <CheckCircle2 size={14} /> VERIFIED [SIMULATED]
          </span>
        );
      case 'PENDING':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#B37400]/15 text-[#B37400] border border-[#B37400]/30">
            <Clock size={14} /> PENDING REVIEW
          </span>
        );
      case 'REQUIRES_REVIEW':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#B37400]/15 text-[#B37400] border border-[#B37400]/30">
            <AlertTriangle size={14} /> REQUIRES REVIEW
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#B84040]/15 text-[#B84040] border border-[#B84040]/30">
            <ShieldX size={14} /> REJECTED
          </span>
        );
      case 'EXPIRED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#82786F]/15 text-[#82786F] border border-[#82786F]/30">
            <Clock size={14} /> EXPIRED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-[#82786F]/15 text-[#82786F] border border-[#82786F]/30">
            <ShieldAlert size={14} /> NOT STARTED
          </span>
        );
    }
  };

  async function handleInitiate(e: React.FormEvent) {
    e.preventDefault();
    try {
      setLoading(true);
      setMsg(null);
      const url = await initiateKyc({ country, account_type: accountType, intended_use: intendedUse });
      setMsg({ type: 'success', text: `Verification session created! Hosted capture session URL: ${url}` });
    } catch (err: any) {
      setMsg({ type: 'error', text: err.message || 'Failed to initiate verification session.' });
    } finally {
      setLoading(false);
    }
  }

  async function handleSimulate(decision: string) {
    try {
      setSimLoading(true);
      setMsg(null);
      await simulateKycDecision(decision, `Deterministic test transition to ${decision}`);
      setMsg({ type: 'success', text: `Mock provider webhook processed: status updated to ${decision}` });
    } catch (err: any) {
      setMsg({ type: 'error', text: err.message || `Failed to transition to ${decision}. Check state machine rules.` });
    } finally {
      setSimLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      {/* 1. Prominent Mock & Safety Banner */}
      <div className="bg-[#B37400]/10 border border-[#B37400]/30 rounded-xl p-4 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-[#B37400] shrink-0 mt-0.5" />
        <div className="space-y-1 text-xs">
          <p className="font-bold text-[#241B19]">
            [SIMULATED - NOT REAL-WORLD IDENTITY VERIFICATION]
          </p>
          <p className="text-[#82786F]">
            Real KYC provider integration is disabled. Local deterministic mock provider is active for development.
            No live biometric services are contacted, and raw identity documents are never requested or stored.
          </p>
        </div>
      </div>

      {msg && (
        <div
          className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
            msg.type === 'success'
              ? 'bg-[#38865B]/10 border border-[#38865B]/30 text-[#38865B]'
              : 'bg-[#B84040]/10 border border-[#B84040]/30 text-[#B84040]'
          }`}
        >
          {msg.type === 'success' ? <CheckCircle2 size={16} /> : <ShieldAlert size={16} />}
          <span>{msg.text}</span>
        </div>
      )}

      {/* 2. Current Status Card */}
      <div className="bg-[#FFFFFF] border border-[#CFC7BB] rounded-xl p-6 space-y-4 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#CFC7BB]">
          <div>
            <h1 className="text-xl font-bold font-serif text-[#241B19]">Identity Verification (KYC)</h1>
            <p className="text-xs text-[#82786F]">Provider-neutral identity status and lifecycle audit</p>
          </div>
          <div>{getStatusBadge()}</div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
          <div className="p-3 bg-[#F7F4EE] rounded-lg border border-[#CFC7BB]">
            <span className="text-[#82786F] block text-[10px]">Active Provider</span>
            <span className="font-semibold text-[#241B19]">{kycStatus?.provider || 'mock_simulated'}</span>
          </div>
          <div className="p-3 bg-[#F7F4EE] rounded-lg border border-[#CFC7BB]">
            <span className="text-[#82786F] block text-[10px]">Provider Reference</span>
            <span className="font-semibold text-[#241B19] truncate block">
              {kycStatus?.provider_reference_id || 'None (Uninitiated)'}
            </span>
          </div>
          <div className="p-3 bg-[#F7F4EE] rounded-lg border border-[#CFC7BB]">
            <span className="text-[#82786F] block text-[10px]">Simulation Mode</span>
            <span className="font-semibold text-[#38865B]">Active (Mock)</span>
          </div>
        </div>

        {kycStatus?.rejection_reasons && (
          <div className="p-3 rounded-lg bg-[#B84040]/10 border border-[#B84040]/30 text-[#B84040] text-xs">
            <strong>Rejection Reason:</strong> {kycStatus.rejection_reasons}
          </div>
        )}
      </div>

      {/* 3. Initiate Verification Flow */}
      {(status === 'NOT_STARTED' || status === 'REJECTED' || status === 'EXPIRED') && (
        <div className="bg-[#FFFFFF] border border-[#CFC7BB] rounded-xl p-6 space-y-4 shadow-sm">
          <h2 className="text-base font-bold font-serif text-[#241B19]">
            {status === 'NOT_STARTED' ? 'Start Hosted Verification Session' : 'Re-verify Identity'}
          </h2>
          <p className="text-xs text-[#82786F]">
            Submit applicant metadata to create a hosted capture session. Only metadata is stored; raw documents are handled by the mock provider interface.
          </p>

          <form onSubmit={handleInitiate} className="space-y-4 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[#82786F] mb-1 font-semibold">Country / Jurisdiction</label>
                <select
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  className="w-full bg-white border border-[#CFC7BB] rounded-lg px-3 py-2 text-[#241B19]"
                >
                  <option value="US">United States</option>
                  <option value="IN">India</option>
                  <option value="GB">United Kingdom</option>
                  <option value="SG">Singapore</option>
                  <option value="CA">Canada</option>
                </select>
              </div>

              <div>
                <label className="block text-[#82786F] mb-1 font-semibold">Account Type</label>
                <select
                  value={accountType}
                  onChange={(e) => setAccountType(e.target.value)}
                  className="w-full bg-white border border-[#CFC7BB] rounded-lg px-3 py-2 text-[#241B19]"
                >
                  <option value="individual">Individual</option>
                  <option value="business">Business / Organization</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-[#82786F] mb-1 font-semibold">Intended Marketplace Use</label>
              <input
                type="text"
                value={intendedUse}
                onChange={(e) => setIntendedUse(e.target.value)}
                className="w-full bg-white border border-[#CFC7BB] rounded-lg px-3 py-2 text-[#241B19]"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2.5 bg-[#7D292D] text-[#F7F4EE] rounded-lg font-semibold hover:bg-[#612024] transition-colors cursor-pointer flex items-center gap-2"
            >
              {loading ? 'Creating session...' : 'Initiate Mock Verification Session'} <ArrowRight size={15} />
            </button>
          </form>
        </div>
      )}

      {/* 4. Development Simulator Controls */}
      <div className="bg-[#FFFFFF] border border-[#CFC7BB] rounded-xl p-6 space-y-4 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold font-serif text-[#241B19]">
            Development & Testing Simulator
          </h2>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#DED8CD] text-[#241B19]">
            Webhook HMAC Engine
          </span>
        </div>
        <p className="text-xs text-[#82786F]">
          Simulate deterministic provider decisions. State transitions are strictly validated against the state machine and signed with HMAC-SHA256.
        </p>

        <div className="flex flex-wrap gap-2.5 pt-1">
          <button
            onClick={() => handleSimulate('VERIFIED')}
            disabled={simLoading || status !== 'PENDING' && status !== 'REQUIRES_REVIEW'}
            className="px-3.5 py-2 rounded-lg text-xs font-semibold bg-[#38865B] text-white hover:bg-[#2c6d48] disabled:opacity-40 transition-colors cursor-pointer"
          >
            Simulate Decision: VERIFIED
          </button>
          <button
            onClick={() => handleSimulate('REQUIRES_REVIEW')}
            disabled={simLoading || status !== 'PENDING' && status !== 'VERIFIED'}
            className="px-3.5 py-2 rounded-lg text-xs font-semibold bg-[#B37400] text-white hover:bg-[#8f5d00] disabled:opacity-40 transition-colors cursor-pointer"
          >
            Simulate Decision: REQUIRES_REVIEW
          </button>
          <button
            onClick={() => handleSimulate('REJECTED')}
            disabled={simLoading || status !== 'PENDING' && status !== 'REQUIRES_REVIEW'}
            className="px-3.5 py-2 rounded-lg text-xs font-semibold bg-[#B84040] text-white hover:bg-[#962f2f] disabled:opacity-40 transition-colors cursor-pointer"
          >
            Simulate Decision: REJECTED
          </button>
          <button
            onClick={() => handleSimulate('EXPIRED')}
            disabled={simLoading || status !== 'VERIFIED'}
            className="px-3.5 py-2 rounded-lg text-xs font-semibold bg-[#82786F] text-white hover:bg-[#635b53] disabled:opacity-40 transition-colors cursor-pointer"
          >
            Simulate Expiry: EXPIRED
          </button>
        </div>
      </div>

      {/* 5. Chronological Audit Trail */}
      <div className="bg-[#FFFFFF] border border-[#CFC7BB] rounded-xl p-6 space-y-4 shadow-sm">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-[#7D292D]" />
          <h2 className="text-base font-bold font-serif text-[#241B19]">Verification Audit Trail</h2>
        </div>

        {kycStatus?.audit_history && kycStatus.audit_history.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-[#CFC7BB] text-[#82786F]">
                  <th className="py-2 px-3">Timestamp</th>
                  <th className="py-2 px-3">From</th>
                  <th className="py-2 px-3">To</th>
                  <th className="py-2 px-3">Provider</th>
                  <th className="py-2 px-3">Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EFECE6]">
                {kycStatus.audit_history.map((entry) => (
                  <tr key={entry.id} className="hover:bg-[#F7F4EE]">
                    <td className="py-2.5 px-3 text-[#82786F] whitespace-nowrap">
                      {new Date(entry.timestamp).toLocaleString()}
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-[#82786F]">{entry.from_status}</td>
                    <td className="py-2.5 px-3 font-bold text-[#241B19]">{entry.to_status}</td>
                    <td className="py-2.5 px-3 text-[#82786F]">{entry.provider}</td>
                    <td className="py-2.5 px-3 text-[#241B19] max-w-xs truncate">{entry.reason || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-xs text-[#82786F] py-2">No verification transitions recorded yet.</p>
        )}
      </div>
    </div>
  );
};
