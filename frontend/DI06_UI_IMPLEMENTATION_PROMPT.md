# UI Implementation Prompt --- DI-06 Pay-per-Call Agent Economy

You are a senior product designer and full-stack frontend engineer
working inside our existing DI-06 hackathon repository. Implement a
polished, responsive, production-quality UI for our **Pay-per-Call Agent
Economy**. Use the attached `gemini-code-1792156032420.md` as the visual
and information-architecture reference. Recreate its design direction
and major sections, but adapt all content and interactions to our actual
solution. Do not blindly copy Agentic Market branding, example metrics,
or third-party services.

## 1. First: inspect the repository

Before editing code:

1.  Inspect the current project structure, package manager, routes,
    components, styles, API client, and environment configuration.
2.  Read the project documentation, especially:
    -   `DATABASE_SCHEMA.md`
    -   `API_CONTRACTS.md`
    -   `PAYMENT_ENGINE_IMPLEMENTATION.md`
    -   `SELLER_AGENTS_IMPLEMENTATION.md`
    -   `BUYER_AND_REGISTRY_IMPLEMENTATION.md`
    -   `LEDGER_DASHBOARD_IMPLEMENTATION.md` or the Member 4
        implementation guide if present.
3.  Identify which backend endpoints actually exist and what their
    request/response schemas are.
4.  Reuse the existing stack and conventions. Expected stack is React +
    Vite + TypeScript + Tailwind CSS with a FastAPI backend, but verify
    rather than assume.
5.  Give a short plan and list any missing API dependencies before
    implementation. Then continue with implementation; do not stop after
    planning.

**Do not replace working project configuration or rewrite the app from
scratch unless necessary.**

## 2. Product purpose and key user journey

Our app lets a buyer describe a task, set a spending budget, discover
registered seller-agent services, pay per call using the x402 payment
flow, and inspect results and payment records.

The primary user journey must be:

**Discover services → describe task and budget → inspect planned
services/costs → execute task → view results → verify ledger and
spend.**

The UI must make payment status and budget safety understandable. It
must never imply that a payment succeeded unless the backend/payment
engine reports verified settlement.

## 3. Visual direction from the reference

Create a premium developer-tool marketplace inspired by the supplied
reference:

-   Dark, high-contrast interface with near-black/charcoal backgrounds,
    subtle borders, restrained gradients, and crisp typography.
-   Compact, information-dense layouts that still have generous spacing
    and clear hierarchy.
-   A top navigation bar with product mark/name, central search, and
    clear primary action.
-   Hero area with a strong product statement, concise explanation, and
    a small set of meaningful platform metrics.
-   Interactive service explorer with search, category filters, sort,
    status/network filters where supported, and a dense directory/table
    or responsive cards.
-   Featured task workflows or example bundles.
-   A seller acquisition callout and a clean footer.
-   Subtle hover/focus states, polished empty/loading/error states, and
    responsive behavior.
-   Avoid overdone neon, excessive glassmorphism, decorative animation,
    or huge marketing copy. The product should feel credible, fast, and
    useful for developers.

Use the attached reference for layout inspiration, not as a source of
facts about our system. Never display its example volume, transaction,
buyer/seller counts, prices, service names, or claims as if they
belonged to our app.

## 4. Product identity and content

Use our project identity: **DI-06 Pay-per-Call Agent Economy**. You may
use a concise UI-facing title such as **Agent Economy** with a visible
subtitle explaining "Discover services. Pay per call. Inspect every
result."

Core product concepts: - Buyer task console - Service registry /
marketplace - Seller agents: Data, Scraping, and Inference (show only
those actually implemented) - x402 payment flow - Per-task budget and
spending - Payment ledger and settlement status - Task results and
output validation - Seller reputation / latency / outcomes when data
exists

Use accurate terminology from our API contracts. Do not invent
unsupported blockchain networks, payment currencies, service categories,
metrics, or verification badges. If Base Sepolia and USDC are configured
in this repository, show them as **testnet/demo configuration**, not as
a claim of mainnet production support.

## 5. Required screens and layout

Implement these routes or equivalent existing routes. Preserve current
routing conventions if already established.

### A. Marketplace / Home

-   Brand/logo area and navigation.
-   Search field: "Search services, capabilities, or endpoints..."
-   Main hero: explain pay-per-call service discovery and execution.
-   Small metric cards for real values only, such as registered
    services, calls processed, verified settlements, and total verified
    spend. Fetch these from an existing API if available.
