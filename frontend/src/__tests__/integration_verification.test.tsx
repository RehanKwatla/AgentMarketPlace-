import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { 
  getApiBaseUrl, 
  submitBuyerTask, 
  fetchWalletBalance, 
  verifyTransaction
} from '../api/client';
import { isValidBaseSepoliaTxHash, getBaseSepoliaExplorerUrl } from '../types';

describe('Frontend Integration Verification & Safety', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sanitizes VITE_API_BASE_URL and strips accidental duplicate /api suffix', () => {
    const customEnv = {
      VITE_API_BASE_URL: 'https://agentica-backend.onrender.com/api/',
      MODE: 'production',
      PROD: true,
      DEV: false,
    };

    const url = getApiBaseUrl(customEnv);
    expect(url).toBe('https://agentica-backend.onrender.com');
  });

  it('enforces strict Base Sepolia transaction hash validation and never links rec_auth_... synthetics', () => {
    // Valid 66-character hex
    const validHash = '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef';
    expect(isValidBaseSepoliaTxHash(validHash)).toBe(true);
    expect(getBaseSepoliaExplorerUrl(validHash)).toBe(`https://sepolia.basescan.org/tx/${validHash}`);

    // Synthetics, local authorizations, and invalid strings
    expect(isValidBaseSepoliaTxHash('rec_auth_1234567890')).toBe(false);
    expect(getBaseSepoliaExplorerUrl('rec_auth_1234567890')).toBeNull();

    expect(isValidBaseSepoliaTxHash('simulated_payment_001')).toBe(false);
    expect(getBaseSepoliaExplorerUrl('simulated_payment_001')).toBeNull();

    expect(isValidBaseSepoliaTxHash(null)).toBe(false);
    expect(getBaseSepoliaExplorerUrl(null)).toBeNull();
  });

  it('submits buyer task using POST /api/v1/tasks and includes Idempotency-Key header and payload', async () => {
    let capturedUrl = '';
    let capturedHeaders: Record<string, string> = {};
    let capturedBody: any = null;

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url: any, init: any) => {
      capturedUrl = String(url);
      capturedHeaders = init?.headers || {};
      capturedBody = JSON.parse(init?.body || '{}');

      return {
        ok: true,
        status: 201,
        json: async () => ({
          task_id: 'task_mock_123',
          status: 'completed',
          task: 'Lookup ETH market price',
          budget_usdc: '0.050000',
          spent_usdc: '0.002000',
          calls: [
            {
              call_id: 'call_mock_1',
              step: 1,
              service_id: 'data_001',
              status: 'paid',
              amount_usdc: '0.002000',
              transaction_hash: 'rec_auth_abc123',
              latency_ms: 25.0
            }
          ],
          final_result: 'ETH price is $3125.50',
          is_settlement_confirmed: true
        })
      } as Response;
    });

    const res = await submitBuyerTask({
      task: 'Lookup ETH market price',
      budget_usdc: '0.050000',
      idempotency_key: 'custom_idem_test_key_001',
      execute_now: true
    });

    expect(capturedUrl).toContain('/api/v1/tasks');
    expect(capturedHeaders['Idempotency-Key']).toBe('custom_idem_test_key_001');
    expect(capturedBody.idempotency_key).toBe('custom_idem_test_key_001');

    // Both new and legacy fields are normalized
    expect(res.task_id).toBe('task_mock_123');
    expect(res.status).toBe('completed');
    expect(res.total_cost_usdc).toBe('0.002000');
    expect(res.budget_allocated_usdc).toBe('0.050000');
    expect(res.executions).toHaveLength(1);
    expect(res.executions[0].service_id).toBe('data_001');
    expect(res.final_result).toBe('ETH price is $3125.50');
  });

  it('queries wallet balance from /api/v1/wallets/{address}/balance', async () => {
    const testAddr = '0x0000000000000000000000000000000000000001';
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url: any) => {
      expect(String(url)).toContain(`/api/v1/wallets/${testAddr}/balance`);
      return {
        ok: true,
        status: 200,
        json: async () => ({
          address: testAddr,
          network: 'eip155:84532',
          chain_id: 84532,
          token: 'USDC',
          token_address: '0x036CbD53842c5426634e7929541eC2318f3dCF7e',
          balance_base_units: 50000000,
          balance_usdc: '50.000000',
          native_balance_wei: '100000000000000000',
          native_balance_eth: '0.100000',
          is_verified_onchain: true,
          source: 'rpc'
        })
      } as Response;
    });

    const bal = await fetchWalletBalance(testAddr);
    expect(bal.address).toBe(testAddr);
    expect(bal.balance_usdc).toBe('50.000000');
    expect(bal.is_verified_onchain).toBe(true);
  });

  it('queries transaction verification from /api/v1/payments/verify-tx/{txHash}', async () => {
    const dummyHash = '0x' + 'a'.repeat(64);
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (url: any) => {
      expect(String(url)).toContain(`/api/v1/payments/verify-tx/${dummyHash}`);
      return {
        ok: true,
        status: 200,
        json: async () => ({
          tx_hash: dummyHash,
          network: 'eip155:84532',
          service_id: 'data_001',
          amount_usdc: '0.002',
          amount_units: 2000,
          is_confirmed: false,
          status: 'unverified_hash',
          evidence_type: 'unverified_hash',
          explorer_url: `https://sepolia.basescan.org/tx/${dummyHash}`,
          settlement_proof: dummyHash
        })
      } as Response;
    });

    const txInfo = await verifyTransaction(dummyHash);
    expect(txInfo.tx_hash).toBe(dummyHash);
    expect(txInfo.is_confirmed).toBe(false);
    expect(txInfo.status).toBe('unverified_hash');
  });
});
