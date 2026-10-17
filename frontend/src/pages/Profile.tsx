import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  User, 
  ShieldCheck, 
  Wallet, 
  LogOut, 
  CheckCircle2, 
  AlertCircle,
  ArrowRight
} from 'lucide-react';

import { useAuth } from '../context/AuthContext';

export const ProfilePage: React.FC = () => {
  const { user, wallets, kycStatus, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  if (!isAuthenticated || !user) {
    return (
      <div className="max-w-3xl mx-auto py-12 px-4 space-y-6 text-center">
        <div className="bg-white border border-[#CFC7BB] rounded-xl p-8 space-y-4 shadow-sm">
          <User className="w-12 h-12 text-[#7D292D] mx-auto" />
          <h2 className="text-xl font-bold font-serif text-[#241B19]">Sign in to view your profile</h2>
          <div className="pt-2">
            <Link to="/login" className="px-5 py-2.5 bg-[#7D292D] text-[#F7F4EE] rounded-lg text-xs font-semibold hover:bg-[#612024] transition-colors">
              Sign In
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      {/* 1. Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold font-serif text-[#241B19]">Account Profile</h1>
          <p className="text-xs text-[#82786F]">Account identity, security credentials, and platform status</p>
        </div>
        <button
          onClick={handleLogout}
          className="px-4 py-2 border border-[#B84040]/40 text-[#B84040] hover:bg-[#B84040]/10 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer w-fit"
        >
          <LogOut size={15} /> Sign Out
        </button>
      </div>

      {/* 2. User Overview Card */}
      <div className="bg-[#FFFFFF] border border-[#CFC7BB] rounded-xl p-6 space-y-4 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-[#7D292D] to-[#612024] flex items-center justify-center text-[#F7F4EE] font-serif font-bold text-lg shadow-sm">
            {user.email.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <h2 className="text-base font-bold text-[#241B19]">{user.email}</h2>
            <div className="flex items-center gap-2 mt-1 text-xs">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#DED8CD] text-[#241B19] uppercase">
                {user.role}
              </span>
              {user.is_verified ? (
                <span className="flex items-center gap-1 text-[#38865B] font-semibold text-[11px]">
                  <CheckCircle2 size={13} /> Email Verified
                </span>
              ) : (
                <Link to="/verify-email" className="flex items-center gap-1 text-[#B37400] font-semibold text-[11px] underline">
                  <AlertCircle size={13} /> Verify Email
                </Link>
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3 border-t border-[#CFC7BB] text-xs font-mono">
          <div className="p-3 bg-[#F7F4EE] rounded-lg border border-[#CFC7BB]">
            <span className="text-[#82786F] block text-[10px]">User Identifier</span>
            <span className="font-semibold text-[#241B19]">{user.id}</span>
          </div>
          <div className="p-3 bg-[#F7F4EE] rounded-lg border border-[#CFC7BB]">
            <span className="text-[#82786F] block text-[10px]">Member Since</span>
            <span className="font-semibold text-[#241B19]">
              {new Date(user.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>
      </div>

      {/* 3. Linked Wallets Summary */}
      <div className="bg-[#FFFFFF] border border-[#CFC7BB] rounded-xl p-6 space-y-3 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wallet className="w-5 h-5 text-[#7D292D]" />
            <h2 className="text-base font-bold font-serif text-[#241B19]">Connected EVM Wallets</h2>
          </div>
          <Link
            to="/wallets"
            className="text-xs font-semibold text-[#7D292D] hover:underline flex items-center gap-1"
          >
            Manage Wallets <ArrowRight size={13} />
          </Link>
        </div>
        <p className="text-xs text-[#82786F]">
          You have <strong>{wallets.length}</strong> linked wallet(s). Active payment address:{' '}
          <span className="font-mono text-[#241B19] font-bold">
            {user.active_payment_wallet || 'None designated'}
          </span>
        </p>
      </div>

      {/* 4. KYC Status Card */}
      <div className="bg-[#FFFFFF] border border-[#CFC7BB] rounded-xl p-6 space-y-3 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-[#7D292D]" />
            <h2 className="text-base font-bold font-serif text-[#241B19]">Identity Verification (KYC)</h2>
          </div>
          <Link
            to="/kyc"
            className="text-xs font-semibold text-[#7D292D] hover:underline flex items-center gap-1"
          >
            KYC Console <ArrowRight size={13} />
          </Link>
        </div>
        <p className="text-xs text-[#82786F]">
          Status:{' '}
          <span className="font-mono font-bold text-[#241B19] ml-1">
            {kycStatus?.status || 'NOT_STARTED'}
          </span>{' '}
          {kycStatus?.is_simulated && (
            <span className="text-[10px] font-bold text-[#B37400] ml-1">[SIMULATED]</span>
          )}
        </p>
      </div>
    </div>
  );
};
