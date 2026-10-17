import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  Wallet, 
  Plus, 
  Trash2, 
  Check, 
  Copy, 
  Shield, 
  AlertCircle, 
  Lock,
  Star
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const WalletManagementPage: React.FC = () => {
  const { wallets, connectAndLinkWallet, updateWalletRole, unlinkWallet, isAuthenticated } = useAuth();

  const [selectedRole, setSelectedRole] = useState<'identity' | 'payment' | 'receiving'>('identity');
  const [selectedProvider, setSelectedProvider] = useState<'metamask' | 'coinbase'>('metamask');
  const [loading, setLoading] = useState(false);
  const [copiedAddress, setCopiedAddress] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  if (!isAuthenticated) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-4 space-y-6">
        <div className="bg-[#FFFFFF] border border-[#CFC7BB] rounded-xl p-8 text-center space-y-4 shadow-sm">
          <Lock className="w-10 h-10 text-[#7D292D] mx-auto" />
          <h2 className="text-xl font-bold font-serif text-[#241B19]">Authentication Required</h2>
          <p className="text-xs text-[#82786F] max-w-md mx-auto">
            You must be signed in to link EVM wallets and configure wallet roles.
          </p>
          <div className="pt-2 flex justify-center gap-3">
            <Link to="/login" className="px-4 py-2 bg-[#7D292D] text-[#F7F4EE] rounded-lg text-xs font-semibold hover:bg-[#612024] transition-colors">
              Sign In
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const handleCopy = (addr: string) => {
    navigator.clipboard.writeText(addr);
    setCopiedAddress(addr);
    setTimeout(() => setCopiedAddress(null), 2000);
  };

  const handleLink = async () => {
    try {
      setLoading(true);
      setMsg(null);
      const linked = await connectAndLinkWallet(selectedProvider, selectedRole);
      setMsg({ type: 'success', text: `Wallet ${linked.address.slice(0, 6)}... linked as ${linked.role}!` });
    } catch (err: any) {
      setMsg({ type: 'error', text: err.message || 'Failed to verify and link wallet.' });
    } finally {
      setLoading(false);
    }
  };

  const handleRoleChange = async (walletId: string, newRole: string) => {
    try {
      setMsg(null);
      await updateWalletRole(walletId, newRole);
      setMsg({ type: 'success', text: 'Wallet role updated successfully.' });
    } catch (err: any) {
      setMsg({ type: 'error', text: err.message || 'Failed to update role.' });
    }
  };

  const handleSetPrimary = async (walletId: string) => {
    try {
      setMsg(null);
      await updateWalletRole(walletId, undefined, true);
      setMsg({ type: 'success', text: 'Set as primary wallet.' });
    } catch (err: any) {
      setMsg({ type: 'error', text: err.message || 'Failed to set primary wallet.' });
    }
  };

  const handleUnlink = async (walletId: string) => {
    if (!window.confirm('Are you sure you want to unlink this wallet?')) return;
    try {
      setMsg(null);
      await unlinkWallet(walletId);
      setMsg({ type: 'success', text: 'Wallet unlinked successfully.' });
    } catch (err: any) {
      setMsg({ type: 'error', text: err.message || 'Failed to unlink wallet.' });
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      {/* 1. Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold font-serif text-[#241B19]">Linked EVM Wallets</h1>
          <p className="text-xs text-[#82786F]">
            Manage identities, payment authorization, and receiving addresses on Base Sepolia.
          </p>
        </div>
        <span className="text-xs font-mono px-2.5 py-1 rounded bg-[#DED8CD] text-[#241B19] border border-[#CFC7BB] w-fit">
          Base Sepolia (eip155:84532)
        </span>
      </div>

      {msg && (
        <div
          className={`p-3 rounded-lg text-xs flex items-center gap-2 ${
            msg.type === 'success'
              ? 'bg-[#38865B]/10 border border-[#38865B]/30 text-[#38865B]'
              : 'bg-[#B84040]/10 border border-[#B84040]/30 text-[#B84040]'
          }`}
        >
          {msg.type === 'success' ? <Check size={16} /> : <AlertCircle size={16} />}
          <span>{msg.text}</span>
        </div>
      )}

      {/* 2. Link New Wallet Card */}
      <div className="bg-[#FFFFFF] border border-[#CFC7BB] rounded-xl p-6 space-y-4 shadow-sm">
        <h2 className="text-base font-bold font-serif text-[#241B19] flex items-center gap-2">
          <Plus size={18} className="text-[#7D292D]" /> Link a New EVM Wallet
        </h2>
        <p className="text-xs text-[#82786F]">
          Ownership is cryptographically verified via a single-use server challenge signed using your browser wallet.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div>
            <label className="block text-[#82786F] mb-1 font-semibold">Wallet Provider</label>
            <select
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value as any)}
              className="w-full bg-white border border-[#CFC7BB] rounded-lg px-3 py-2 text-[#241B19]"
            >
              <option value="metamask">MetaMask</option>
              <option value="coinbase">Coinbase Wallet</option>
            </select>
          </div>

          <div>
            <label className="block text-[#82786F] mb-1 font-semibold">Assigned Role</label>
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value as any)}
              className="w-full bg-white border border-[#CFC7BB] rounded-lg px-3 py-2 text-[#241B19]"
            >
              <option value="identity">Identity Wallet</option>
              <option value="payment">Payment Wallet</option>
              <option value="receiving">Receiving Wallet</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={handleLink}
              disabled={loading}
              className="w-full py-2 bg-[#7D292D] text-[#F7F4EE] rounded-lg font-semibold hover:bg-[#612024] disabled:opacity-50 transition-colors cursor-pointer flex items-center justify-center gap-1.5"
            >
              <Wallet size={15} />
              {loading ? 'Verifying...' : 'Connect & Verify'}
            </button>
          </div>
        </div>
      </div>

      {/* 3. Linked Wallets List */}
      <div className="bg-[#FFFFFF] border border-[#CFC7BB] rounded-xl p-6 space-y-4 shadow-sm">
        <h2 className="text-base font-bold font-serif text-[#241B19]">Active Linked Wallets ({wallets.length})</h2>

        {wallets.length === 0 ? (
          <div className="p-8 text-center text-xs text-[#82786F] space-y-2">
            <Wallet className="w-8 h-8 text-[#82786F] mx-auto opacity-40" />
            <p>No EVM wallets linked yet. Connect MetaMask or Coinbase Wallet above.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {wallets.map((w) => (
              <div
                key={w.id}
                className="p-4 rounded-xl bg-[#F7F4EE] border border-[#CFC7BB] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono font-bold text-[#241B19] text-sm">
                      {w.address.slice(0, 8)}...{w.address.slice(-6)}
                    </span>
                    <button
                      onClick={() => handleCopy(w.address)}
                      className="text-[#82786F] hover:text-[#241B19] transition-colors"
                      title="Copy address"
                    >
                      {copiedAddress === w.address ? <Check size={14} className="text-[#38865B]" /> : <Copy size={14} />}
                    </button>

                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#7D292D]/15 text-[#7D292D] uppercase">
                      {w.role}
                    </span>
                    {w.is_primary && (
                      <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-[#38865B]/15 text-[#38865B]">
                        <Star size={11} fill="#38865B" /> PRIMARY
                      </span>
                    )}
                    <span className="px-2 py-0.5 rounded text-[10px] bg-[#DED8CD] text-[#241B19]">
                      {w.wallet_type}
                    </span>
                  </div>

                  <div className="text-[11px] text-[#82786F] flex items-center gap-3">
                    <span>Verified: {new Date(w.verified_at).toLocaleDateString()}</span>
                    <span>Chain: Base Sepolia ({w.chain_id})</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <select
                    value={w.role}
                    onChange={(e) => handleRoleChange(w.id, e.target.value)}
                    className="bg-white border border-[#CFC7BB] rounded px-2 py-1 text-xs text-[#241B19]"
                  >
                    <option value="identity">Identity</option>
                    <option value="payment">Payment</option>
                    <option value="receiving">Receiving</option>
                  </select>

                  {!w.is_primary && (
                    <button
                      onClick={() => handleSetPrimary(w.id)}
                      className="px-2.5 py-1 bg-white border border-[#CFC7BB] text-[#241B19] rounded hover:bg-[#DED8CD] text-xs font-semibold"
                    >
                      Set Primary
                    </button>
                  )}

                  <button
                    onClick={() => handleUnlink(w.id)}
                    className="p-1.5 text-[#B84040] hover:bg-[#B84040]/10 rounded transition-colors"
                    title="Unlink wallet"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 4. Payment Safety Boundaries Notice */}
      <div className="bg-[#FFFFFF] border border-[#CFC7BB] rounded-xl p-5 space-y-2 text-xs text-[#82786F] shadow-sm">
        <div className="flex items-center gap-2 text-[#241B19] font-bold">
          <Shield size={16} className="text-[#38865B]" />
          <span>Payment Safety Boundaries & Cryptographic Isolation</span>
        </div>
        <ul className="list-disc pl-5 space-y-1">
          <li>Linking an EVM wallet verifies address ownership only; it does not authorize payments.</li>
          <li>Every autonomous buyer agent payment requires explicit on-demand authorization via the x402 payment client.</li>
          <li>Private keys and seed phrases are never stored or transmitted.</li>
        </ul>
      </div>
    </div>
  );
};
