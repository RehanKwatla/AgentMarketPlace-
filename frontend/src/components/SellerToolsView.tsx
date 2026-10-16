import React, { useState } from 'react';
import { 
  ShieldCheck, 
  CheckCircle2,
  AlertCircle,
  PlusCircle
} from 'lucide-react';
import { ServiceCategory } from '../types';

export const SellerToolsView: React.FC = () => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState<ServiceCategory>('data');
  const [endpointUrl, setEndpointUrl] = useState('');
  const [priceUsdc, setPriceUsdc] = useState('0.002');
  const [payTo, setPayTo] = useState('');
  const [inputSchema, setInputSchema] = useState('{\n  "type": "object",\n  "properties": {\n    "query": { "type": "string" }\n  }\n}');
  const [outputSchema, setOutputSchema] = useState('{\n  "type": "object",\n  "properties": {\n    "result": { "type": "string" }\n  }\n}');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionFeedback, setSubmissionFeedback] = useState<{ status: 'success' | 'error'; message: string } | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmissionFeedback(null);

    // Validation
    if (!name.trim() || !endpointUrl.trim() || !payTo.trim()) {
      setSubmissionFeedback({
        status: 'error',
        message: 'Please fill in all required fields (Service Name, Endpoint URL, PayTo Address).'
      });
      return;
    }

    if (!payTo.startsWith('0x') || payTo.length !== 42) {
      setSubmissionFeedback({
        status: 'error',
        message: 'Invalid Ethereum/Base Sepolia recipient address. Must start with 0x and be 42 characters.'
      });
      return;
    }

    try {
      JSON.parse(inputSchema);
      JSON.parse(outputSchema);
    } catch {
      setSubmissionFeedback({
        status: 'error',
        message: 'Input or Output schema is not valid JSON.'
      });
      return;
    }

    setIsSubmitting(true);
    // Dynamic self-registration validation demonstration
    setTimeout(() => {
      setIsSubmitting(false);
      setSubmissionFeedback({
        status: 'success',
        message: `Service specification '${name}' successfully validated for Base Sepolia testnet. Endpoint registered in self-test environment.`
      });
    }, 600);
  };

  return (
    <div className="space-y-8">
      {/* Banner */}
      <div className="glass-panel p-8 rounded-2xl border border-slate-800 relative overflow-hidden">
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 text-xs font-mono mb-3">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Seller Onboarding & Registration</span>
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight">
            Publish & Monetize Your Agent Microservices
          </h2>
          <p className="text-slate-400 text-sm mt-2 leading-relaxed">
            Register your service endpoint in the Agentic Market. Buyers pay per invocation over standard HTTP 402 challenge flow in Base Sepolia USDC.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Registration Form */}
        <div className="lg:col-span-7 glass-panel p-6 rounded-2xl border border-slate-800 space-y-5">
          <div className="flex items-center gap-2">
            <PlusCircle className="w-4 h-4 text-blue-400" />
            <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wide">
              Service Registration & Spec Validator
            </h3>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 text-xs font-mono">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-slate-300 uppercase text-[10px] mb-1">Service Name *</label>
                <input
                  type="text"
                  placeholder="e.g. DeFi Liquidity Oracle"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-300 uppercase text-[10px] mb-1">Category *</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value as ServiceCategory)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-blue-500 capitalize"
                >
                  <option value="data">Data</option>
                  <option value="scraping">Web Scraping</option>
                  <option value="inference">AI Inference</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-slate-300 uppercase text-[10px] mb-1">Service Description</label>
              <textarea
                placeholder="Describe capabilities, data source freshness, model parameters..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full h-20 bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-blue-500 resize-none font-sans"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-slate-300 uppercase text-[10px] mb-1">Endpoint URL *</label>
                <input
                  type="url"
                  placeholder="https://api.yourdomain.com/v1/call"
                  value={endpointUrl}
                  onChange={(e) => setEndpointUrl(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-300 uppercase text-[10px] mb-1">Price Per Call (USDC) *</label>
                <input
                  type="text"
                  placeholder="0.002"
                  value={priceUsdc}
                  onChange={(e) => setPriceUsdc(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-blue-500"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-slate-300 uppercase text-[10px] mb-1">Network</label>
                <input
                  type="text"
                  value="Base Sepolia (eip155:84532)"
                  disabled
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-400"
                />
              </div>

              <div>
                <label className="block text-slate-300 uppercase text-[10px] mb-1">Seller PayTo Address *</label>
                <input
                  type="text"
                  placeholder="0x..."
                  value={payTo}
                  onChange={(e) => setPayTo(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-blue-500"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-slate-300 uppercase text-[10px] mb-1">Input Schema (JSON)</label>
                <textarea
                  value={inputSchema}
                  onChange={(e) => setInputSchema(e.target.value)}
                  className="w-full h-28 bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-300 text-[11px] focus:outline-none focus:border-blue-500 font-mono resize-none"
                />
              </div>

              <div>
                <label className="block text-slate-300 uppercase text-[10px] mb-1">Output Schema (JSON)</label>
                <textarea
                  value={outputSchema}
                  onChange={(e) => setOutputSchema(e.target.value)}
                  className="w-full h-28 bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-300 text-[11px] focus:outline-none focus:border-blue-500 font-mono resize-none"
                />
              </div>
            </div>

            {submissionFeedback && (
              <div className={`p-3 rounded-lg border flex items-center gap-2 ${
                submissionFeedback.status === 'success'
                  ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-400'
                  : 'bg-rose-950/30 border-rose-500/30 text-rose-300'
              }`}>
                {submissionFeedback.status === 'success' ? (
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                ) : (
                  <AlertCircle className="w-4 h-4 shrink-0" />
                )}
                <span>{submissionFeedback.message}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs uppercase tracking-wide transition-all shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <span>Validating Specification...</span>
              ) : (
                <span>Validate & Register Microservice</span>
              )}
            </button>
          </form>
        </div>

        {/* Integration Spec Reference */}
        <div className="lg:col-span-5 space-y-4">
          <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-3">
            <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wide">
              x402 Implementation Requirements
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              Seller agents must emit standard HTTP 402 challenge headers when called without valid authorization.
            </p>

            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-[11px] font-mono text-slate-300 space-y-2">
              <div className="text-blue-400 font-semibold">1. HTTP 402 Header Format:</div>
              <pre className="text-slate-400 text-[10px] overflow-x-auto">{`{
  "version": "2.0",
  "network": "eip155:84532",
  "token": "0x036CbD5...",
  "amount": "2000",
  "payTo": "0xSellerWallet...",
  "nonce": "nonce_abc123"
}`}</pre>
            </div>
          </div>

          <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-2 text-xs font-mono text-slate-400">
            <span className="text-white font-bold block">Developer Security Notice</span>
            <p className="font-sans text-[11px] leading-relaxed">
              Never bundle or share private keys in registration schemas. Settlement verification is performed server-to-server.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
