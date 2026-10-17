/**
 * API Client for Authentication, Multi-Wallet, and KYC Endpoints.
 */
import { getApiBaseUrl } from './client';

const API_BASE_URL = getApiBaseUrl();
const apiUrl = (path: string): string => `${API_BASE_URL}${path}`;

function authHeaders(token?: string | null): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// --- Auth Endpoints ---

export async function signupApi(email: string, password: string) {
  const res = await fetch(apiUrl('/api/v1/auth/signup'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Sign-up failed');
  }
  return data;
}

export async function loginApi(email: string, password: string) {
  const res = await fetch(apiUrl('/api/v1/auth/login'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Sign-in failed');
  }
  return data;
}

export async function verifyEmailApi(token: string) {
  const res = await fetch(apiUrl('/api/v1/auth/verify-email'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Email verification failed');
  }
  return data;
}

export async function forgotPasswordApi(email: string) {
  const res = await fetch(apiUrl('/api/v1/auth/forgot-password'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Password reset request failed');
  }
  return data;
}

export async function resetPasswordApi(token: string, new_password: string) {
  const res = await fetch(apiUrl('/api/v1/auth/reset-password'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, new_password }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Password reset failed');
  }
  return data;
}

export async function logoutApi(token: string) {
  try {
    await fetch(apiUrl('/api/v1/auth/logout'), {
      method: 'POST',
      headers: authHeaders(token),
    });
  } catch (err) {
    console.warn('Logout API error:', err);
  }
}

export async function getMeApi(token: string) {
  const res = await fetch(apiUrl('/api/v1/auth/me'), {
    headers: authHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Failed to fetch user profile');
  }
  return data;
}

// --- Multi-Wallet Endpoints ---

export async function requestWalletChallengeApi(address: string, wallet_type: string = 'metamask') {
  const res = await fetch(apiUrl('/api/v1/wallets/challenge'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ address, wallet_type }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Failed to generate wallet challenge');
  }
  return data;
}

export async function linkWalletApi(
  token: string,
  payload: {
    address: string;
    signature: string;
    nonce: string;
    role: string;
    wallet_type: string;
    is_primary?: boolean;
  }
) {
  const res = await fetch(apiUrl('/api/v1/wallets/link'), {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Failed to link wallet');
  }
  return data;
}

export async function getWalletsApi(token: string) {
  const res = await fetch(apiUrl('/api/v1/wallets'), {
    headers: authHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Failed to fetch wallets');
  }
  return data;
}

export async function updateWalletApi(
  token: string,
  walletId: string,
  role?: string,
  is_primary?: boolean
) {
  const res = await fetch(apiUrl(`/api/v1/wallets/${walletId}`), {
    method: 'PATCH',
    headers: authHeaders(token),
    body: JSON.stringify({ role, is_primary }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Failed to update wallet');
  }
  return data;
}

export async function unlinkWalletApi(token: string, walletId: string) {
  const res = await fetch(apiUrl(`/api/v1/wallets/${walletId}`), {
    method: 'DELETE',
    headers: authHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Failed to unlink wallet');
  }
  return data;
}

// --- Provider-Neutral KYC Endpoints ---

export async function getKycStatusApi(token: string) {
  const res = await fetch(apiUrl('/api/v1/kyc/status'), {
    headers: authHeaders(token),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Failed to fetch KYC status');
  }
  return data;
}

export async function initiateKycApi(
  token: string,
  payload: { country?: string; account_type?: string; intended_use?: string }
) {
  const res = await fetch(apiUrl('/api/v1/kyc/initiate'), {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Failed to initiate KYC session');
  }
  return data;
}

export async function triggerMockKycDecisionApi(
  token: string,
  decision: string,
  reason?: string
) {
  const res = await fetch(apiUrl('/api/v1/kyc/mock-decision'), {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({
      event_id: `evt_sim_${Date.now()}`,
      provider_reference_id: '',
      user_id: 'me',
      decision,
      reason: reason || `Simulated transition to ${decision}`,
      timestamp: Math.floor(Date.now() / 1000),
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || 'Failed to simulate KYC decision');
  }
  return data;
}
