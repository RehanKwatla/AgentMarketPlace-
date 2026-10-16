import React from 'react';
import { 
  ShieldCheck, 
  Code
} from 'lucide-react';
import { ServiceCategory } from '../types';

export const SellerToolsView: React.FC = () => {
  const [name, setName] = React.useState('');
  const [description, setDescription] = React.useState('');
  const [category, setCategory] = React.useState<ServiceCategory>('data');
  const [endpointUrl, setEndpointUrl] = React.useState('');
  const [priceUsdc, setPriceUsdc] = React.useState('0.002');
  const [payTo, setPayTo] = React.useState('');
  const [inputSchema, setInputSchema] = React.useState('{\n  "type": "object",\n  "properties": {\n    "query": { "type": "string" }\n  }\n}');
  const [outputSchema, setOutputSchema] = React.useState('{\n  "type": "object",\n  "properties": {\n    "result": { "type": "string" }\n  }\n}');
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [submissionFeedback, setSubmissionFeedback] = React.useState<{ status: 'success' | 'error'; message: string } | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmissionFeedback(null);

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
    setTimeout(() => {
      setIsSubmitting(false);
      setSubmissionFeedback({
        status: 'success',
        message: `Service specification '${name}' successfully validated for Base Sepolia testnet.`
      });
    }, 500);
  };

  return (
    <div className="space-y-6">
      {/* Banner */}
      <div className="bg-[#171819] p-6 rounded-lg border border-[#303133]">
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded bg-[#FF982E]/10 text-[#FF982E] border border-[#FF982E]/30 text-xs font-mono mb-2">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Seller Onboarding & Registration</span>
          </div>
          <h2 className="text-xl font-bold text-[#F5F5F5] font-sans">
            Register Autonomous Microservices
          </h2>
          <p className="text-[#A0A1A5] text-xs mt-1 leading-relaxed font-sans">
            Expose endpoints to autonomous buyer agents using the standardized x402 v2 challenge flow on Base Sepolia.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Registration Form */}
        <div className="lg:col-span-7 bg-[#171819] p-5 rounded-lg border border-[#303133] space-y-4">
          <div className="flex items-center gap-2">
            <Code className="w-4 h-4 text-[#FF982E]" />
            <h3 className="text-xs font-bold text-[#F5F5F5] font-mono uppercase tracking-wide">
              Service Registration & Spec Validator
            </h3>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3 text-xs font-mono">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[#777980] uppercase text-[10px] mb-1">Service Name *</label>
                <input
                  type="text"
                  placeholder="e.g. DeFi Liquidity Oracle"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-[#101112] border border-[#303133] rounded p-2 text-[#F5F5F5] focus:outline-none focus:border-[#FF982E]"
                  required
                />
              </div>

              <div>
                <label className="block text-[#777980] uppercase text-[10px] mb-1">Category *</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value as ServiceCategory)}
                  className="w-full bg-[#101112] border border-[#303133] rounded p-2 text-[#F5F5F5] focus:outline-none focus:border-[#FF982E] capitalize"
                >
                  <option value="data">Data</option>
                  <option value="scraping">Web Scraping</option>
                  <option value="inference">AI Inference</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-[#777980] uppercase text-[10px] mb-1">Service Description</label>
              <textarea
                placeholder="Describe capabilities, data source freshness, model parameters..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full h-18 bg-[#101112] border border-[#303133] rounded p-2 text-[#F5F5F5] focus:outline-none focus:border-[#FF982E] resize-none font-sans"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[#777980] uppercase text-[10px] mb-1">Endpoint URL *</label>
                <input
                  type="url"
                  placeholder="https://api.yourdomain.com/v1/call"
                  value={endpointUrl}
                  onChange={(e) => setEndpointUrl(e.target.value)}
                  className="w-full bg-[#101112] border border-[#303133] rounded p-2 text-[#F5F5F5] focus:outline-none focus:border-[#FF982E]"
                  required
                />
              </div>

              <div>
                <label className="block text-[#777980] uppercase text-[10px] mb-1">Price Per Call (USDC) *</label>
                <input
                  type="text"
                  placeholder="0.002"
                  value={priceUsdc}
                  onChange={(e) => setPriceUsdc(e.target.value)}
                  className="w-full bg-[#101112] border border-[#303133] rounded p-2 text-[#F5F5F5] focus:outline-none focus:border-[#FF982E]"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[#777980] uppercase text-[10px] mb-1">Network</label>
                <input
                  type="text"
                  value="Base Sepolia (eip155:84532)"
                  disabled
                  className="w-full bg-[#111214] border border-[#303133] rounded p-2 text-[#777980]"
                />
              </div>

              <div>
                <label className="block text-[#777980] uppercase text-[10px] mb-1">Seller PayTo Address *</label>
                <input
                  type="text"
                  placeholder="0x..."
                  value={payTo}
                  onChange={(e) => setPayTo(e.target.value)}
                  className="w-full bg-[#101112] border border-[#303133] rounded p-2 text-[#F5F5F5] focus:outline-none focus:border-[#FF982E]"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[#777980] uppercase text-[10px] mb-1">Input Schema (JSON)</label>
                <textarea
                  value={inputSchema}
                  onChange={(e) => setInputSchema(e.target.value)}
                  className="w-full h-24 bg-[#111214] border border-[#303133] rounded p-2 text-[#E6E6E6] text-[11px] focus:outline-none focus:border-[#FF982E] font-mono resize-none"
                />
              </div>

              <div>
                <label className="block text-[#777980] uppercase text-[10px] mb-1">Output Schema (JSON)</label>
                <textarea
                  value={outputSchema}
                  onChange={(e) => setOutputSchema(e.target.value)}
                  className="w-full h-24 bg-[#111214] border border-[#303133] rounded p-2 text-[#E6E6E6] text-[11px] focus:outline-none focus:border-[#FF982E] font-mono resize-none"
                />
              </div>
            </div>

            {submissionFeedback && (
              <div className={`p-2.5 rounded border text-xs ${
                submissionFeedback.status === 'success'
                  ? 'bg-[#58B779]/10 border-[#58B779]/30 text-[#58B779]'
                  : 'bg-[#E15D52]/10 border-[#E15D52]/30 text-[#E15D52]'
              }`}>
                {submissionFeedback.message}
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 rounded bg-[#FF982E] hover:bg-[#E98522] text-[#101112] font-bold text-xs uppercase tracking-wide transition-all shadow-sm shadow-[#FF982E]/30"
            >
              {isSubmitting ? 'Validating Specification...' : 'Validate & Register Microservice'}
            </button>
          </form>
        </div>

        {/* Integration Spec Reference */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-[#171819] p-5 rounded-lg border border-[#303133] space-y-3">
            <h3 className="text-xs font-bold text-[#F5F5F5] font-mono uppercase tracking-wide">
              x402 Implementation Requirements
            </h3>
            <p className="text-xs text-[#A0A1A5] leading-relaxed font-sans">
              Seller agents must emit standard HTTP 402 challenge headers when called without valid authorization.
            </p>

            <div className="bg-[#111214] p-3 rounded border border-[#303133] text-[11px] font-mono text-[#E6E6E6] space-y-1.5">
              <div className="text-[#FF982E] font-semibold text-[10px] uppercase">HTTP 402 Header Format:</div>
              <pre className="text-[#A0A1A5] text-[10px] overflow-x-auto">{`{
  "version": "2.0",
  "network": "eip155:84532",
  "token": "0x036CbD5...",
  "amount": "2000",
  "payTo": "0xSellerWallet...",
  "nonce": "nonce_abc123"
}`}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
