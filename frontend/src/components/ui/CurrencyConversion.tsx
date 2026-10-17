import React, { useCallback, useEffect, useState } from 'react';
import { Coins, RefreshCw, AlertTriangle, Info } from 'lucide-react';

interface ExchangeRateSnapshot {
  /** Fiat units per 1 USDC */
  usd: number | null;
  inr: number | null;
  source: string;
  updatedAt: string | null;
}

type ConversionState = 'idle' | 'loading' | 'ready' | 'unavailable';

interface CurrencyConversionProps {
  /** Authoritative USDC amount, in decimal string form (e.g. "0.002000"). */
  amountUsdc: string;
  /** Network identifier reported by the backend record, when known. */
  network?: string | null;
}

/** A rate older than this is surfaced as stale rather than silently trusted. */
const STALE_AFTER_MS = 6 * 60 * 60 * 1000;

function toNumber(value: unknown): number | null {
  const parsed = typeof value === 'string' ? parseFloat(value) : value;
  if (typeof parsed !== 'number' || !isFinite(parsed) || parsed <= 0) return null;
  return parsed;
}

/**
 * Reads a fiat-per-USDC rate map from a provider response without assuming a
 * single vendor schema. Returns null when no usable rate is present.
 */
function parseRateResponse(payload: any): ExchangeRateSnapshot | null {
  if (!payload || typeof payload !== 'object') return null;

  const map = payload.rates || payload.data?.rates || payload.conversion_rates || payload;
  const usd = toNumber(map?.USD ?? map?.usd);
  const inr = toNumber(map?.INR ?? map?.inr);

  if (usd === null && inr === null) return null;

  return {
    usd,
    inr,
    source: String(payload.source || payload.provider || payload.data?.source || 'configured rate endpoint'),
    updatedAt: String(
      payload.updated_at || payload.timestamp || payload.date || payload.data?.updated_at || '',
    ) || null,
  };
}

/**
 * Compact USDC -> fiat display conversion.
 *
 * The rate is never hardcoded and never assumed: it is only shown when a real
 * provider response is available. The original USDC amount always remains the
 * authoritative figure, and the converted value is explicitly an estimate that
 * does not represent an on-chain swap.
 */