-   If no metrics endpoint exists, show neutral labels such as "Live
    registry data" or omit the metric rather than fabricating numbers.
-   "Start a task" primary action.
-   Featured workflows/examples based on capabilities that exist in the
    project. Clearly label examples as examples, not live marketplace
    listings.
-   Service directory with service name, category,
    description/capability, price/price range, endpoint count if
    available, status, and supported network/token if available.
-   Filters for category, status, and sort; only include filters
    supported by the data model.
-   Pagination or "load more" for larger lists.
-   Proper no-results state.

### B. Buyer Task Console

-   Task description input.
-   Budget input with currency/token label from configuration.
-   Optional controls only if supported by the backend, such as
    preferred category or maximum calls.
-   "Plan task" / "Preview plan" action if planning is a separate API.
-   Show selected services, expected cost or price estimates, and budget
    allocation when returned by the backend.
-   Require a clear confirmation step before starting a task that can
    trigger paid calls.
-   Show progress per call and overall task status.
-   Display refusal, failure, and pending-reconciliation outcomes
    clearly.
-   Never implement payment signing or payment verification in browser
    code. Call the existing backend API.

### C. Task Results

-   Display final aggregated output and per-service outputs using the
    actual result schema.
-   Show output validation status and fallback/partial-result
    information if returned by the backend.
-   Treat service output as untrusted. Render it as text or validated
    structured data; do not inject arbitrary HTML.
-   Link each service call to its ledger detail when identifiers are
    available.

### D. Payment Ledger

-   Table/list of calls with task ID, service, amount, token, payment
    status, timestamp, and transaction hash if genuinely present.
-   Filters for status and task/service where APIs support them.
-   Detail panel/page with payment attempt status, settlement
    verification status, and safe explanation.
-   Distinguish at minimum the meanings represented by our contract:
    -   verified paid / settled
    -   payment verified but output rejected
    -   refused before payment
    -   confirmed failure with no charge
    -   pending reconciliation / uncertain outcome
-   Use the exact enum values in the contract; UI labels may be
    friendlier, but never collapse distinct statuses into one.
-   A transaction explorer link may be constructed only from a
    configured, trusted explorer base URL and a real transaction hash
    supplied by the backend.

### E. Seller Reputation / Service Detail

-   Show service description, pricing, capability metadata, and endpoint
    information from registry APIs.
-   Show calls, success/failure outcomes, latency, and reputation only
    when the backend provides enough data.
-   Include sample size and "Not enough data yet" state for new
    services.
-   Never invent review stars, verification badges, uptime, or success
    rates.

### F. Seller Tools (if supported)

-   A seller onboarding / endpoint validation page only if there are
    real backend endpoints for it.
-   Otherwise, make it a clearly labeled "Coming soon" placeholder or
    omit it. Do not present nonfunctional controls as completed
    features.

## 6. Navigation and interaction requirements

-   Suggested navigation: Marketplace, Run a Task, Ledger, Results,
    Seller Tools, Docs/About (only if real routes/content exist).
-   Global service search should filter the visible service list and
    support a keyboard shortcut if practical.
-   Every visible button must perform a real action. Do not leave
    decorative buttons that look functional.
-   Add clear focus rings and keyboard accessibility.
-   Provide loading, empty, error, retry, and success/partial-success
    states.
-   Keep filter state and selected tabs consistent with the URL if the
    project already uses URL-driven state.
-   Use toast/inline feedback for actions where helpful.
-   Prevent duplicate submissions while a request is in flight.
-   Avoid fake live tickers, fake transaction feeds, and fabricated
    real-time metrics.

## 7. Technical implementation requirements

-   TypeScript strictness: avoid `any` unless unavoidable and
    documented.
-   Reuse existing components, styles, router, and API client.
-   Create typed API functions for the endpoints that exist.
-   Keep the backend base URL in the existing environment configuration,
    such as `VITE_API_BASE_URL`; do not hardcode deployment URLs.
-   Keep secrets, signing keys, and payment credentials exclusively
    server-side.
-   Use the actual request/response schemas from backend contracts.
-   Handle network errors, non-2xx responses, invalid responses, and
    empty responses gracefully.
-   Do not silently swallow errors.
-   Avoid over-fetching and avoid repeated polling unless the API and
    task lifecycle require it.
-   If polling is required, stop when the task reaches a terminal state
    and clean up timers on route changes/unmount.
