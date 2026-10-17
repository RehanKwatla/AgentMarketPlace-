/**
 * Authentication, Multi-Wallet, and KYC Context Provider.
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  loginApi,
  signupApi,
  logoutApi,
  getMeApi,
  verifyEmailApi,
  forgotPasswordApi,
  resetPasswordApi,
  requestWalletChallengeApi,
  linkWalletApi,
  getWalletsApi,
  updateWalletApi,
  unlinkWalletApi,
  getKycStatusApi,
  initiateKycApi,
  triggerMockKycDecisionApi,
} from '../api/auth';

export interface UserProfile {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  linked_wallets_count: number;
  active_payment_wallet?: string | null;
  kyc_status: string;
  is_kyc_simulated: boolean;
}

export interface LinkedWallet {
  id: string;
  user_id: string;
  address: string;
  role: 'identity' | 'payment' | 'receiving';
  wallet_type: 'metamask' | 'coinbase' | 'other';
  is_primary: boolean;
  network: string;
  chain_id: number;
  verified_at: string;
}

export interface KycAuditEntry {
  id: string;
  from_status: string;
  to_status: string;
  provider: string;
  provider_reference_id?: string | null;
  reason?: string | null;
  timestamp: string;
}

export interface KycStatusData {
  user_id: string;
  status: 'NOT_STARTED' | 'PENDING' | 'VERIFIED' | 'REJECTED' | 'REQUIRES_REVIEW' | 'EXPIRED';
  provider: string;
  provider_reference_id?: string | null;
  is_simulated: boolean;
  simulation_disclaimer: string;
  rejection_reasons?: string | null;
  session_url?: string | null;
  verified_at?: string | null;
  expires_at?: string | null;
  audit_history: KycAuditEntry[];
}

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  wallets: LinkedWallet[];
  kycStatus: KycStatusData | null;
  loading: boolean;
  error: string | null;
  login: (email: string, pass: string) => Promise<void>;
  signup: (email: string, pass: string) => Promise<{ verification_token?: string }>;
  logout: () => Promise<void>;
  verifyEmail: (token: string) => Promise<void>;
  forgotPassword: (email: string) => Promise<{ reset_token?: string }>;
  resetPassword: (token: string, newPass: string) => Promise<void>;
  refreshUserData: () => Promise<void>;
  connectAndLinkWallet: (
    walletType: 'metamask' | 'coinbase',
    role?: 'identity' | 'payment' | 'receiving'
  ) => Promise<LinkedWallet>;
  updateWalletRole: (walletId: string, role?: string, isPrimary?: boolean) => Promise<void>;
  unlinkWallet: (walletId: string) => Promise<void>;
  initiateKyc: (data: { country?: string; account_type?: string; intended_use?: string }) => Promise<string>;
  simulateKycDecision: (decision: string, reason?: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('agentica_auth_token'));
  const [user, setUser] = useState<UserProfile | null>(null);
  const [wallets, setWallets] = useState<LinkedWallet[]>([]);
  const [kycStatus, setKycStatus] = useState<KycStatusData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const refreshUserData = useCallback(async () => {
    if (!token) {
      setUser(null);
      setWallets([]);
      setKycStatus(null);
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const [profileData, walletsData, kycData] = await Promise.all([
        getMeApi(token),
        getWalletsApi(token),
        getKycStatusApi(token),
      ]);
      setUser(profileData);
      setWallets(walletsData);
      setKycStatus(kycData);
    } catch (err: any) {
      console.warn('Failed to load user auth data:', err);
      // If token expired or invalid, clear it
      if (err.message && (err.message.includes('401') || err.message.includes('revoked') || err.message.includes('expired'))) {
        localStorage.removeItem('agentica_auth_token');
        setToken(null);
        setUser(null);
      }
      setError(err.message || 'Authentication error');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    refreshUserData();
  }, [refreshUserData]);

  const login = async (email: string, pass: string) => {
    setError(null);
    const data = await loginApi(email, pass);
    localStorage.setItem('agentica_auth_token', data.access_token);
    setToken(data.access_token);
  };

  const signup = async (email: string, pass: string) => {
    setError(null);
    const data = await signupApi(email, pass);
    return data;
  };

  const logout = async () => {
    if (token) {
      await logoutApi(token);
    }
    localStorage.removeItem('agentica_auth_token');
    setToken(null);
    setUser(null);
    setWallets([]);
    setKycStatus(null);
  };

  const verifyEmail = async (tokenStr: string) => {
    setError(null);
    await verifyEmailApi(tokenStr);
    await refreshUserData();
  };

  const forgotPassword = async (email: string) => {
    setError(null);
    return await forgotPasswordApi(email);
  };

  const resetPassword = async (tokenStr: string, newPass: string) => {
    setError(null);
    await resetPasswordApi(tokenStr, newPass);
  };

  // Browser EVM wallet connection via window.ethereum (MetaMask / Coinbase Wallet)
  const connectAndLinkWallet = async (
    walletType: 'metamask' | 'coinbase' = 'metamask',
    role: 'identity' | 'payment' | 'receiving' = 'identity'
  ): Promise<LinkedWallet> => {
    if (!token) throw new Error('Must be logged in to link a wallet');
    if (typeof window === 'undefined' || !(window as any).ethereum) {
      throw new Error('No EVM wallet detected. Please install MetaMask or Coinbase Wallet extension.');
    }

    const ethereum = (window as any).ethereum;
    // Request accounts from wallet
    const accounts = await ethereum.request({ method: 'eth_requestAccounts' });
    if (!accounts || accounts.length === 0) {
      throw new Error('No EVM account selected in wallet');
    }
    const address = accounts[0];

    // 1. Request challenge from backend
    const challengeRes = await requestWalletChallengeApi(address, walletType);

    // 2. Request signature via personal_sign (EIP-191)
    const signature = await ethereum.request({
      method: 'personal_sign',
      params: [challengeRes.challenge_text, address],
    });

    // 3. Submit signature to link wallet
    const linked = await linkWalletApi(token, {
      address,
      signature,
      nonce: challengeRes.nonce,
      role,
      wallet_type: walletType,
      is_primary: wallets.filter((w) => w.role === role).length === 0,
    });

    await refreshUserData();
    return linked;
  };

  const updateWalletRole = async (walletId: string, role?: string, isPrimary?: boolean) => {
    if (!token) throw new Error('Must be logged in');
    await updateWalletApi(token, walletId, role, isPrimary);
    await refreshUserData();
  };

  const unlinkWallet = async (walletId: string) => {
    if (!token) throw new Error('Must be logged in');
    await unlinkWalletApi(token, walletId);
    await refreshUserData();
  };

  const initiateKyc = async (data: { country?: string; account_type?: string; intended_use?: string }) => {
    if (!token) throw new Error('Must be logged in');
    const res = await initiateKycApi(token, data);
    await refreshUserData();
    return res.session_url;
  };

  const simulateKycDecision = async (decision: string, reason?: string) => {
    if (!token) throw new Error('Must be logged in');
    await triggerMockKycDecisionApi(token, decision, reason);
    await refreshUserData();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: Boolean(user && token),
        wallets,
        kycStatus,
        loading,
        error,
        login,
        signup,
        logout,
        verifyEmail,
        forgotPassword,
        resetPassword,
        refreshUserData,
        connectAndLinkWallet,
        updateWalletRole,
        unlinkWallet,
        initiateKyc,
        simulateKycDecision,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

const defaultAuthContext: AuthContextType = {
  user: null,
  token: null,
  isAuthenticated: false,
  wallets: [],
  kycStatus: null,
  loading: false,
  error: null,
  login: async () => {},
  signup: async () => ({}),
  logout: async () => {},
  verifyEmail: async () => {},
  forgotPassword: async () => ({}),
  resetPassword: async () => {},
  refreshUserData: async () => {},
  connectAndLinkWallet: async () => { throw new Error('Wallet connection requires active browser session'); },
  updateWalletRole: async () => {},
  unlinkWallet: async () => {},
  initiateKyc: async () => '',
  simulateKycDecision: async () => {},
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  return context || defaultAuthContext;
};

