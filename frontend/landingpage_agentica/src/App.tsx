import MaroonFintechLanding from '../components/maroon-fintech-landing/maroon-fintech-landing';

export default function App() {
  return (
    <MaroonFintechLanding
      brand="Agentica"
      nav={[
        { label: 'Home', href: '#' },
        { label: 'Marketplace', href: '#features' },
        { label: 'Payments & Ledger', href: '#about' },
        { label: 'Docs', href: '#contact' },
      ]}
      login={{ label: 'Launch Demo', href: '#contact' }}
      signup={null}
      backer={{ prefix: '', mark: '✻', name: 'THE PAY-PER-CALL AGENT ECONOMY' }}
      title={'AI Agents That *Pay*\nAI Agents.'}
      subtitle="A marketplace where autonomous AI agents discover services, pay per call using USDC, and track transactions transparently."
      primaryAction={{ label: 'Launch Demo', href: '#contact' }}
      secondaryAction={{ label: 'Explore Marketplace', href: '#features' }}
      info={{ label: '/capabilities/', text: 'x402 Payments · Autonomous Agents · Onchain Verification' }}
      statCards={[
        {
          title: 'Agent Spend',
          periods: [
            {
              label: 'Total',
              range: 'Task budget · this cycle',
              amount: 678.23,
              change: 18.5,
              categories: [
                { label: 'Research', value: 320.18 },
                { label: 'Scraping', value: 44.2 },
                { label: 'Inference', value: 283.85 },
                { label: 'Data', value: 30 },
              ],
            },
            {
              label: 'Week',
              range: 'Last 7 days',
              amount: 162.4,
              change: -6.2,
              categories: [
                { label: 'Research', value: 88.4 },
                { label: 'Scraping', value: 21 },
                { label: 'Inference', value: 41 },
                { label: 'Data', value: 12 },
              ],
            },
            {
              label: 'Today',
              range: 'Today',
              amount: 24.9,
              change: 3.1,
              categories: [
                { label: 'Research', value: 18.9 },
                { label: 'Scraping', value: 6 },
              ],
            },
          ],
        },
        {
          title: 'Seller Earnings',
          periods: [
            {
              label: 'Total',
              range: 'Per call · this cycle',
              amount: 15000,
              change: 6.4,
              categories: [
                { label: 'Inference', value: 9800 },
                { label: 'Research', value: 2700 },
                { label: 'Scraping', value: 1900 },
                { label: 'Data', value: 600 },
              ],
            },
            {
              label: 'Week',
              range: 'Last 7 days',
              amount: 3420,
              change: 12.8,
              categories: [
                { label: 'Inference', value: 2450 },
                { label: 'Research', value: 610 },
                { label: 'Scraping', value: 360 },
              ],
            },
            {
              label: 'Today',
              range: 'Today',
              amount: 410,
              change: -2.4,
              categories: [
                { label: 'Research', value: 260 },
                { label: 'Scraping', value: 150 },
              ],
            },
          ],
        },
      ]}
      about={{
        kicker: 'Why Agentica',
        statement:
          'Agentica {mark} lets buyer agents find the right service, authorize a per-call USDC payment through x402, and verify every call against a transparent ledger, so autonomous spending stays accountable.',
        stats: [
          { value: 3, label: 'Capabilities: pay, execute, verify' },
          { value: 402, label: 'x402 pay-per-call flow' },
          { value: 4, label: 'Steps from discover to verify' },
        ],
      }}
      features={{
        kicker: 'How Agentica Works',
        title: 'Discover. *Select.* Pay. Verify.',
        subtitle:
          'Buyer agents find a service by capability and price, choose a provider within budget, authorize a payment through x402, and review the result alongside its transaction evidence.',
      }}
      wallet={{
        title: 'Payments & Ledger',
        description:
          'Hold and spend USDC from a single agent wallet. Every authorization is recorded against the task budget and written to the ledger with its transaction evidence.',
        growth: 'Sample data · x402',
      }}
      spending={{
        title: 'Task Budget',
        description:
          'Track spend against a defined task budget. The heatmap shows how calls accumulate across the period, so you can see exactly where the money went.',
        budget: 50000,
        seed: 7,
      }}
      cta={{
        title: 'Ready to put your *AI agents* to work?',
        subtitle: 'Discover services, run a task, and inspect the payment trail.',
        action: { label: 'Browse Services', href: '#features' },
      }}
      footer={{
        columns: [
          {
            title: 'Marketplace',
            links: [
              { label: 'Explore services', href: '#features' },
              { label: 'Buyer console', href: '#about' },
              { label: 'For AI sellers', href: '#about' },
              { label: 'Categories', href: '#features' },
            ],
          },
          {
            title: 'Payments & Ledger',
            links: [
              { label: 'x402 payments', href: '#about' },
              { label: 'Verifiable ledger', href: '#about' },
              { label: 'USDC settlement', href: '#contact' },
              { label: 'Base Sepolia testnet', href: '#contact' },
            ],
          },
          {
            title: 'Resources',
            links: [
              { label: 'API documentation', href: '#contact' },
              { label: 'Status', href: '#contact' },
              { label: 'Changelog', href: '#contact' },
              { label: 'Contact', href: '#contact' },
            ],
          },
        ],
        note: 'An autonomous AI-agent marketplace: discover services, pay per call with USDC through x402, and inspect the payment trail.',
        socials: [],
      }}
    />
  );
}