-   Do not add large UI dependencies without a clear need.
-   Keep components modular: app shell, nav, service explorer, service
    card/table, task form, plan preview, progress view, result viewer,
    ledger table/detail, reputation panel, and shared status badge.
-   Follow the project's existing lint, formatting, and build scripts.

## 8. API and backend integration policy

Before implementing each screen, map it to a real endpoint and schema.

-   Use real API data wherever available.
-   If an endpoint is not implemented yet, create a typed API boundary
    and a development-only mock only if it helps unblock UI work.
-   Any mock must be isolated behind an explicit development flag and
    must be visibly labeled "Demo data" in the UI.
-   Never mix mock records with live records.
-   Never use mocks in production builds.
-   Do not fabricate transaction hashes, settlement statuses, prices,
    service counts, or payment volume.
-   If no metrics endpoint exists, omit metrics or show a neutral empty
    state.
-   If the backend contract is unclear, preserve the existing API
    contract and report the unresolved dependency rather than guessing.

Suggested API concepts to map if present in `API_CONTRACTS.md`: -
list/search registered services - service detail - plan task -
submit/execute task - get task status - get task result - list ledger
entries - ledger entry detail - get task spend/budget summary - get
service reputation - health/readiness

These are concepts, not instructions to invent new route paths. Use the
exact routes from the repository.

## 9. Responsive design

Desktop: - Dense directory/table with aligned columns. - Main content
centered with a sensible max width. - Optional side panel for filters or
task preview when useful.

Tablet: - Preserve clear navigation and filter usability. - Collapse
secondary columns.

Mobile: - Stack cards and controls. - Make forms and buttons full-width
where appropriate. - Use horizontally scrollable tables only when
necessary. - Ensure task progress, payment status, and spend remain easy
to understand.

## 10. Trust, safety, and financial clarity

-   Treat the backend/payment engine as the source of truth for all
    payment states.
-   Distinguish reserved budget from verified spend and pending
    reconciliation.
-   Never count a pending payment as a confirmed settlement.
-   Never display a failed call as "free" unless the backend confirms no
    charge.
-   Never show a transaction as confirmed based only on HTTP success.
-   Do not expose private keys, seed phrases, authorization headers, or
    raw secrets.
-   Escape or safely render service-provided strings.
-   Display the testnet/demo environment clearly if configured for Base
    Sepolia.
-   If an operation can trigger payment, show the service,
    price/estimate, and budget impact before confirmation whenever the
    API supports it.

## 11. Suggested implementation order

Implement a working vertical slice first, then expand:

1.  Inspect repository and document the API/data model.
2.  Build the app shell, theme, navigation, and responsive layout.
3.  Connect Marketplace to the real registry endpoint.
4.  Build task creation and plan preview using the real backend.
5.  Add execution progress and task results.
6.  Add ledger and task spending views.
7.  Add service detail/reputation.
8.  Add seller tools only if supported.
9.  Add loading/error/empty states and accessibility polish.
10. Run typecheck, lint, tests, and production build. Fix actual
    failures.

## 12. Acceptance criteria

The implementation is complete only when:

-   [ ] The UI follows the supplied reference's dark
    developer-marketplace direction while using DI-06 branding and real
    project capabilities.
-   [ ] All core routes/screens render and work at desktop and mobile
    widths.
-   [ ] Marketplace displays real registry data or a clearly labeled
    empty state.
-   [ ] A buyer can enter a task and budget and invoke the existing
    planning/execution API.
-   [ ] Paid execution requires a visible confirmation step when
    applicable.
-   [ ] Results and per-call statuses match backend data.
-   [ ] Ledger and spending views use persisted backend records.
-   [ ] Verified settlement is never inferred from HTTP success.
-   [ ] Pending reconciliation remains visibly uncertain.
-   [ ] No fake transactions, fabricated metrics, or production mock
    data exist.
-   [ ] No payment secrets are shipped to the browser.
-   [ ] Every visible interactive control works or is explicitly marked
    unavailable/coming soon.
-   [ ] Typecheck, lint, tests, and production build are run; report
    their actual outcomes.
-   [ ] The final response lists files changed, routes/screens
    implemented, API endpoints used, tests run, and remaining blockers.

## 13. Final instruction

Implement the UI in the existing repository, not as a disconnected
static mockup. Make sensible design decisions without asking unnecessary
questions. Do not stop after producing a plan. If an API or backend
feature is missing, finish the UI for the working parts, clearly mark
the dependency, and report exactly what is blocked. Do not claim
functionality, tests, or deployment that you have not verified.
