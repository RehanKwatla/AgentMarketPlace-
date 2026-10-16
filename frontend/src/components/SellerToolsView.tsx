import React from 'react';
import { 
  Code,
  CheckCircle2
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
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[rgba(120,160,153,0.16)] pb-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-[#F4F7F6] tracking-tight">
            Seller Tools & Registration
          </h1>
          <p className="text-xs text-[#A0AAA7] mt-0.5">
            Register microservice endpoints supporting the x402 v2 challenge flow on Base Sepolia.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Registration Form */}
        <div className="lg:col-span-7 bg-[#101514] p-5 rounded-xl border border-[rgba(120,160,153,0.16)] space-y-4">
          <div className="flex items-center gap-2">
            <Code className="w-4 h-4 text-[#36D6C8]" />
            <h2 className="text-xs font-semibold text-[#F4F7F6]">
              Service Registration & Spec Validator
            </h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[#A0AAA7] text-xs font-medium mb-1">Service Name *</label>
                <input
                  type="text"
                  placeholder="e.g. DeFi Liquidity Oracle"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-[#0D1111] border border-[rgba(120,160,153,0.20)] rounded-lg p-2.5 text-[#F4F7F6] placeholder-[#6F7C78] focus:outline-none focus:border-[#36D6C8] font-sans"
                  required
                />
              </div>

              <div>
                <label className="block text-[#A0AAA7] text-xs font-medium mb-1">Category *</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value as ServiceCategory)}
                  className="w-full bg-[#0D1111] border border-[rgba(120,160,153,0.20)] rounded-lg p-2.5 text-[#F4F7F6] focus:outline-none focus:border-[#36D6C8] font-sans capitalize"
                >
                  <option value="data">Data</option>
                  <option value="scraping">Web Scraping</option>
                  <option value="inference">AI Inference</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-[#A0AAA7] text-xs font-medium mb-1">Description</label>
              <textarea
                placeholder="Brief summary of capabilities and data source..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full h-18 bg-[#0D1111] border border-[rgba(120,160,153,0.20)] rounded-lg p-2.5 text-[#F4F7F6] placeholder-[#6F7C78] focus:outline-none focus:border-[#36D6C8] resize-none font-sans text-xs"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[#A0AAA7] text-xs font-medium mb-1">Endpoint URL *</label>
                <input
                  type="url"
                  placeholder="https://api.domain.com/v1/endpoint"
                  value={endpointUrl}
                  onChange={(e) => setEndpointUrl(e.target.value)}
                  className="w-full bg-[#0D1111] border border-[rgba(120,160,153,0.20)] rounded-lg p-2.5 text-[#F4F7F6] placeholder-[#6F7C78] focus:outline-none focus:border-[#36D6C8] font-mono text-[11px]"
                  required
                />
              </div>

              <div>
                <label className="block text-[#A0AAA7] text-xs font-medium mb-1">Price Per Call (USDC) *</label>
                <input
                  type="text"
                  placeholder="0.002"
                  value={priceUsdc}
                  onChange={(e) => setPriceUsdc(e.target.value)}
                  className="w-full bg-[#0D1111] border border-[rgba(120,160,153,0.20)] rounded-lg p-2.5 text-[#F4F7F6] placeholder-[#6F7C78] focus:outline-none focus:border-[#36D6C8] font-mono text-[11px]"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[#A0AAA7] text-xs font-medium mb-1">Network</label>
                <input
                  type="text"
                  value="Base Sepolia (eip155:84532)"
                  disabled
                  className="w-full bg-[#141A19] border border-[rgba(120,160,153,0.14)] rounded-lg p-2.5 text-[#A0AAA7] font-mono text-[11px]"
                />
              </div>

              <div>
                <label className="block text-[#A0AAA7] text-xs font-medium mb-1">PayTo Recipient Address *</label>
                <input
                  type="text"
                  placeholder="0x..."
                  value={payTo}
                  onChange={(e) => setPayTo(e.target.value)}
                  className="w-full bg-[#0D1111] border border-[rgba(120,160,153,0.20)] rounded-lg p-2.5 text-[#F4F7F6] placeholder-[#6F7C78] focus:outline-none focus:border-[#36D6C8] font-mono text-[11px]"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[#A0AAA7] text-xs font-medium mb-1">Input Schema (JSON)</label>
                <textarea
                  value={inputSchema}
                  onChange={(e) => setInputSchema(e.target.value)}
                  className="w-full h-24 bg-[#0D1111] border border-[rgba(120,160,153,0.20)] rounded-lg p-2.5 text-[#F4F7F6] text-[11px] focus:outline-none focus:border-[#36D6C8] font-mono resize-none"
                />
              </div>

              <div>
                <label className="block text-[#A0AAA7] text-xs font-medium mb-1">Output Schema (JSON)</label>
                <textarea
                  value={outputSchema}
                  onChange={(e) => setOutputSchema(e.target.value)}
                  className="w-full h-24 bg-[#0D1111] border border-[rgba(120,160,153,0.20)] rounded-lg p-2.5 text-[#F4F7F6] text-[11px] focus:outline-none focus:border-[#36D6C8] font-mono resize-none"
                />
              </div>
            </div>

            {submissionFeedback && (
              <div className={`p-3 rounded-lg border text-xs ${
                submissionFeedback.status === 'success'
                  ? 'bg-[rgba(66,201,149,0.08)] border-[rgba(66,201,149,0.25)] text-[#42C995]'
                  : 'bg-[rgba(225,109,109,0.08)] border-[rgba(225,109,109,0.25)] text-[#E16D6D]'
              }`}>
                {submissionFeedback.message}
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 rounded-lg bg-[#36D6C8] hover:bg-[#53E3D6] text-[#0B0D0D] font-medium text-xs transition-colors cursor-pointer"
            >
              {isSubmitting ? 'Validating Specification...' : 'Register Microservice'}
            </button>
          </form>
        </div>

        {/* Integration Spec Reference */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-[#101514] p-5 rounded-xl border border-[rgba(120,160,153,0.16)] space-y-3">
            <h2 className="text-xs font-semibold text-[#F4F7F6]">
              x402 Protocol Specification
            </h2>
            <p className="text-xs text-[#A0AAA7] leading-relaxed">
              When unauthenticated requests arrive, sellers respond with HTTP 402 and the payment requirement header.
            </p>

            <div className="bg-[#0D1111] p-3 rounded-lg border border-[rgba(120,160,153,0.16)] text-xs space-y-1.5">
              <div className="text-[#36D6C8] font-medium text-[11px]">X-402-Requirement Header:</div>
              <pre className="text-[#A0AAA7] text-[10px] font-mono overflow-x-auto leading-relaxed">{`{
  "version": "2.0",
  "network": "eip155:84532",
  "token": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
  "amount": "2000",
  "payTo": "0xSellerWallet...",
  "nonce": "e81d77a94f6c49"
}`}</pre>
            </div>

            <div className="pt-2 text-xs text-[#A0AAA7] space-y-1.5">
              <div className="flex items-center gap-1.5 text-[#42C995] font-medium text-xs">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Base Sepolia Verified Facilitator</span>
              </div>
              <p className="text-xs leading-relaxed">
                Settlement proofs are submitted back with HTTP 200 upon verifying buyer EIP-712 payment authorization payloads.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