export const CurrencyConversion: React.FC<CurrencyConversionProps> = ({ amountUsdc, network }) => {
  const [state, setState] = useState<ConversionState>('idle');
  const [rate, setRate] = useState<ExchangeRateSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  const rateEndpoint: string | undefined = (import.meta as any).env?.VITE_EXCHANGE_RATE_URL;

  const loadRate = useCallback(async () => {
    if (!rateEndpoint) {
      setState('unavailable');
      setRate(null);
      setError('No exchange-rate provider is configured for this deployment.');
      return;
    }

    setState('loading');
    setError(null);
    try {
      const res = await fetch(rateEndpoint, { headers: { Accept: 'application/json' } });
      if (!res.ok) throw new Error(`Rate provider responded with HTTP ${res.status}`);
      const parsed = parseRateResponse(await res.json());
      if (!parsed) throw new Error('Rate provider response did not contain a usable USD or INR rate.');
      setRate(parsed);
      setState('ready');
    } catch (err: any) {
      setRate(null);
      setState('unavailable');
      setError(err?.message || 'Exchange-rate lookup failed.');
    }
  }, [rateEndpoint]);

  useEffect(() => {
    loadRate();
  }, [loadRate]);

  const amount = parseFloat(amountUsdc || '0');
  const hasAmount = isFinite(amount) && amount > 0;

  const updatedAtMs = rate?.updatedAt ? new Date(rate.updatedAt).getTime() : NaN;
  const isStale = isFinite(updatedAtMs) && Date.now() - updatedAtMs > STALE_AFTER_MS;

  const formatConverted = (value: number, currency: 'USD' | 'INR') =>
    new Intl.NumberFormat(currency === 'INR' ? 'en-IN' : 'en-US', {
      style: 'currency',
      currency,
      maximumFractionDigits: currency === 'INR' ? 4 : 6,
    }).format(value);

  return (
    <div className="p-4 rounded-xl bg-[#FFFFFF] border border-[#CFC7BB] space-y-3 shadow-xs">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Coins className="w-3.5 h-3.5 text-[#7D292D]" />
          <span className="text-[11px] font-mono font-semibold text-[#241B19] uppercase tracking-wider">
            Display Conversion
          </span>
        </div>

        {rateEndpoint && (
          <button
            type="button"
            onClick={loadRate}
            disabled={state === 'loading'}
            className="text-[10px] font-mono text-[#82786F] hover:text-[#7D292D] flex items-center gap-1 transition-colors cursor-pointer disabled:opacity-50"
            title="Re-request the latest published rate"
          >
            <RefreshCw className={`w-3 h-3 ${state === 'loading' ? 'animate-spin' : ''}`} />
            <span>{state === 'loading' ? 'Fetching' : 'Refresh rate'}</span>
          </button>
        )}
      </div>

      {/* Authoritative amount always preserved in USDC */}
      <div className="flex items-baseline justify-between gap-3 font-mono">
        <span className="text-[11px] text-[#82786F]">Recorded amount (authoritative)</span>
        <span className="text-sm font-bold text-[#7D292D]">
          {hasAmount ? `${amountUsdc} USDC` : '— USDC'}
        </span>
      </div>

      {state === 'loading' && (
        <div className="space-y-2">
          <div className="skeleton-block h-3.5 w-full" />
          <div className="skeleton-block h-3.5 w-2/3" />
        </div>
      )}

      {state === 'ready' && rate && (
        <div className="space-y-2">
          {rate.usd !== null && (
            <div className="flex items-baseline justify-between gap-3 font-mono">
              <span className="text-[11px] text-[#82786F]">Estimated USD</span>
              <span className="text-sm font-semibold text-[#241B19]">
                {hasAmount ? `≈ ${formatConverted(amount * rate.usd, 'USD')}` : '—'}
              </span>
            </div>
          )}
          {rate.inr !== null && (
            <div className="flex items-baseline justify-between gap-3 font-mono">
              <span className="text-[11px] text-[#82786F]">Estimated INR</span>
              <span className="text-sm font-semibold text-[#241B19]">
                {hasAmount ? `≈ ${formatConverted(amount * rate.inr, 'INR')}` : '—'}
              </span>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] font-mono text-[#82786F] pt-1 border-t border-[#CFC7BB]/60">
            <span>Source: {rate.source}</span>
            <span>
              Updated: {rate.updatedAt && isFinite(updatedAtMs) ? new Date(updatedAtMs).toLocaleString() : 'not reported'}
            </span>
          </div>

          {isStale && (
            <div className="p-2 rounded-lg bg-[#FBF2E5] border border-[#E8CEA7] text-[#A86E24] text-[10px] font-mono flex items-start gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>Rate may be stale — last update was more than 6 hours ago.</span>
            </div>
          )}
        </div>
      )}

      {state === 'unavailable' && (
        <div className="p-3 rounded-lg bg-[#DED8CD]/50 border border-[#CFC7BB] space-y-1">
          <div className="flex items-center gap-1.5 text-[11px] font-mono font-semibold text-[#82786F]">
            <AlertTriangle className="w-3.5 h-3.5 text-[#A86E24]" />
            <span>Conversion unavailable</span>
          </div>
          <p className="text-[10px] font-mono text-[#82786F] leading-relaxed">
            {error}{' '}
            {!rateEndpoint && 'Set VITE_EXCHANGE_RATE_URL to enable a live fiat estimate. '}
            The USDC amount above remains the authoritative recorded value.
          </p>
        </div>
      )}

      <p className="text-[10px] font-mono text-[#82786F] leading-relaxed flex items-start gap-1.5">
        <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
        <span>
          Estimate only. This is a display conversion on {network || 'the recorded network'} — it is not an on-chain currency swap and settles nothing.
        </span>
      </p>
    </div>
  );
};

export default CurrencyConversion;
