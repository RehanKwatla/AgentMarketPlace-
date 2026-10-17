"use client"

// Maroon Fintech Landing — a complete finance-SaaS landing page in one file.
// A maroon frame holds a cream hero: a pill nav with a fold-out menu, a
// "backed by" badge, a two-tone headline and a sage-green device that tilts
// under the pointer while signals run toward it along a circuit board. Live
// expense and income cards sit at its feet. Below, a dark "about" statement
// lights up word by word as you scroll, stats count up, and a satin-lit feature
// panel shows a multi-currency wallet and a profit & loss heatmap you can use.
// A call to action, a request-demo dialog and a footer finish the page.
//
// Everything is drawn here: the device, the circuit, the satin, the flags and
// the charts are SVG; the type is the system stack; nothing loads at runtime.
import * as React from "react"
import { useNavigate } from "react-router-dom"

export type MflLink = { label: string; href?: string }

export type MflCategory = { label: string; value: number; color?: string }

export type MflPeriod = {
  /** Shown in the card's period menu, e.g. "Month". */
  label: string
  /** The date range under the title. */
  range: string
  amount: number
  /** Percent versus the previous period. Negative shows a falling arrow. */
  change: number
  categories: MflCategory[]
}

export type MflStatCard = { title: string; periods: MflPeriod[] }

export type MflStat = { value: number; prefix?: string; suffix?: string; decimals?: number; label: string }

export type MflWallet = {
  /** ISO code: USD, EUR, KRW, IDR, GBP and JPY get a drawn flag. */
  code: string
  symbol: string
  balance: number
  /** Units of this currency per one US dollar. Used to total the wallets. */
  perUsd: number
  active?: boolean
}

export type MflPaletteName = "maroon" | "forest" | "midnight"

export type MflPalette = {
  frame: string
  paper: string
  ink: string
  muted: string
  brand: string
  night: string
  card: string
  cream: string
  device: string
  glow: string
  /** The satin behind the feature panel: shadow, sheen and highlight. */
  satin: [string, string, string]
}

export type MflDemoRequest = { name: string; email: string; company: string; size: string }

export interface MaroonFintechLandingProps {
  /** Brand name. A trailing "." is drawn as part of the wordmark. */
  brand?: string
  /** Replaces the drawn asterisk mark beside the brand. */
  logo?: React.ReactNode
  /** Links in the fold-out menu. `#about`, `#features`, `#contact` scroll in-page. */
  nav?: MflLink[]
  login?: MflLink | null
  signup?: MflLink | null
  /** The badge above the headline. `null` hides it. */
  backer?: { prefix?: string; name: string; mark?: string } | null
  /** Wrap words in *asterisks* to mute them. "\n" breaks the line. */
  title?: string
  subtitle?: string
  primaryAction?: MflLink
  /** Without an href this opens the request-demo dialog. */
  secondaryAction?: MflLink
  /** Bottom-left block in the hero. *Asterisks* mute the tail. */
  info?: { label?: string; text: string } | null
  /** The two dark cards at the hero's feet. Each has periods you can switch between. */
  statCards?: MflStatCard[]
  /** `{mark}` in the statement places the three-tile mark inline. *Asterisks* are ignored here. */
  about?: { kicker?: string; statement: string; stats?: MflStat[] } | null
  features?: { kicker?: string; title: string; subtitle?: string } | null
  wallet?: { title?: string; description?: string; wallets?: MflWallet[]; growth?: string } | null
  spending?: { title?: string; description?: string; budget?: number; seed?: number; months?: number[][] } | null
  cta?: { title: string; subtitle?: string; action?: MflLink } | null
  footer?: { columns?: { title: string; links: MflLink[] }[]; note?: string; socials?: MflLink[] } | null
  palette?: MflPaletteName | MflPaletteInput
  /** Called with the dialog's fields. Return (or resolve to) `false`, or throw, to show an error. */
  onRequestDemo?: (data: MflDemoRequest) => unknown
  /** Minimum height of the hero. A definite length, so it survives any host layout. */
  height?: string
  className?: string
}

export type MflPaletteInput = {
  frame?: string
  paper?: string
  ink?: string
  muted?: string
  brand?: string
  night?: string
  card?: string
  cream?: string
  device?: string
  glow?: string
  satin?: [string, string, string]
}

// #region content
const PALETTES = {
  maroon: {
    frame: "#7a2e33",
    paper: "#e7e2d8",
    ink: "#1c1412",
    muted: "#8c8279",
    brand: "#7a2a2e",
    night: "#2a1411",
    card: "#3b1816",
    cream: "#efe9df",
    device: "#97a18e",
    glow: "#ffc46b",
    satin: ["#24100d", "#8a5a3e", "#f2dfc1"] as [string, string, string],
  },
  forest: {
    frame: "#2f4436",
    paper: "#e5e4da",
    ink: "#141a16",
    muted: "#7f857b",
    brand: "#2f5640",
    night: "#121d17",
    card: "#1c2c22",
    cream: "#ecebe1",
    device: "#c9b79a",
    glow: "#ffd98a",
    satin: ["#0d1712", "#4f6b4f", "#e6e4c8"] as [string, string, string],
  },
  midnight: {
    frame: "#26324f",
    paper: "#e4e3e0",
    ink: "#12141c",
    muted: "#7c7f89",
    brand: "#2b3d6b",
    night: "#10141f",
    card: "#1b2236",
    cream: "#eceae6",
    device: "#a7a9b2",
    glow: "#8fd0ff",
    satin: ["#0b1020", "#46557f", "#dde3f2"] as [string, string, string],
  },
}

const DEFAULT_NAV: MflLink[] = [
  { label: "Overview", href: "#about" },
  { label: "Architecture", href: "#features" },
  { label: "Marketplace", href: "/marketplace" },
  { label: "Buyer Console", href: "/buyer" },
  { label: "Ledger", href: "/ledger" },
  { label: "Docs", href: "/docs" },
]

const CAT_COLORS = ["#efe9df", "#b8a99a", "#c4673f", "#7b6a5f", "#d9b48a"]

const DEFAULT_CARDS: MflStatCard[] = [
  {
    title: "Task Spending (USDC)",
    periods: [
      {
        label: "Total",
        range: "Feb 01, 2025 - Feb 28, 2025",
        amount: 678.23,
        change: 18.5,
        categories: [
          { label: "Web Scraping & Search", value: 320.18 },
          { label: "Sentiment & NLP", value: 44.2 },
          { label: "Code & Contract Auditing", value: 283.85 },
          { label: "Data Synthesis", value: 30 },
        ],
      },
      {
        label: "Week",
        range: "Feb 22, 2025 - Feb 28, 2025",
        amount: 162.4,
        change: -6.2,
        categories: [
          { label: "Web Scraping & Search", value: 88.4 },
          { label: "Sentiment & NLP", value: 21 },
          { label: "Code Auditing", value: 41 },
          { label: "Data Synthesis", value: 12 },
        ],
      },
      {
        label: "Today",
        range: "Feb 28, 2025",
        amount: 24.9,
        change: 3.1,
        categories: [
          { label: "Web Scraping & Search", value: 18.9 },
          { label: "Sentiment & NLP", value: 6 },
        ],
      },
    ],
  },
  {
    title: "Seller Service Volume",
    periods: [
      {
        label: "Total",
        range: "Feb 01, 2025 - Feb 28, 2025",
        amount: 15000,
        change: 6.4,
        categories: [
          { label: "LLM Reasoning APIs", value: 9800 },
          { label: "Market Data Feeds", value: 2700 },
          { label: "Vision & OCR Parsing", value: 1900 },
          { label: "Code Execution Sandboxes", value: 600 },
        ],
      },
      {
        label: "Week",
        range: "Feb 22, 2025 - Feb 28, 2025",
        amount: 3420,
        change: 12.8,
        categories: [
          { label: "LLM Reasoning APIs", value: 2450 },
          { label: "Market Data Feeds", value: 610 },
          { label: "Vision & OCR Parsing", value: 360 },
        ],
      },
      {
        label: "Today",
        range: "Feb 28, 2025",
        amount: 410,
        change: -2.4,
        categories: [
          { label: "Market Data Feeds", value: 260 },
          { label: "Vision & OCR Parsing", value: 150 },
        ],
      },
    ],
  },
]

const DEFAULT_STATS: MflStat[] = [
  { value: 50, suffix: "+", label: "Registered Agent Services" },
  { value: 99, suffix: ".8%", label: "x402 Settlement Success" },
  { value: 240, suffix: "ms", label: "Average Execution Latency" },
]

const DEFAULT_WALLETS: MflWallet[] = [
  { code: "USD", symbol: "$", balance: 24850, perUsd: 1, active: true },
  { code: "EUR", symbol: "€ ", balance: 14200.45, perUsd: 0.92, active: true },
  { code: "GBP", symbol: "£", balance: 8940.5, perUsd: 0.79, active: true },
  { code: "JPY", symbol: "¥", balance: 3450000, perUsd: 151, active: true },
  { code: "KRW", symbol: "₩ ", balance: 38253120, perUsd: 1380, active: false },
  { code: "IDR", symbol: "Rp ", balance: 309640000, perUsd: 16250, active: false },
]

const DEFAULT_FOOTER = {
  columns: [
    { 
      title: "Platform", 
      links: [
        { label: "Dashboard", href: "/dashboard" }, 
        { label: "Marketplace", href: "/marketplace" }, 
        { label: "Buyer Console", href: "/buyer" }, 
        { label: "Agent Execution", href: "/execution" }
      ] 
    },
    { 
      title: "Protocol", 
      links: [
        { label: "Settlement Ledger", href: "/ledger" }, 
        { label: "Payment Engine", href: "/payments" }, 
        { label: "Architecture", href: "/about" }, 
        { label: "Documentation", href: "/docs" }
      ] 
    },
    { 
      title: "Developers", 
      links: [
        { label: "Seller Tools", href: "/seller" }, 
        { label: "Analytics", href: "/analytics" }, 
        { label: "API Reference", href: "/docs" }, 
        { label: "Base Sepolia Explorer", href: "https://sepolia.basescan.org" }
      ] 
    },
  ],
  note: "Agentica Protocol • Base Sepolia EIP-712 Micro-settlement Engine.",
  socials: [
    { label: "Console", href: "/dashboard" },
    { label: "Docs", href: "/docs" },
    { label: "Marketplace", href: "/marketplace" }
  ],
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
const SPAN_LABELS = ["Yearly", "Half-year", "Quarter"]
const SPAN_MONTHS = [12, 6, 3]
// #endregion content

// #region logic
type Seg = { text: string; muted: boolean }

// "Smarter *Financial*" → [{Smarter, false}, {Financial, true}]. An unclosed
// asterisk mutes the rest of the string, which is what a writer means by it.
function parseEmphasis(s: string): Seg[] {
  const out: Seg[] = []
  let muted = false
  for (const part of s.split("*")) {
    if (part) out.push({ text: part, muted })
    muted = !muted
  }
  return out
}

function clamp(v: number, lo: number, hi: number): number {
  return v < lo ? lo : v > hi ? hi : v
}

function formatMoney(n: number, symbol: string, decimals: number): string {
  const fixed = Math.abs(n).toFixed(decimals)
  const dot = fixed.indexOf(".")
  const int = dot < 0 ? fixed : fixed.slice(0, dot)
  const frac = dot < 0 ? "" : fixed.slice(dot)
  return (n < 0 ? "-" : "") + symbol + int.replace(/\B(?=(\d{3})+(?!\d))/g, ",") + frac
}

// Currencies whose minor unit nobody uses.
function decimalsFor(code: string): number {
  return code === "KRW" || code === "JPY" || code === "IDR" ? 0 : 2
}

function formatCount(n: number, decimals: number): string {
  return formatMoney(n, "", decimals)
}

function easeOutCubic(t: number): number {
  const u = 1 - clamp(t, 0, 1)
  return 1 - u * u * u
}

function mulberry32(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

// Donut arcs in pathLength=100 units. Each arc gives up `gap` so neighbours
// never touch; an arc smaller than the gap still shows as a sliver.
function donutArcs(values: number[], gap: number): { start: number; len: number }[] {
  const total = values.reduce((a, v) => a + Math.max(0, v), 0)
  if (!total) return values.map(() => ({ start: 0, len: 0 }))
  const g = values.filter((v) => v > 0).length > 1 ? gap : 0
  let at = 0
  return values.map((v) => {
    const share = (Math.max(0, v) / total) * 100
    const arc = { start: at + g / 2, len: share > 0 ? Math.max(0.6, share - g) : 0 }
    at += share
    return arc
  })
}

// Every wallet in dollars, then into the display currency.
function totalIn(wallets: MflWallet[], perUsd: number): number {
  return wallets.reduce((sum, w) => sum + (w.perUsd > 0 ? w.balance / w.perUsd : 0), 0) * perUsd
}

// 12 months × 5 weeks of spending, seeded so server and client agree. Months
// drift seasonally and a few weeks spike, like a real ledger.
function spendingGrid(seed: number): number[][] {
  const r = mulberry32(seed)
  return MONTHS.map((_, m) => {
    const season = 1 + 0.35 * Math.sin((m / 12) * Math.PI * 2 + 1.2)
    return [0, 1, 2, 3, 4].map(() => {
      const spike = r() > 0.86 ? 2.2 : 1
      return Math.round((120 + r() * 520) * season * spike * 100) / 100
    })
  })
}

// Five shades. Level 0 is the quietest cell; level 4 the loudest.
function heatLevel(v: number, max: number): number {
  if (!(max > 0) || !(v > 0)) return 0
  return clamp(Math.floor((v / max) * 5), 0, 4)
}

function isEmail(s: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(s.trim())
}

// Arrow keys, Home and End inside a menu. Wraps.
function nextIndex(i: number, key: string, n: number): number {
  if (n <= 0) return -1
  if (key === "ArrowDown") return (i + 1 + n) % n
  if (key === "ArrowUp") return (i - 1 + n) % n
  if (key === "Home") return 0
  if (key === "End") return n - 1
  return i
}

// The statement as words, with "{mark}" kept as its own token so the tile
// trio can sit inline and still count as a step in the reveal.
function statementTokens(s: string): string[] {
  return s
    .replace(/\*/g, "")
    .replace(/\{mark\}/g, " {mark} ")
    .split(/\s+/)
    .filter(Boolean)
}

function resolvePalette(p: MflPaletteName | MflPaletteInput | undefined): MflPalette {
  if (typeof p === "string") return PALETTES[p] || PALETTES.maroon
  return Object.assign({}, PALETTES.maroon, p || {})
}
// #endregion logic

// ---------------------------------------------------------------------------
// small hooks
// ---------------------------------------------------------------------------

function useReducedMotion(): boolean {
  const [reduced, setReduced] = React.useState(false)
  React.useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)")
    const on = () => setReduced(mq.matches)
    on()
    mq.addEventListener?.("change", on)
    return () => mq.removeEventListener?.("change", on)
  }, [])
  return reduced
}

// Closes a popover on an outside press or Escape, returning focus to its button.
function useDismiss(open: boolean, close: () => void, boxRef: { current: HTMLElement | null }) {
  React.useEffect(() => {
    if (!open) return
    const down = (e: PointerEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) close()
    }
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") close()
    }
    document.addEventListener("pointerdown", down)
    document.addEventListener("keydown", key)
    return () => {
      document.removeEventListener("pointerdown", down)
      document.removeEventListener("keydown", key)
    }
  }, [open, close, boxRef])
}

// ---------------------------------------------------------------------------
// marks
// ---------------------------------------------------------------------------

const PETAL = "M12 12C9.2 9.6 9.3 4 12 2.6C14.7 4 14.8 9.6 12 12Z"

function Asterisk({ size = 16, color = "currentColor", className = "" }: { size?: number; color?: string; className?: string }) {
  return (
    <svg className={"mfl-svg " + className} viewBox="0 0 24 24" width={size} height={size} aria-hidden="true">
      <g fill={color} stroke={color} strokeWidth="1.6" strokeLinejoin="round">
        {[0, 60, 120, 180, 240, 300].map((a) => (
          <path key={a} d={PETAL} transform={"rotate(" + a + " 12 12)"} />
        ))}
      </g>
    </svg>
  )
}

function Chevron({ open }: { open?: boolean }) {
  return (
    <svg className={"mfl-svg mfl-chev" + (open ? " is-open" : "")} viewBox="0 0 10 10" width={9} height={9} aria-hidden="true">
      <path d="M2 3.6L5 6.6L8 3.6" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function Arrow({ up }: { up: boolean }) {
  return (
    <svg className="mfl-svg" viewBox="0 0 10 10" width={8} height={8} aria-hidden="true">
      <path d={up ? "M5 1.5L8.6 7.5H1.4Z" : "M5 8.5L8.6 2.5H1.4Z"} fill="currentColor" />
    </svg>
  )
}

function Flag({ code, uid }: { code: string; uid: string }) {
  const clip = uid + "-flag-" + code
  const body = (() => {
    switch (code) {
      case "USD":
        return (
          <>
            <rect width="20" height="20" fill="#f4f1ec" />
            {[0, 1, 2, 3, 4, 5, 6].map((i) => (
              <rect key={i} y={i * 2.9} width="20" height="1.45" fill="#b4302f" />
            ))}
            <rect width="10" height="10" fill="#2b3a67" />
          </>
        )
      case "EUR":
        return (
          <>
            <rect width="20" height="20" fill="#2b4a9b" />
            {Array.from({ length: 12 }, (_, i) => (
              <circle key={i} cx={10 + 5.4 * Math.cos((i / 12) * Math.PI * 2)} cy={10 + 5.4 * Math.sin((i / 12) * Math.PI * 2)} r="0.9" fill="#f5cf4a" />
            ))}
          </>
        )
      case "KRW":
        return (
          <>
            <rect width="20" height="20" fill="#f4f1ec" />
            <path d="M5.5 10a4.5 4.5 0 0 1 9 0z" fill="#c23b3b" />
            <path d="M5.5 10a4.5 4.5 0 0 0 9 0z" fill="#2f4f9b" />
            <circle cx="7.75" cy="10" r="2.25" fill="#c23b3b" />
            <circle cx="12.25" cy="10" r="2.25" fill="#2f4f9b" />
          </>
        )
      case "IDR":
        return (
          <>
            <rect width="20" height="10" fill="#cf3b3b" />
            <rect y="10" width="20" height="10" fill="#f4f1ec" />
          </>
        )
      case "GBP":
        return (
          <>
            <rect width="20" height="20" fill="#2b3a67" />
            <path d="M0 0L20 20M20 0L0 20" stroke="#f4f1ec" strokeWidth="3" />
            <path d="M10 0V20M0 10H20" stroke="#f4f1ec" strokeWidth="5" />
            <path d="M10 0V20M0 10H20" stroke="#c23b3b" strokeWidth="2.6" />
          </>
        )
      case "JPY":
        return (
          <>
            <rect width="20" height="20" fill="#f4f1ec" />
            <circle cx="10" cy="10" r="4.4" fill="#c23b3b" />
          </>
        )
      default:
        return (
          <>
            <rect width="20" height="20" fill="#9a8f84" />
            <text x="10" y="13.2" textAnchor="middle" fontSize="8" fontWeight="600" fill="#fff" fontFamily="ui-sans-serif,system-ui,sans-serif">
              {code.slice(0, 2)}
            </text>
          </>
        )
    }
  })()
  return (
    <svg className="mfl-svg mfl-flag" viewBox="0 0 20 20" width={18} height={18} aria-hidden="true">
      <defs>
        <clipPath id={clip}>
          <circle cx="10" cy="10" r="10" />
        </clipPath>
      </defs>
      <g clipPath={"url(#" + clip + ")"}>{body}</g>
      <circle cx="10" cy="10" r="9.6" fill="none" stroke="rgba(0,0,0,.12)" strokeWidth=".8" />
    </svg>
  )
}

// ---------------------------------------------------------------------------
// a tiny menu button, used by the cards, the wallet and the heatmap
// ---------------------------------------------------------------------------

function MenuSelect({
  label,
  options,
  value,
  onChange,
  tone = "dark",
  render,
}: {
  label: string
  options: string[]
  value: number
  onChange: (i: number) => void
  tone?: "dark" | "light"
  render?: (o: string, i: number) => React.ReactNode
}) {
  const [open, setOpen] = React.useState(false)
  const [active, setActive] = React.useState(value)
  const boxRef = React.useRef(null as HTMLDivElement | null)
  const btnRef = React.useRef(null as HTMLButtonElement | null)
  const listRef = React.useRef(null as HTMLUListElement | null)
  const id = React.useId().replace(/:/g, "")
  const close = React.useCallback(() => {
    setOpen(false)
    btnRef.current?.focus()
  }, [])
  useDismiss(open, close, boxRef)
  React.useEffect(() => {
    if (open) {
      setActive(value)
      listRef.current?.focus()
    }
  }, [open, value])

  const pick = (i: number) => {
    onChange(i)
    close()
  }

  return (
    <div className={"mfl-menu mfl-menu--" + tone} ref={boxRef}>
      <button
        ref={btnRef}
        type="button"
        className="mfl-menu-btn"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={label + ": " + options[value]}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            e.preventDefault()
            setOpen(true)
          }
        }}
      >
        {render ? render(options[value], value) : options[value]}
        <Chevron open={open} />
      </button>
      {open && (
        <ul
          ref={listRef}
          className="mfl-menu-list"
          role="listbox"
          tabIndex={-1}
          aria-label={label}
          aria-activedescendant={id + "-" + active}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault()
              pick(active)
            } else if (e.key === "Tab") setOpen(false)
            else {
              const n = nextIndex(active, e.key, options.length)
              if (n !== active) {
                e.preventDefault()
                setActive(n)
              }
            }
          }}
        >
          {options.map((o, i) => (
            <li
              key={o + i}
              id={id + "-" + i}
              role="option"
              aria-selected={i === value}
              className={"mfl-menu-opt" + (i === active ? " is-active" : "")}
              onPointerEnter={() => setActive(i)}
              onClick={() => pick(i)}
            >
              {render ? render(o, i) : o}
              {i === value && (
                <svg className="mfl-svg" viewBox="0 0 12 12" width={10} height={10} aria-hidden="true">
                  <path d="M2.5 6.2L5 8.6L9.5 3.6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// hero art
// ---------------------------------------------------------------------------

type Chip = { x: number; y: number; glyph: string }

// Traces for the left half. The right half is the same board mirrored, so the
// device sits at the meeting point of both.
const TRACES = [
  "M0 236H96M156 236H232Q252 236 252 256V336Q252 356 272 356H430Q450 356 450 376V560Q450 580 470 580H600",
  "M0 470H118M178 470H300Q320 470 320 490V640Q320 660 340 660H612",
  "M84 0V122Q84 142 104 142H170",
  "M0 640H96M156 640H200Q220 640 220 660V760Q220 780 240 780H560",
  "M0 356H24M84 356H160",
  "M330 0V140Q330 160 350 160H380",
]

const CHIPS: Chip[] = [
  { x: 126, y: 236, glyph: "$" },
  { x: 148, y: 470, glyph: "%" },
  { x: 54, y: 356, glyph: "≡" },
  { x: 126, y: 640, glyph: "↗" },
  { x: 200, y: 142, glyph: "··" },
  { x: 410, y: 160, glyph: "◦" },
]

function CircuitBoard({ uid, reduced, hot }: { uid: string; reduced: boolean; hot: number }) {
  const g = uid + "-pulse"
  const half = (side: number) => (
    <g transform={side ? "translate(1440 0) scale(-1 1)" : undefined}>
      {TRACES.map((d, i) => (
        <path key={"t" + i} d={d} className="mfl-trace" />
      ))}
      {!reduced &&
        TRACES.map((d, i) => (
          <path
            key={"p" + i}
            d={d}
            pathLength={1000}
            className="mfl-pulse"
            stroke={"url(#" + g + ")"}
            style={{ animationDelay: -((i * 1.7 + side * 2.3) % 6) + "s", animationDuration: 5 + ((i + side) % 3) + "s" }}
          />
        ))}
      {CHIPS.map((c, i) => {
        const on = hot === i + side * CHIPS.length
        return (
          <g key={"c" + i} className={"mfl-chip" + (on ? " is-hot" : "")} transform={"translate(" + c.x + " " + c.y + ")"}>
            <rect x="-28" y="-16" width="56" height="32" rx="8" />
            <text x="0" y="4.5" textAnchor="middle" transform={side ? "scale(-1 1)" : undefined}>
              {c.glyph}
            </text>
          </g>
        )
      })}
    </g>
  )
  return (
    <svg className="mfl-svg mfl-circuit" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs>
        <linearGradient id={g} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="var(--mfl-brand)" stopOpacity="0" />
          <stop offset=".7" stopColor="var(--mfl-brand)" stopOpacity=".55" />
          <stop offset="1" stopColor="var(--mfl-glow)" stopOpacity=".9" />
        </linearGradient>
      </defs>
      {half(0)}
      {half(1)}
    </svg>
  )
}

function chipCenters(): { x: number; y: number }[] {
  return [...CHIPS.map((c) => ({ x: c.x, y: c.y })), ...CHIPS.map((c) => ({ x: 1440 - c.x, y: c.y }))]
}

function Device({ uid, pulse }: { uid: string; pulse: number }) {
  const p = uid + "-dev"
  return (
    <svg className="mfl-svg mfl-device-svg" viewBox="0 0 320 320" width={320} height={320} aria-hidden="true">
      <defs>
        <linearGradient id={p + "-face"} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity=".28" />
          <stop offset=".45" stopColor="#fff" stopOpacity=".04" />
          <stop offset="1" stopColor="#000" stopOpacity=".22" />
        </linearGradient>
        <radialGradient id={p + "-sheen"} cx=".28" cy=".22" r=".7">
          <stop offset="0" stopColor="#fff" stopOpacity=".55" />
          <stop offset=".5" stopColor="#fff" stopOpacity=".08" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={p + "-side"} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#000" stopOpacity=".05" />
          <stop offset="1" stopColor="#000" stopOpacity=".45" />
        </linearGradient>
        <linearGradient id={p + "-led"} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="var(--mfl-glow)" stopOpacity="0" />
          <stop offset=".55" stopColor="var(--mfl-glow)" stopOpacity=".95" />
          <stop offset=".8" stopColor="#fff6e0" stopOpacity="1" />
          <stop offset="1" stopColor="var(--mfl-glow)" stopOpacity=".2" />
        </linearGradient>
        <filter id={p + "-blur"} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="9" />
        </filter>
        <filter id={p + "-soft"} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2.4" />
        </filter>
      </defs>
      <g transform="rotate(-14 160 160)">
        {/* thickness: the same body pushed down and shaded */}
        <rect x="46" y="58" width="228" height="228" rx="76" fill="var(--mfl-device)" />
        <rect x="46" y="58" width="228" height="228" rx="76" fill={"url(#" + p + "-side)"} />
        {/* the light ring leaking out under the lid */}
        <g key={pulse} className="mfl-led">
          <path d="M270 150Q276 262 168 280" fill="none" stroke={"url(#" + p + "-led)"} strokeWidth="14" strokeLinecap="round" filter={"url(#" + p + "-blur)"} />
          <path d="M268 160Q270 258 172 276" fill="none" stroke={"url(#" + p + "-led)"} strokeWidth="3.4" strokeLinecap="round" />
        </g>
        {/* lid */}
        <rect x="46" y="44" width="228" height="228" rx="76" fill="var(--mfl-device)" />
        <rect x="46" y="44" width="228" height="228" rx="76" fill={"url(#" + p + "-face)"} />
        <rect x="46" y="44" width="228" height="228" rx="76" fill={"url(#" + p + "-sheen)"} />
        <rect x="47" y="45" width="226" height="226" rx="75" fill="none" stroke="#fff" strokeOpacity=".35" strokeWidth="1.4" />
        {/* the debossed mark */}
        <g transform="translate(160 158) scale(2.1) translate(-12 -12)" filter={"url(#" + p + "-soft)"} opacity=".55">
          <g fill="#fff" transform="translate(.5 .7)">
            {[0, 60, 120, 180, 240, 300].map((a) => (
              <path key={a} d={PETAL} transform={"rotate(" + a + " 12 12)"} />
            ))}
          </g>
        </g>
        <g transform="translate(160 158) scale(2.1) translate(-12 -12)" fill="#000" fillOpacity=".42" stroke="#000" strokeOpacity=".42" strokeWidth="1.4" strokeLinejoin="round">
          {[0, 60, 120, 180, 240, 300].map((a) => (
            <path key={a} d={PETAL} transform={"rotate(" + a + " 12 12)"} />
          ))}
        </g>
      </g>
    </svg>
  )
}

// ---------------------------------------------------------------------------
// satin: the lit fabric behind the feature panel
// ---------------------------------------------------------------------------

function Satin({ uid, variant = 0 }: { uid: string; variant?: number }) {
  const p = uid + "-satin" + variant
  const flip = variant % 2 === 1
  // stop colours go through style so the palette's CSS variables reach them
  const stop = (offset: string, color: string, opacity: number) => (
    <stop offset={offset} style={{ stopColor: "var(--mfl-sat-" + color + ")", stopOpacity: opacity }} />
  )
  const ink = (color: string) => ({ stroke: "var(--mfl-sat-" + color + ")" })
  return (
    <svg className="mfl-svg mfl-satin" viewBox="0 0 1200 700" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      <defs>
        <radialGradient id={p + "-sun"} cx="0.9" cy="0.08" r="0.55">
          {stop("0", "light", 1)}
          {stop(".35", "mid", 0.6)}
          {stop("1", "dark", 0)}
        </radialGradient>
        <linearGradient id={p + "-band"} x1="0" y1="1" x2="1" y2="0">
          {stop("0", "dark", 0)}
          {stop(".3", "mid", 0.7)}
          {stop(".55", "light", 0.95)}
          {stop(".75", "mid", 0.6)}
          {stop("1", "dark", 0)}
        </linearGradient>
        <linearGradient id={p + "-edge"} x1="0" y1="0" x2="1" y2="0">
          {stop("0", "light", 0.95)}
          {stop(".5", "mid", 0.45)}
          {stop("1", "dark", 0)}
        </linearGradient>
        <filter id={p + "-b1"} x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="26" />
        </filter>
        <filter id={p + "-b2"} x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="9" />
        </filter>
        <filter id={p + "-b3"} x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="3" />
        </filter>
      </defs>
      <g transform={flip ? "translate(1200 0) scale(-1 1)" : undefined}>
        <rect width="1200" height="700" style={{ fill: "var(--mfl-sat-dark)" }} />
        <rect width="1200" height="700" fill={"url(#" + p + "-sun)"} />
        <g className="mfl-satin-a">
          <path
            d="M-120 620C160 520 360 420 620 250S1020 20 1320 -60L1320 110C1040 170 820 330 600 470S160 720 -120 800Z"
            fill={"url(#" + p + "-band)"}
            filter={"url(#" + p + "-b1)"}
          />
          <path d="M-60 700C240 560 470 430 700 270S1080 60 1300 0" fill="none" style={ink("light")} strokeOpacity=".6" strokeWidth="7" filter={"url(#" + p + "-b3)"} />
          <path d="M-80 760C230 620 470 500 720 340S1080 130 1310 70" fill="none" stroke="#000" strokeOpacity=".5" strokeWidth="36" filter={"url(#" + p + "-b2)"} />
        </g>
        <g className="mfl-satin-b">
          <path d="M-60 120C40 220 90 380 60 560S20 700 40 760L-60 760Z" fill={"url(#" + p + "-edge)"} filter={"url(#" + p + "-b1)"} />
          <path d="M-20 160C60 260 90 420 64 600" fill="none" style={ink("light")} strokeOpacity=".6" strokeWidth="5" filter={"url(#" + p + "-b3)"} />
        </g>
        <g className="mfl-satin-c">
          <path d="M1240 300C1150 400 1090 520 1080 720L1240 720Z" style={{ fill: "var(--mfl-sat-light)" }} fillOpacity=".5" filter={"url(#" + p + "-b1)"} />
          <path d="M1210 340C1140 430 1100 540 1094 720" fill="none" style={ink("light")} strokeOpacity=".45" strokeWidth="4" filter={"url(#" + p + "-b3)"} />
        </g>
        <rect width="1200" height="700" fill="#000" fillOpacity=".14" />
      </g>
    </svg>
  )
}

// ---------------------------------------------------------------------------
// hero cards
// ---------------------------------------------------------------------------

function Donut({
  cats,
  hover,
  setHover,
  colors,
}: {
  cats: MflCategory[]
  hover: number
  setHover: (i: number) => void
  colors: string[]
}) {
  const arcs = donutArcs(
    cats.map((c) => c.value),
    3,
  )
  const total = cats.reduce((a, c) => a + c.value, 0)
  const shown = hover >= 0 && cats[hover] ? Math.round((cats[hover].value / (total || 1)) * 100) + "%" : ""
  return (
    <svg className="mfl-svg mfl-donut" viewBox="0 0 64 64" width={64} height={64} role="img" aria-label="Category split" onPointerLeave={() => setHover(-1)}>
      <circle cx="32" cy="32" r="24" fill="none" stroke="rgba(255,255,255,.08)" strokeWidth="9" />
      {arcs.map((a, i) =>
        a.len > 0 ? (
          <circle
            key={i}
            cx="32"
            cy="32"
            r="24"
            fill="none"
            pathLength={100}
            stroke={cats[i].color || colors[i % colors.length]}
            strokeWidth={hover === i ? 11 : 9}
            strokeDasharray={a.len + " " + (100 - a.len)}
            strokeDashoffset={-a.start}
            transform="rotate(-90 32 32)"
            className={"mfl-arc" + (hover >= 0 && hover !== i ? " is-dim" : "")}
            onPointerEnter={() => setHover(i)}
          />
        ) : null,
      )}
      <text x="32" y="35.5" textAnchor="middle" className="mfl-donut-t">
        {shown}
      </text>
    </svg>
  )
}

function StatCard({ card }: { card: MflStatCard }) {
  const [pi, setPi] = React.useState(0)
  const [hover, setHover] = React.useState(-1)
  const p = card.periods[pi] || card.periods[0]
  if (!p) return null
  const up = p.change >= 0
  return (
    <article className="mfl-stat">
      <header className="mfl-stat-top">
        <div>
          <h3 className="mfl-stat-t">{card.title}</h3>
          <p className="mfl-stat-d">{p.range}</p>
        </div>
        <div className="mfl-stat-tools">
          <span className="mfl-ico" aria-hidden="true">
            <svg className="mfl-svg" viewBox="0 0 12 12" width={10} height={10}>
              <rect x="1.5" y="2.5" width="9" height="8" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.1" />
              <path d="M1.5 5H10.5M4 1.5V3.5M8 1.5V3.5" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" />
            </svg>
          </span>
          <MenuSelect label={card.title + " period"} options={card.periods.map((x) => x.label)} value={pi} onChange={(i) => (setPi(i), setHover(-1))} />
        </div>
      </header>
      <div className="mfl-stat-amt" key={pi}>
        {formatMoney(p.amount, "$ ", 2)}
      </div>
      <div className="mfl-stat-chg">
        <span className={"mfl-chg" + (up ? "" : " is-down")}>
          <Arrow up={up} />
          {Math.abs(p.change).toFixed(1)}%
        </span>
        <span>from last {pi === 2 ? "day" : pi === 1 ? "week" : "month"}</span>
      </div>
      <div className="mfl-stat-split">
        <Donut cats={p.categories} hover={hover} setHover={setHover} colors={CAT_COLORS} />
        <div className="mfl-legend">
          <p className="mfl-legend-h">All categories</p>
          <ul>
            {p.categories.slice(0, 4).map((c, i) => (
              <li
                key={c.label}
                className={hover >= 0 && hover !== i ? "is-dim" : ""}
                onPointerEnter={() => setHover(i)}
                onPointerLeave={() => setHover(-1)}
              >
                <i style={{ background: c.color || CAT_COLORS[i % CAT_COLORS.length] }} />
                <span>{c.label}</span>
                <b>{formatMoney(c.value, "$", 2)}</b>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </article>
  )
}

// ---------------------------------------------------------------------------
// feature widgets
// ---------------------------------------------------------------------------

function WalletWidget({ wallets, growth, uid }: { wallets: MflWallet[]; growth: string; uid: string }) {
  const [sel, setSel] = React.useState(0)
  const [all, setAll] = React.useState(false)
  const cur = wallets[sel] || wallets[0]
  const total = cur ? totalIn(wallets, cur.perUsd) : 0
  const shown = all ? wallets : wallets.slice(0, 4)
  return (
    <div className="mfl-panel mfl-wallet">
      <div className="mfl-panel-row">
        <div>
          <p className="mfl-panel-k">Total Balance</p>
          <p className="mfl-wallet-total" key={sel} aria-live="polite">
            {cur ? formatMoney(total, cur.symbol, decimalsFor(cur.code)) : "—"}
          </p>
          <p className="mfl-wallet-g">{growth}</p>
        </div>
        {cur && (
          <MenuSelect
            label="Display currency"
            tone="light"
            options={wallets.map((w) => w.code)}
            value={sel}
            onChange={setSel}
            render={(o, i) => (
              <span className="mfl-cur">
                <Flag code={o} uid={uid + "m" + i} />
                {o}
              </span>
            )}
          />
        )}
      </div>
      <div className="mfl-panel-row mfl-wallet-h">
        <p>Wallets</p>
        {wallets.length > 4 && (
          <button type="button" className="mfl-link" aria-expanded={all} onClick={() => setAll((a) => !a)}>
            {all ? "Show less" : "See all"}
          </button>
        )}
      </div>
      <div className="mfl-wallet-grid">
        {shown.map((w, i) => (
          <button
            key={w.code}
            type="button"
            className={"mfl-wtile" + (i === sel ? " is-sel" : "")}
            aria-pressed={i === sel}
            onClick={() => setSel(i)}
            title={"Show the total in " + w.code}
          >
            <span className="mfl-cur">
              <Flag code={w.code} uid={uid + "t" + i} />
              {w.code}
            </span>
            <b>{formatMoney(w.balance, w.symbol, decimalsFor(w.code))}</b>
            <em className={w.active === false ? "is-off" : ""}>{w.active === false ? "Paused" : "Active"}</em>
          </button>
        ))}
      </div>
    </div>
  )
}

function SpendingWidget({ grid, budget }: { grid: number[][]; budget: number }) {
  const [span, setSpan] = React.useState(0)
  const [tip, setTip] = React.useState(null as null | { m: number; w: number })
  const months = SPAN_MONTHS[span]
  const first = 12 - months
  const cols = grid.slice(first)
  const scaled = budget * (months / 12)
  const total = cols.reduce((a, c) => a + c.reduce((b, v) => b + v, 0), 0)
  const max = Math.max(1, ...grid.flat())
  const pct = clamp(total / (scaled || 1), 0, 1)
  return (
    <div className="mfl-panel mfl-spend" onPointerLeave={() => setTip(null)}>
      <div className="mfl-panel-row">
        <p className="mfl-panel-k">Spending Overview</p>
        <MenuSelect label="Range" tone="light" options={SPAN_LABELS} value={span} onChange={(i) => (setSpan(i), setTip(null))} />
      </div>
      <div className="mfl-panel-row mfl-spend-sum">
        <p>
          <b key={span}>{formatMoney(total, "$", 2)}</b>
          <span> of {formatMoney(scaled, "$", 2)}</span>
        </p>
        <div className="mfl-spend-legend" aria-hidden="true">
          <span>
            <i className="lv2" />
            &gt;$500
          </span>
          <span>
            <i className="lv4" />
            &gt;$900
          </span>
        </div>
      </div>
      <div className="mfl-meter" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(pct * 100)} aria-label="Budget used">
        <i style={{ width: pct * 100 + "%" }} />
      </div>
      <div className="mfl-heat" style={{ gridTemplateColumns: "repeat(" + months + ", 1fr)" }}>
        {cols.map((col, ci) => (
          <div className="mfl-heat-col" key={first + ci}>
            {col.map((v, wi) => {
              const lv = heatLevel(v, max)
              const on = tip && tip.m === first + ci && tip.w === wi
              return (
                <button
                  key={wi}
                  type="button"
                  className={"mfl-cell lv" + lv + (on ? " is-on" : "")}
                  aria-label={MONTHS[first + ci] + ", week " + (wi + 1) + ": " + formatMoney(v, "$", 2)}
                  onPointerEnter={() => setTip({ m: first + ci, w: wi })}
                  onFocus={() => setTip({ m: first + ci, w: wi })}
                  onBlur={() => setTip(null)}
                  style={{ animationDelay: (ci * 5 + wi) * 14 + "ms" }}
                />
              )
            })}
            <span className="mfl-heat-m">{MONTHS[first + ci]}</span>
          </div>
        ))}
      </div>
      <p className="mfl-heat-tip" aria-live="polite">
        {tip ? (
          <>
            <b>{MONTHS[tip.m]}</b> · week {tip.w + 1} · {formatMoney(grid[tip.m][tip.w], "$", 2)}
          </>
        ) : (
          "Hover a week to see what went out."
        )}
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// request-demo dialog
// ---------------------------------------------------------------------------

function DemoDialog({
  open,
  onClose,
  brand,
  onRequestDemo,
}: {
  open: boolean
  onClose: () => void
  brand: string
  onRequestDemo?: MaroonFintechLandingProps["onRequestDemo"]
}) {
  const [form, setForm] = React.useState({ name: "", email: "", company: "", size: "11–50" } as MflDemoRequest)
  const [state, setState] = React.useState("idle" as "idle" | "sending" | "done" | "error")
  const [err, setErr] = React.useState("")
  const boxRef = React.useRef(null as HTMLDivElement | null)
  const firstRef = React.useRef(null as HTMLInputElement | null)
  const alive = React.useRef(true)
  React.useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
    }
  }, [])

  React.useEffect(() => {
    if (!open) return
    const back = document.activeElement as HTMLElement | null
    setState("idle")
    setErr("")
    const t = window.setTimeout(() => firstRef.current?.focus(), 30)
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
      if (e.key === "Tab" && boxRef.current) {
        const f = boxRef.current.querySelectorAll("button, input, select")
        if (!f.length) return
        const a = f[0] as HTMLElement
        const z = f[f.length - 1] as HTMLElement
        if (e.shiftKey && document.activeElement === a) {
          e.preventDefault()
          z.focus()
        } else if (!e.shiftKey && document.activeElement === z) {
          e.preventDefault()
          a.focus()
        }
      }
    }
    document.addEventListener("keydown", key)
    return () => {
      window.clearTimeout(t)
      document.removeEventListener("keydown", key)
      back?.focus?.()
    }
  }, [open, onClose])

  if (!open) return null

  const set = (k: keyof MflDemoRequest) => (e: ChangeEv) => {
    const v = e.target.value
    setForm((f) => ({ ...f, [k]: v }))
    if (err) setErr("")
  }

  const submit = async (e: FormEv) => {
    e.preventDefault()
    if (state === "sending") return
    if (!form.name.trim()) return setErr("Tell us who to ask for.")
    if (!isEmail(form.email)) return setErr("That email doesn't look right.")
    setErr("")
    setState("sending")
    try {
      const ok = onRequestDemo ? await onRequestDemo(form) : await new Promise((done: (v: boolean) => void) => setTimeout(() => done(true), 900))
      if (ok === false) throw new Error("rejected")
      if (alive.current) setState("done")
    } catch {
      if (alive.current) {
        setState("error")
        setErr("Something went wrong. Try again in a moment.")
      }
    }
  }

  return (
    <div className="mfl-modal" onPointerDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="mfl-dialog" role="dialog" aria-modal="true" aria-labelledby="mfl-dialog-h" ref={boxRef}>
        <button type="button" className="mfl-x" aria-label="Close" onClick={onClose}>
          <svg className="mfl-svg" viewBox="0 0 12 12" width={12} height={12} aria-hidden="true">
            <path d="M2 2L10 10M10 2L2 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>
        {state === "done" ? (
          <div className="mfl-done">
            <span className="mfl-done-mark">
              <Asterisk size={30} />
            </span>
            <h2 id="mfl-dialog-h">Request received.</h2>
            <p>
              We'll email {form.email.trim()} within one business day to arrange your walkthrough.
            </p>
            <button type="button" className="mfl-btn mfl-btn--brand" onClick={onClose}>
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={submit} noValidate>
            <p className="mfl-badge mfl-badge--light">
              <Asterisk size={10} /> Launch Demo
            </p>
            <h2 id="mfl-dialog-h">See {brand.replace(/\.$/, "")} run a task end to end.</h2>
            <p className="mfl-dialog-sub">A short walkthrough of the marketplace, x402 payments and the ledger. No slides.</p>
            <label>
              <span>Full name</span>
              <input ref={firstRef} value={form.name} onChange={set("name")} autoComplete="name" placeholder="Ada Mensah" />
            </label>
            <label>
              <span>Work email</span>
              <input value={form.email} onChange={set("email")} type="email" autoComplete="email" placeholder="ada@company.com" aria-invalid={!!err && !isEmail(form.email)} />
            </label>
            <div className="mfl-dialog-row">
              <label>
                <span>Company</span>
                <input value={form.company} onChange={set("company")} autoComplete="organization" placeholder="Northwind" />
              </label>
              <label>
                <span>Team size</span>
                <select value={form.size} onChange={set("size")}>
                  {["1–10", "11–50", "51–200", "201–1000", "1000+"].map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </label>
            </div>
            <p className="mfl-err" role="alert">
              {err}
            </p>
            <button type="submit" className="mfl-btn mfl-btn--brand mfl-btn--wide" disabled={state === "sending"}>
              {state === "sending" ? "Sending…" : "Send request"}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// the page
// ---------------------------------------------------------------------------

export default function MaroonFintechLanding({
  brand = "Agentica.",
  logo,
  nav = DEFAULT_NAV,
  login = { label: "Launch App", href: "/dashboard" },
  signup = { label: "Buyer Console", href: "/buyer" },
  backer = { prefix: "Protocol v2 • EIP-712", name: "Base Sepolia Testnet", mark: "x402" },
  title = "AI Agents That *Pay*\n*AI* Agents",
  subtitle = "The first pay-per-call marketplace where autonomous agents discover specialized services, pay in USDC via x402 handshakes, and verify cryptographic execution.",
  primaryAction = { label: "Launch App", href: "/dashboard" },
  secondaryAction = { label: "Explore Marketplace", href: "/marketplace" },
  info = {
    label: "/protocol/",
    text: "Agentica empowers autonomous agents to discover registered seller endpoints, negotiate micro-budgets in USDC, and execute cryptographic x402 handshakes with sub-second finality.",
  },
  statCards = DEFAULT_CARDS,
  about = {
    kicker: "The Machine Economy",
    statement:
      "Agentica {mark} establishes the economic standard for autonomous intelligence. Software agents discover verified tool capabilities, negotiate micro-budgets in real-time, and settle payments per API call using cryptographic x402 handshakes.",
    stats: DEFAULT_STATS,
  },
  features = {
    kicker: "Autonomous Architecture",
    title: "Essential *Tools For*\n*Autonomous* Agents",
    subtitle: "Instant discovery, EIP-712 signatures, and budget-enforced micro-settlement on Base Sepolia.",
  },
  wallet = {
    title: "Agent Treasury & Budget Enforcer",
    description: "Manage autonomous agent balances from a single dashboard. Cap task budgets, monitor per-call USDC spending, and inspect cryptographic signatures.",
    growth: "+18.4% · Volume This Month",
  },
  spending = {
    title: "Real-Time Settlement Ledger",
    description: "Visualize micro-transaction velocity, invocation frequency, and latency heatmaps across 12 months of testnet execution.",
    budget: 50000,
    seed: 7,
  },
  cta = {
    title: "Every agent call, *cryptographically* settled.",
    subtitle: "Connect your buyer agent or register your seller services in minutes. Testnet faucet tokens available on launch.",
    action: { label: "Explore Marketplace", href: "/marketplace" },
  },
  footer = DEFAULT_FOOTER,
  palette = "maroon",
  onRequestDemo,
  height = "100svh",
  className = "",
}: MaroonFintechLandingProps) {
  const uid = React.useId().replace(/:/g, "")
  const reduced = useReducedMotion()
  const pal = resolvePalette(palette)
  const rootRef = React.useRef(null as HTMLDivElement | null)
  const heroRef = React.useRef(null as HTMLElement | null)
  const svgWrapRef = React.useRef(null as HTMLDivElement | null)
  const deviceRef = React.useRef(null as HTMLDivElement | null)
  const statementRef = React.useRef(null as HTMLParagraphElement | null)
  const statsRef = React.useRef(null as HTMLDivElement | null)
  const satinRef = React.useRef(null as HTMLElement | null)

  const [menuOpen, setMenuOpen] = React.useState(false)
  const [scrolled, setScrolled] = React.useState(false)
  const [demoOpen, setDemoOpen] = React.useState(false)
  const [hotChip, setHotChip] = React.useState(-1)
  const [pulse, setPulse] = React.useState(0)
  const [spin, setSpin] = React.useState(0)
  const [lit, setLit] = React.useState(0)
  const [counts, setCounts] = React.useState(0)
  const menuBoxRef = React.useRef(null as HTMLDivElement | null)
  const menuBtnRef = React.useRef(null as HTMLButtonElement | null)
  const closeMenu = React.useCallback(() => setMenuOpen(false), [])
  const closeDemo = React.useCallback(() => setDemoOpen(false), [])
  useDismiss(menuOpen, closeMenu, menuBoxRef)

  const brandWord = brand.replace(/\.$/, "")
  const brandDot = brand.endsWith(".")
  const tokens = React.useMemo(() => (about ? statementTokens(about.statement) : []), [about])
  const grid = React.useMemo(() => {
    const m = spending?.months
    if (m && m.length === 12) return m.map((c) => [0, 1, 2, 3, 4].map((i) => Math.max(0, c[i] || 0)))
    return spendingGrid(spending?.seed ?? 7)
  }, [spending])
  const wallets = wallet?.wallets && wallet.wallets.length ? wallet.wallets : DEFAULT_WALLETS

  const navigate = useNavigate()

  // ---- in-page and SPA route links ----------------------------------------
  const go = (href: string | undefined, e: AnchorEv) => {
    setMenuOpen(false)
    if (!href) return
    if (href.startsWith("/")) {
      e.preventDefault()
      navigate(href)
      return
    }
    if (href.startsWith("http://") || href.startsWith("https://")) {
      return
    }
    if (!href.startsWith("#")) return
    const target = rootRef.current?.querySelector('[data-sec="' + href.slice(1) + '"]')
    if (!target) {
      if (href === "#") e.preventDefault()
      return
    }
    e.preventDefault()
    target.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" })
  }

  // ---- scroll: nav state, statement reveal, counters ----------------------
  React.useEffect(() => {
    let raf = 0
    const tick = () => {
      raf = 0
      const root = rootRef.current
      if (!root) return
      setScrolled(root.getBoundingClientRect().top < -40)
      const st = statementRef.current
      if (st) {
        const r = st.getBoundingClientRect()
        const vh = window.innerHeight || 800
        // first word lights as the paragraph's top crosses 85% of the
        // viewport; the last as its bottom crosses 55%.
        const start = vh * 0.85
        const end = vh * 0.55
        const prog = clamp((start - r.top) / (start - end + r.height), 0, 1)
        setLit(reduced ? tokens.length : Math.round(prog * tokens.length))
      }
    }
    const on = () => {
      if (!raf) raf = requestAnimationFrame(tick)
    }
    on()
    window.addEventListener("scroll", on, { passive: true })
    window.addEventListener("resize", on)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener("scroll", on)
      window.removeEventListener("resize", on)
    }
  }, [tokens.length, reduced])

  React.useEffect(() => {
    const el = statsRef.current
    if (!el) return
    if (reduced || typeof IntersectionObserver === "undefined") {
      setCounts(1)
      return
    }
    let raf = 0
    const io = new IntersectionObserver(
      (es) => {
        if (!es.some((x) => x.isIntersecting)) return
        io.disconnect()
        const t0 = performance.now()
        const step = (t: number) => {
          const k = easeOutCubic((t - t0) / 1600)
          setCounts(k)
          if (k < 1) raf = requestAnimationFrame(step)
        }
        raf = requestAnimationFrame(step)
      },
      { threshold: 0.4 },
    )
    io.observe(el)
    return () => {
      io.disconnect()
      cancelAnimationFrame(raf)
    }
  }, [reduced])

  // ---- reveal on scroll: only what starts below the fold is hidden --------
  React.useEffect(() => {
    const root = rootRef.current
    if (!root || reduced || typeof IntersectionObserver === "undefined") return
    const vh = window.innerHeight || 800
    const below = Array.from(root.querySelectorAll(".mfl-rise")).filter((n) => n.getBoundingClientRect().top > vh)
    below.forEach((n) => n.classList.add("mfl-pre"))
    const io = new IntersectionObserver(
      (es) =>
        es.forEach((x) => {
          if (x.isIntersecting) {
            x.target.classList.remove("mfl-pre")
            io.unobserve(x.target)
          }
        }),
      { threshold: 0.15, rootMargin: "0px 0px -40px 0px" },
    )
    below.forEach((n) => io.observe(n))
    return () => {
      io.disconnect()
      below.forEach((n) => n.classList.remove("mfl-pre"))
    }
  }, [reduced])

  // ---- hero pointer: tilt the device, light the nearest chip --------------
  const centers = React.useMemo(chipCenters, [])
  const onHeroMove = (e: PointerEv) => {
    if (e.pointerType === "touch") return
    const dev = deviceRef.current
    const hero = heroRef.current
    if (dev && hero && !reduced) {
      const r = hero.getBoundingClientRect()
      const nx = (e.clientX - r.left) / r.width - 0.5
      const ny = (e.clientY - r.top) / r.height - 0.5
      dev.style.setProperty("--mfl-rx", (-ny * 18).toFixed(2) + "deg")
      dev.style.setProperty("--mfl-ry", (nx * 24).toFixed(2) + "deg")
    }
    const box = svgWrapRef.current
    if (!box) return
    const b = box.getBoundingClientRect()
    // undo preserveAspectRatio="xMidYMid slice"
    const s = Math.max(b.width / 1440, b.height / 900)
    const vx = (e.clientX - b.left - (b.width - 1440 * s) / 2) / s
    const vy = (e.clientY - b.top - (b.height - 900 * s) / 2) / s
    let best = -1
    let bestD = 90
    centers.forEach((c, i) => {
      const d = Math.hypot(c.x - vx, c.y - vy)
      if (d < bestD) {
        bestD = d
        best = i
      }
    })
    if (best !== hotChip) setHotChip(best)
  }
  const onHeroLeave = () => {
    setHotChip(-1)
    deviceRef.current?.style.setProperty("--mfl-rx", "0deg")
    deviceRef.current?.style.setProperty("--mfl-ry", "0deg")
  }

  // ---- the satin follows the pointer a little -----------------------------
  const onSatinMove = (e: PointerEv) => {
    const el = satinRef.current
    if (!el || reduced) return
    const r = el.getBoundingClientRect()
    el.style.setProperty("--mfl-sx", ((e.clientX - r.left) / r.width) * 100 + "%")
    el.style.setProperty("--mfl-sy", ((e.clientY - r.top) / r.height) * 100 + "%")
  }

  const press = () => {
    setPulse((p) => p + 1)
    setSpin((s) => s + 1)
  }

  const rootStyle = {
    "--mfl-frame": pal.frame,
    "--mfl-paper": pal.paper,
    "--mfl-ink": pal.ink,
    "--mfl-muted": pal.muted,
    "--mfl-brand": pal.brand,
    "--mfl-night": pal.night,
    "--mfl-card": pal.card,
    "--mfl-cream": pal.cream,
    "--mfl-device": pal.device,
    "--mfl-glow": pal.glow,
    "--mfl-sat-dark": pal.satin[0],
    "--mfl-sat-mid": pal.satin[1],
    "--mfl-sat-light": pal.satin[2],
  } as React.CSSProperties

  const mark = logo ?? (
    <span className="mfl-logo-mark" aria-hidden="true">
      <Asterisk size={13} color={pal.cream} />
    </span>
  )

  const two = (s: string, cls = "") =>
    s.split("\n").map((line, li) => (
      <span className={"mfl-line " + cls} key={li}>
        {parseEmphasis(line).map((seg, si) => (
          <span key={si} className={seg.muted ? "mfl-mute" : undefined}>
            {seg.text}
          </span>
        ))}
      </span>
    ))

  return (
    <div ref={rootRef} className={"mfl-root " + className} style={rootStyle} data-scrolled={scrolled || undefined}>
      <style>{MFL_CSS}</style>

      {/* ------------------------------------------------------------ nav */}
      <nav className="mfl-nav" aria-label="Main">
        <div className="mfl-nav-l" ref={menuBoxRef}>
          <div className="mfl-logo-pill">
            <a href="#" className="mfl-logo" onClick={(e) => (e.preventDefault(), rootRef.current?.scrollIntoView({ behavior: reduced ? "auto" : "smooth" }))}>
              {mark}
              <span>
                {brandWord}
                {brandDot && <span className="mfl-dot">.</span>}
              </span>
            </a>
            {nav.length > 0 && (
              <button
                ref={menuBtnRef}
                type="button"
                className={"mfl-burger" + (menuOpen ? " is-open" : "")}
                aria-label={menuOpen ? "Close menu" : "Open menu"}
                aria-expanded={menuOpen}
                aria-controls={uid + "-menu"}
                onClick={() => setMenuOpen((o) => !o)}
              >
                <i />
                <i />
              </button>
            )}
          </div>
          {menuOpen && (
            <div className="mfl-dropdown" id={uid + "-menu"}>
              <ul>
                {nav.map((l, i) => (
                  <li key={l.label} style={{ animationDelay: i * 40 + "ms" }}>
                    <a href={l.href || "#"} onClick={(e) => go(l.href, e)}>
                      <span className="mfl-dd-n">0{i + 1}</span>
                      {l.label}
                      <svg className="mfl-svg" viewBox="0 0 12 12" width={12} height={12} aria-hidden="true">
                        <path d="M3 9L9 3M4 3H9V8" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                      </svg>
                    </a>
                  </li>
                ))}
              </ul>
              <div className="mfl-dd-foot">
                <span className="mfl-live" />
                All systems normal
              </div>
            </div>
          )}
        </div>
        <div className="mfl-nav-r">
          {login && (
            <a className="mfl-btn mfl-btn--brand mfl-btn--sm" href={login.href || "#"} onClick={(e) => go(login.href, e)}>
              {login.label}
            </a>
          )}
          {signup && (
            <a className="mfl-btn mfl-btn--white mfl-btn--sm" href={signup.href || "#"} onClick={(e) => go(signup.href, e)}>
              {signup.label}
            </a>
          )}
        </div>
      </nav>

      {/* ----------------------------------------------------------- hero */}
      <header
        ref={heroRef}
        className="mfl-hero"
        style={{ minHeight: "max(700px, calc(" + height + " - 14px))" }}
        onPointerMove={onHeroMove}
        onPointerLeave={onHeroLeave}
      >
        <div className="mfl-circuit-wrap" ref={svgWrapRef}>
          <CircuitBoard uid={uid} reduced={reduced} hot={hotChip} />
        </div>

        <button type="button" className="mfl-float-tile" aria-label="Send a signal to the device" onClick={press}>
          <span style={{ transform: "rotate(" + spin * 60 + "deg)" }}>
            <Asterisk size={20} color={pal.ink} />
          </span>
        </button>

        <div className="mfl-hero-head">
          {backer && (
            <p className="mfl-backer mfl-in" style={{ animationDelay: "60ms" }}>
              {backer.prefix ?? "Backed by"}
              <span className="mfl-backer-mark" aria-hidden="true">
                {backer.mark ?? backer.name.slice(0, 1)}
              </span>
              <b>{backer.name}</b>
            </p>
          )}
          <h1 className="mfl-h1">{two(title, "mfl-in")}</h1>
          {subtitle && (
            <p className="mfl-sub mfl-in" style={{ animationDelay: "260ms" }}>
              {subtitle}
            </p>
          )}
          <div className="mfl-cta-row mfl-in" style={{ animationDelay: "340ms" }}>
            <a className="mfl-btn mfl-btn--brand" href={primaryAction.href || "#"} onClick={(e) => go(primaryAction.href, e)}>
              {primaryAction.label}
            </a>
            {secondaryAction.href ? (
              <a className="mfl-btn mfl-btn--white" href={secondaryAction.href} onClick={(e) => go(secondaryAction.href, e)}>
                {secondaryAction.label}
              </a>
            ) : (
              <button type="button" className="mfl-btn mfl-btn--white" onClick={() => setDemoOpen(true)}>
                {secondaryAction.label}
              </button>
            )}
          </div>
        </div>

        <div className="mfl-stage">
          <div className="mfl-rings" key={pulse} aria-hidden="true">
            <i />
            <i />
            <i />
          </div>
          <div className="mfl-device" ref={deviceRef}>
            <button type="button" className="mfl-device-btn" aria-label="Press the device" onClick={press}>
              <span className="mfl-device-float">
                <Device uid={uid} pulse={pulse} />
              </span>
            </button>
            <span className="mfl-device-shadow" aria-hidden="true" />
            <span className="mfl-callout" aria-hidden="true">
              <span className="mfl-live" />
              {pulse ? "Synced just now" : "Auto-sync · live"}
            </span>
          </div>

          <div className="mfl-hero-foot">
            {info && (
              <div className="mfl-info mfl-in" style={{ animationDelay: "480ms" }}>
                {info.label && (
                  <p className="mfl-info-k">
                    <Asterisk size={10} /> {info.label}
                  </p>
                )}
                <p className="mfl-info-t">{two(info.text)}</p>
              </div>
            )}
            {statCards.length > 0 && (
              <div className="mfl-cards mfl-in" style={{ animationDelay: "560ms" }}>
                {statCards.slice(0, 2).map((c, i) => (
                  <StatCard key={c.title + i} card={c} />
                ))}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* -------------------------------------------------------- night */}
      <main className="mfl-night">
        {about && (
          <section className="mfl-about" data-sec="about" aria-labelledby={uid + "-about"}>
            <p className="mfl-badge mfl-rise" id={uid + "-about"}>
              <Asterisk size={10} /> {about.kicker ?? "About us"}
            </p>
            <p className="mfl-statement" ref={statementRef}>
              {tokens.map((w, i) => {
                const on = i < lit
                if (w === "{mark}")
                  return (
                    <span key={i} className={"mfl-trio" + (on ? " is-on" : "")} aria-hidden="true">
                      <i>
                        <Asterisk size={14} color="#efe9df" />
                      </i>
                      <i>
                        <Asterisk size={14} color="#2a1411" />
                      </i>
                      <i>
                        <Asterisk size={14} color="#2a1411" />
                      </i>{" "}
                    </span>
                  )
                return (
                  <span key={i} className={"mfl-w" + (on ? " is-on" : "")}>
                    {w}{" "}
                  </span>
                )
              })}
            </p>
            {about.stats && about.stats.length > 0 && (
              <div className="mfl-stats" ref={statsRef}>
                {about.stats.map((s) => (
                  <div className="mfl-statnum mfl-rise" key={s.label}>
                    <p className="mfl-statnum-v">
                      {s.prefix}
                      {formatCount(s.value * counts, s.decimals ?? 0)}
                      {s.suffix}
                    </p>
                    <p className="mfl-statnum-l">{s.label}</p>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {features && (
          <section className="mfl-feat" data-sec="features" aria-labelledby={uid + "-feat"} ref={satinRef} onPointerMove={onSatinMove}>
            <div className="mfl-feat-bg" aria-hidden="true">
              <Satin uid={uid} />
              <span className="mfl-feat-light" />
            </div>
            <div className="mfl-feat-in">
              <p className="mfl-badge mfl-rise">
                <Asterisk size={10} /> {features.kicker ?? "Our features"}
              </p>
              <h2 className="mfl-h2 mfl-rise" id={uid + "-feat"}>
                {two(features.title)}
              </h2>
              {features.subtitle && <p className="mfl-feat-sub mfl-rise">{features.subtitle}</p>}
              <div className="mfl-fcards">
                {wallet && (
                  <article className="mfl-fcard mfl-rise">
                    <div className="mfl-fmedia">
                      <Satin uid={uid} variant={1} />
                      <span className="mfl-flare" aria-hidden="true" />
                      <WalletWidget wallets={wallets} growth={wallet.growth ?? ""} uid={uid} />
                    </div>
                    <h3>{wallet.title ?? "Multi-Currency Wallet"}</h3>
                    {wallet.description && <p>{wallet.description}</p>}
                  </article>
                )}
                {spending && (
                  <article className="mfl-fcard mfl-rise">
                    <div className="mfl-fmedia">
                      <Satin uid={uid} variant={2} />
                      <span className="mfl-flare mfl-flare--r" aria-hidden="true" />
                      <SpendingWidget grid={grid} budget={spending.budget ?? 50000} />
                    </div>
                    <h3>{spending.title ?? "Profit & Loss Tracking"}</h3>
                    {spending.description && <p>{spending.description}</p>}
                  </article>
                )}
              </div>
            </div>
          </section>
        )}

        {cta && (
          <section className="mfl-cta" data-sec="contact" aria-labelledby={uid + "-cta"}>
            <div className="mfl-cta-mark mfl-rise" aria-hidden="true">
              <Asterisk size={28} color={pal.cream} />
            </div>
            <h2 className="mfl-h2 mfl-rise" id={uid + "-cta"}>
              {two(cta.title)}
            </h2>
            {cta.subtitle && <p className="mfl-feat-sub mfl-rise">{cta.subtitle}</p>}
            <div className="mfl-cta-row mfl-rise">
              {cta.action && (
                <a className="mfl-btn mfl-btn--cream" href={cta.action.href || "#"} onClick={(e) => go(cta.action?.href, e)}>
                  {cta.action.label}
                </a>
              )}
              <button type="button" className="mfl-btn mfl-btn--ghost" onClick={() => setDemoOpen(true)}>
                Launch Demo
              </button>
            </div>
          </section>
        )}

        {footer && (
          <footer className="mfl-foot">
            <div className="mfl-foot-top">
              <div className="mfl-foot-brand">
                <span className="mfl-logo">
                  {mark}
                  <span>
                    {brandWord}
                    {brandDot && <span className="mfl-dot">.</span>}
                  </span>
                </span>
                {footer.note && <p>{footer.note}</p>}
              </div>
              {(footer.columns ?? []).map((c) => (
                <div className="mfl-foot-col" key={c.title}>
                  <p>{c.title}</p>
                  <ul>
                    {c.links.map((l) => (
                      <li key={l.label}>
                        <a href={l.href || "#"} onClick={(e) => go(l.href || "#", e)}>
                          {l.label}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <p className="mfl-wordmark" aria-hidden="true">
              {brandWord}
              {brandDot && <span>.</span>}
            </p>
            <div className="mfl-foot-bot">
              <span>
                © {new Date().getFullYear()} {brandWord}. All rights reserved.
              </span>
              <span className="mfl-foot-soc">
                {(footer.socials ?? []).map((s) => (
                  <a key={s.label} href={s.href || "#"} onClick={(e) => go(s.href || "#", e)}>
                    {s.label}
                  </a>
                ))}
              </span>
            </div>
          </footer>
        )}
      </main>

      <DemoDialog open={demoOpen} onClose={closeDemo} brand={brand} onRequestDemo={onRequestDemo} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// styles — scoped to .mfl-*; colours come from the palette variables above
// ---------------------------------------------------------------------------

const MFL_CSS = `
.mfl-root{position:relative;background:var(--mfl-frame);color:var(--mfl-ink);padding:14px 14px 0;overflow-x:clip;font-family:"Inter Tight","Inter","Geist",ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;line-height:1.4;font-feature-settings:"ss01","cv11"}
.mfl-root :where(button){font:inherit;color:inherit;background:none;border:0;padding:0;margin:0;cursor:pointer;text-align:inherit}
.mfl-root :where(a){color:inherit;text-decoration:none}
.mfl-root :where(p,h1,h2,h3,ul){margin:0;padding:0}
.mfl-root :where(ul){list-style:none}
.mfl-root :where(input,select){font:inherit;color:inherit}
.mfl-root :where(button,a,input,select,[tabindex]):focus-visible{outline:2px solid var(--mfl-glow);outline-offset:2px;border-radius:6px}
.mfl-svg{display:block;max-width:none;flex:none}

/* ---- buttons ---- */
.mfl-btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;height:44px;padding:0 22px;border-radius:3px;font-size:14px;font-weight:500;letter-spacing:-.01em;transition:transform .25s cubic-bezier(.2,.8,.2,1),background-color .25s,box-shadow .25s,color .25s;white-space:nowrap}
.mfl-btn:active{transform:scale(.97)}
.mfl-btn--sm{height:38px;padding:0 18px;font-size:13px}
.mfl-btn--brand{background:var(--mfl-brand);color:#fff;box-shadow:inset 0 1px 0 rgba(255,255,255,.14),0 1px 2px rgba(0,0,0,.18)}
.mfl-btn--brand:hover{background:color-mix(in srgb,var(--mfl-brand) 86%,#000);box-shadow:inset 0 1px 0 rgba(255,255,255,.14),0 8px 22px -8px color-mix(in srgb,var(--mfl-brand) 70%,transparent)}
.mfl-btn--white{background:#fff;color:var(--mfl-ink);box-shadow:0 1px 2px rgba(0,0,0,.08)}
.mfl-btn--white:hover{box-shadow:0 8px 22px -10px rgba(0,0,0,.35)}
.mfl-btn--cream{background:var(--mfl-cream);color:var(--mfl-night)}
.mfl-btn--cream:hover{background:#fff}
.mfl-btn--ghost{color:var(--mfl-cream);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--mfl-cream) 30%,transparent)}
.mfl-btn--ghost:hover{box-shadow:inset 0 0 0 1px var(--mfl-cream)}
.mfl-btn--wide{width:100%}
.mfl-btn[disabled]{opacity:.7;cursor:progress}

/* ---- nav ---- */
.mfl-nav{position:sticky;top:0;z-index:40;display:flex;justify-content:space-between;align-items:flex-start;padding:10px 10px 0;height:58px;margin-bottom:-58px;pointer-events:none}
.mfl-nav>*{pointer-events:auto}
.mfl-nav-l{position:relative}
.mfl-nav-r{display:flex;gap:6px}
.mfl-root[data-scrolled] .mfl-nav{padding-top:8px}
.mfl-root[data-scrolled] .mfl-logo-pill,.mfl-root[data-scrolled] .mfl-nav-r .mfl-btn{box-shadow:0 10px 30px -12px rgba(0,0,0,.45)}
.mfl-logo-pill{display:flex;align-items:center;gap:20px;height:38px;padding:0 4px 0 10px;border-radius:5px;background:color-mix(in srgb,var(--mfl-paper) 70%,#c9c2b4);backdrop-filter:blur(8px);transition:box-shadow .3s}
.mfl-logo{display:inline-flex;align-items:center;gap:7px;font-size:15px;font-weight:600;letter-spacing:-.03em;color:var(--mfl-ink)}
.mfl-logo-mark{display:grid;place-items:center;width:20px;height:20px;border-radius:5px;background:var(--mfl-ink)}
.mfl-dot{color:var(--mfl-brand)}
.mfl-burger{position:relative;width:30px;height:30px;border-radius:3px;background:var(--mfl-brand);display:grid;place-items:center;transition:background-color .2s}
.mfl-burger i{position:absolute;left:9px;right:9px;height:1.4px;background:#fff;border-radius:2px;transition:transform .3s cubic-bezier(.2,.8,.2,1),top .3s}
.mfl-burger i:nth-child(1){top:12px}
.mfl-burger i:nth-child(2){top:17px}
.mfl-burger.is-open i:nth-child(1){top:14.5px;transform:rotate(45deg)}
.mfl-burger.is-open i:nth-child(2){top:14.5px;transform:rotate(-45deg)}
.mfl-dropdown{position:absolute;left:0;top:44px;width:260px;padding:6px;border-radius:8px;background:var(--mfl-night);color:var(--mfl-cream);box-shadow:0 24px 60px -20px rgba(0,0,0,.6);transform-origin:top left;animation:mfl-pop .28s cubic-bezier(.2,.8,.2,1)}
.mfl-dropdown li{animation:mfl-rise .35s cubic-bezier(.2,.8,.2,1) backwards}
.mfl-dropdown a{display:flex;align-items:center;gap:12px;padding:12px 12px;border-radius:5px;font-size:20px;letter-spacing:-.03em;transition:background-color .2s}
.mfl-dropdown a svg{margin-left:auto;opacity:0;transform:translate(-4px,4px);transition:opacity .2s,transform .25s}
.mfl-dropdown a:hover{background:rgba(255,255,255,.06)}
.mfl-dropdown a:hover svg{opacity:1;transform:none}
.mfl-dd-n{font-size:10px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;opacity:.45;letter-spacing:0}
.mfl-dd-foot{display:flex;align-items:center;gap:8px;margin-top:4px;padding:10px 12px 6px;border-top:1px solid rgba(255,255,255,.08);font-size:11px;opacity:.6}
.mfl-live{width:6px;height:6px;border-radius:50%;background:#7bd389;box-shadow:0 0 0 0 rgba(123,211,137,.6);animation:mfl-ping 2s infinite}

/* ---- hero ---- */
.mfl-hero{position:relative;display:flex;flex-direction:column;background:var(--mfl-paper);border-radius:4px 4px 0 0;overflow:hidden;isolation:isolate}
.mfl-circuit-wrap{position:absolute;inset:0;z-index:0;pointer-events:none}
.mfl-circuit{position:absolute;inset:0;width:100%;height:100%}
.mfl-trace{fill:none;stroke:var(--mfl-ink);stroke-opacity:.13;stroke-width:1.4}
.mfl-pulse{fill:none;stroke-width:2.2;stroke-linecap:round;stroke-dasharray:70 930;animation:mfl-run 6s linear infinite}
.mfl-chip rect{fill:var(--mfl-paper);stroke:var(--mfl-ink);stroke-opacity:.16;stroke-width:1.2;transition:fill .3s,stroke .3s,stroke-opacity .3s}
.mfl-chip text{font-size:13px;fill:var(--mfl-ink);fill-opacity:.35;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;transition:fill .3s,fill-opacity .3s}
.mfl-chip.is-hot rect{fill:#fff;stroke:var(--mfl-brand);stroke-opacity:.8}
.mfl-chip.is-hot text{fill:var(--mfl-brand);fill-opacity:1}
.mfl-float-tile{position:absolute;z-index:3;top:34%;right:14%;width:46px;height:46px;display:grid;place-items:center;border-radius:9px;background:linear-gradient(180deg,#fff,#f1ede6);box-shadow:0 1px 0 #fff inset,0 14px 30px -12px rgba(40,20,10,.45),0 0 0 1px rgba(0,0,0,.04);animation:mfl-bob 5s ease-in-out infinite}
.mfl-float-tile span{display:block;transition:transform .6s cubic-bezier(.3,1.6,.4,1)}
.mfl-float-tile:hover{box-shadow:0 1px 0 #fff inset,0 18px 34px -12px rgba(40,20,10,.55),0 0 0 1px color-mix(in srgb,var(--mfl-brand) 40%,transparent)}
.mfl-hero-head{position:relative;z-index:2;display:flex;flex-direction:column;align-items:center;text-align:center;padding:96px 20px 0}
.mfl-backer{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--mfl-ink);margin-bottom:22px}
.mfl-backer b{font-weight:500}
.mfl-backer-mark{display:inline-grid;place-items:center;width:16px;height:16px;border-radius:2px;background:#f26522;color:#fff;font-size:10px;font-weight:700;margin-left:2px}
.mfl-h1{font-size:clamp(42px,6.2vw,92px);line-height:.98;font-weight:400;letter-spacing:-.055em;color:var(--mfl-ink)}
.mfl-line{display:block}
.mfl-mute{color:var(--mfl-muted)}
.mfl-h1 .mfl-line:nth-child(1){animation-delay:120ms}
.mfl-h1 .mfl-line:nth-child(2){animation-delay:190ms}
.mfl-sub{max-width:300px;margin-top:22px;font-size:14px;line-height:1.45;color:var(--mfl-muted)}
.mfl-cta-row{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin-top:22px}
.mfl-in{animation:mfl-rise .9s cubic-bezier(.2,.8,.2,1) backwards}
.mfl-stage{position:relative;flex:1;min-height:360px;display:flex;flex-direction:column;justify-content:flex-end}
.mfl-device{position:absolute;z-index:1;left:50%;bottom:24px;width:clamp(230px,24vw,330px);aspect-ratio:1;transform:translateX(-50%);perspective:900px;--mfl-rx:0deg;--mfl-ry:0deg}
.mfl-device-btn{display:block;width:100%;height:100%;border-radius:40%;transform:rotateX(var(--mfl-rx)) rotateY(var(--mfl-ry));transform-style:preserve-3d;transition:transform .5s cubic-bezier(.2,.8,.2,1)}
.mfl-device-btn:active{transform:rotateX(var(--mfl-rx)) rotateY(var(--mfl-ry)) scale(.96)}
.mfl-device-float{display:block;width:100%;height:100%;animation:mfl-float 6s ease-in-out infinite,mfl-drop 1.1s cubic-bezier(.2,.8,.2,1) .2s backwards}
.mfl-device-svg{width:100%;height:100%;filter:drop-shadow(0 30px 30px rgba(40,25,15,.28)) drop-shadow(0 6px 8px rgba(40,25,15,.18))}
.mfl-device-shadow{position:absolute;left:18%;right:18%;bottom:-6%;height:12%;border-radius:50%;background:radial-gradient(closest-side,rgba(40,25,15,.32),transparent);z-index:-1;animation:mfl-shadow 6s ease-in-out infinite}
.mfl-led{animation:mfl-led 1.6s ease-out}
.mfl-callout{position:absolute;left:-34%;top:16%;display:inline-flex;align-items:center;gap:7px;height:28px;padding:0 11px;border-radius:999px;background:rgba(255,255,255,.72);backdrop-filter:blur(8px);box-shadow:0 10px 24px -14px rgba(40,20,10,.5),0 0 0 1px rgba(0,0,0,.04);font-size:11.5px;color:var(--mfl-ink);white-space:nowrap;animation:mfl-bob 7s ease-in-out infinite,mfl-rise .9s cubic-bezier(.2,.8,.2,1) .9s backwards;pointer-events:none}
.mfl-rings{position:absolute;left:50%;bottom:calc(24px + clamp(230px,24vw,330px)/2);width:0;height:0;z-index:0}
.mfl-rings i{position:absolute;left:-160px;top:-160px;width:320px;height:320px;border-radius:50%;border:1px solid color-mix(in srgb,var(--mfl-brand) 45%,transparent);opacity:0;animation:mfl-ring 1.8s cubic-bezier(.2,.8,.2,1)}
.mfl-rings i:nth-child(2){animation-delay:.18s}
.mfl-rings i:nth-child(3){animation-delay:.36s}
.mfl-hero-foot{position:relative;z-index:2;display:flex;justify-content:space-between;align-items:flex-end;gap:24px;padding:0 20px 20px}
.mfl-hero-foot{pointer-events:none}
.mfl-hero-foot>*{pointer-events:auto}
.mfl-info{max-width:380px}
.mfl-info-k{display:flex;align-items:center;gap:6px;font-size:11px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--mfl-muted);margin-bottom:12px}
.mfl-info-t{font-size:clamp(17px,1.55vw,22px);line-height:1.18;letter-spacing:-.025em;color:var(--mfl-ink)}
.mfl-info-t .mfl-line{display:inline}
.mfl-cards{display:flex;gap:8px}

/* ---- hero stat cards ---- */
.mfl-stat{width:272px;padding:12px;border-radius:6px;background:var(--mfl-card);color:var(--mfl-cream);box-shadow:0 30px 50px -28px rgba(0,0,0,.6),inset 0 1px 0 rgba(255,255,255,.06);transition:transform .35s cubic-bezier(.2,.8,.2,1)}
.mfl-stat:hover{transform:translateY(-4px)}
.mfl-stat-top{display:flex;justify-content:space-between;gap:8px}
.mfl-stat-t{font-size:12px;font-weight:500;letter-spacing:-.01em}
.mfl-stat-d{font-size:9.5px;opacity:.55;margin-top:2px}
.mfl-stat-tools{display:flex;align-items:flex-start;gap:4px}
.mfl-ico{display:grid;place-items:center;width:22px;height:22px;border-radius:4px;background:rgba(255,255,255,.08)}
.mfl-stat-amt{font-size:22px;letter-spacing:-.03em;margin-top:12px;animation:mfl-swap .45s cubic-bezier(.2,.8,.2,1)}
.mfl-stat-chg{display:flex;align-items:center;gap:6px;font-size:10px;margin-top:6px;color:color-mix(in srgb,var(--mfl-cream) 60%,transparent)}
.mfl-chg{display:inline-flex;align-items:center;gap:4px;padding:3px 6px;border-radius:3px;background:color-mix(in srgb,var(--mfl-brand) 70%,#fff 6%);color:#fff;font-weight:500}
.mfl-chg.is-down{background:rgba(255,255,255,.1)}
.mfl-stat-split{display:flex;align-items:center;gap:12px;margin-top:12px;padding-top:10px;border-top:1px solid rgba(255,255,255,.07)}
.mfl-donut{flex:none}
.mfl-arc{transition:stroke-width .25s,opacity .25s;cursor:pointer}
.mfl-arc.is-dim{opacity:.35}
.mfl-donut-t{font-size:9px;fill:var(--mfl-cream);font-weight:500}
.mfl-legend{flex:1;min-width:0}
.mfl-legend-h{font-size:9.5px;font-weight:500;margin-bottom:5px}
.mfl-legend ul{display:grid;grid-template-columns:1fr 1fr;gap:4px 8px}
.mfl-legend li{display:grid;grid-template-columns:6px 1fr;column-gap:5px;font-size:8.5px;line-height:1.25;transition:opacity .25s;cursor:default}
.mfl-legend li.is-dim{opacity:.35}
.mfl-legend li i{width:6px;height:6px;border-radius:50%;margin-top:2px}
.mfl-legend li span{opacity:.6;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mfl-legend li b{grid-column:2;font-weight:500}

/* ---- menu select ---- */
.mfl-menu{position:relative}
.mfl-menu-btn{display:inline-flex;align-items:center;gap:6px;height:22px;padding:0 7px;border-radius:4px;font-size:10px;white-space:nowrap;transition:background-color .2s}
.mfl-menu--dark .mfl-menu-btn{background:rgba(255,255,255,.1);color:var(--mfl-cream)}
.mfl-menu--dark .mfl-menu-btn:hover{background:rgba(255,255,255,.18)}
.mfl-menu--light .mfl-menu-btn{height:26px;background:#fff;color:#1c1412;box-shadow:inset 0 0 0 1px rgba(0,0,0,.09);font-size:11px}
.mfl-menu--light .mfl-menu-btn:hover{box-shadow:inset 0 0 0 1px rgba(0,0,0,.2)}
.mfl-chev{transition:transform .25s}
.mfl-chev.is-open{transform:rotate(180deg)}
.mfl-menu-list{position:absolute;right:0;top:calc(100% + 4px);z-index:20;min-width:120px;padding:4px;border-radius:7px;outline:none;animation:mfl-pop .2s cubic-bezier(.2,.8,.2,1);transform-origin:top right}
.mfl-menu--dark .mfl-menu-list{background:#1d0d0b;color:var(--mfl-cream);box-shadow:0 16px 40px -10px rgba(0,0,0,.7),0 0 0 1px rgba(255,255,255,.06)}
.mfl-menu--light .mfl-menu-list{background:#fff;color:#1c1412;box-shadow:0 16px 40px -10px rgba(0,0,0,.35),0 0 0 1px rgba(0,0,0,.06)}
.mfl-menu-opt{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:7px 8px;border-radius:4px;font-size:11px;cursor:pointer}
.mfl-menu--dark .mfl-menu-opt.is-active{background:rgba(255,255,255,.08)}
.mfl-menu--light .mfl-menu-opt.is-active{background:#f2efe9}

/* ---- night ---- */
.mfl-night{display:block;background:var(--mfl-night);color:var(--mfl-cream);padding:0 10px}
.mfl-about{padding:110px 16px 40px;text-align:center}
.mfl-badge{display:inline-flex;align-items:center;gap:6px;height:24px;padding:0 9px;border-radius:3px;background:var(--mfl-cream);color:var(--mfl-night);font-size:10.5px;font-weight:500;text-transform:uppercase;letter-spacing:.02em}
.mfl-badge--light{background:var(--mfl-paper);color:var(--mfl-ink)}
.mfl-statement{max-width:1000px;margin:40px auto 0;font-size:clamp(28px,3.9vw,54px);line-height:1.12;letter-spacing:-.04em;font-weight:400}
.mfl-w{color:color-mix(in srgb,var(--mfl-cream) 32%,transparent);transition:color .5s}
.mfl-w.is-on{color:var(--mfl-cream)}
.mfl-trio{display:inline-flex;vertical-align:-.12em;margin:0 .1em;opacity:.45;transition:opacity .5s}
.mfl-trio.is-on{opacity:1}
.mfl-trio i{display:grid;place-items:center;width:1.05em;height:.95em;border-radius:.2em;font-style:normal;transition:transform .45s cubic-bezier(.3,1.6,.4,1)}
.mfl-trio i:nth-child(1){background:#4a3a37;z-index:3}
.mfl-trio i:nth-child(2){background:#a29890;margin-left:-.28em;z-index:2}
.mfl-trio i:nth-child(3){background:#e9e3d8;margin-left:-.28em;z-index:1}
.mfl-trio i svg{width:.5em;height:.5em}
.mfl-trio:hover i:nth-child(1){transform:translate(-.12em,-.06em) rotate(-8deg)}
.mfl-trio:hover i:nth-child(3){transform:translate(.12em,-.06em) rotate(8deg)}
.mfl-stats{display:grid;grid-template-columns:repeat(3,1fr);max-width:1180px;margin:110px auto 0}
.mfl-statnum{padding:16px 12px 22px}
.mfl-statnum+.mfl-statnum{border-left:1px solid color-mix(in srgb,var(--mfl-cream) 22%,transparent)}
.mfl-statnum-v{font-size:clamp(38px,4.2vw,58px);font-weight:300;letter-spacing:-.04em;font-variant-numeric:tabular-nums;line-height:1}
.mfl-statnum-l{margin-top:16px;font-size:14px;color:color-mix(in srgb,var(--mfl-cream) 70%,transparent)}

/* ---- features ---- */
.mfl-feat{position:relative;margin:90px auto 0;max-width:1440px;border-radius:18px;overflow:hidden;isolation:isolate;--mfl-sx:80%;--mfl-sy:10%}
.mfl-feat-bg{position:absolute;inset:0;z-index:-1}
.mfl-satin{position:absolute;inset:0;width:100%;height:100%}
.mfl-satin-a{animation:mfl-satin-a 18s ease-in-out infinite alternate;transform-origin:50% 50%}
.mfl-satin-b{animation:mfl-satin-b 14s ease-in-out infinite alternate;transform-origin:0 50%}
.mfl-satin-c{animation:mfl-satin-b 16s ease-in-out infinite alternate-reverse;transform-origin:100% 50%}
.mfl-feat-light{position:absolute;inset:0;background:radial-gradient(520px circle at var(--mfl-sx) var(--mfl-sy),color-mix(in srgb,var(--mfl-sat-light) 20%,transparent),transparent 60%);mix-blend-mode:screen;transition:background .2s}
.mfl-feat-in{position:relative;display:flex;flex-direction:column;align-items:center;text-align:center;padding:64px 20px 72px}
.mfl-h2{margin-top:22px;font-size:clamp(34px,4.2vw,58px);line-height:1;letter-spacing:-.05em;font-weight:400;color:var(--mfl-cream)}
.mfl-h2 .mfl-mute{color:color-mix(in srgb,var(--mfl-cream) 50%,transparent)}
.mfl-feat-sub{margin-top:16px;font-size:14px;color:color-mix(in srgb,var(--mfl-cream) 72%,transparent);max-width:420px}
.mfl-fcards{display:flex;flex-wrap:wrap;justify-content:center;gap:16px;margin-top:44px;width:100%}
.mfl-fcard{width:min(100%,430px);padding:8px 8px 22px;border-radius:6px;background:var(--mfl-cream);color:var(--mfl-ink);box-shadow:0 40px 70px -40px rgba(0,0,0,.8);transition:transform .45s cubic-bezier(.2,.8,.2,1),box-shadow .45s}
.mfl-fcard:hover{transform:translateY(-6px);box-shadow:0 50px 80px -40px rgba(0,0,0,.9)}
.mfl-fmedia{position:relative;height:300px;border-radius:4px;overflow:hidden;display:grid;place-items:center;isolation:isolate}
.mfl-fmedia .mfl-satin{z-index:-2}
.mfl-flare{position:absolute;z-index:-1;right:-30px;top:-40px;width:160px;height:220px;border-radius:50%;background:radial-gradient(closest-side,color-mix(in srgb,var(--mfl-glow) 85%,transparent),color-mix(in srgb,var(--mfl-glow) 30%,transparent) 50%,transparent);filter:blur(6px);transform:rotate(24deg);animation:mfl-flare 7s ease-in-out infinite alternate}
.mfl-flare--r{left:-40px;right:auto;top:auto;bottom:-60px}
.mfl-fcard h3{margin-top:18px;font-size:16px;font-weight:500;letter-spacing:-.02em}
.mfl-fcard>p{margin:8px auto 0;max-width:330px;font-size:12px;line-height:1.5;color:var(--mfl-muted)}

/* ---- widgets ---- */
.mfl-panel{width:min(calc(100% - 40px),300px);padding:12px;border-radius:7px;background:#fbfaf7;color:#1c1412;text-align:left;box-shadow:0 24px 50px -20px rgba(0,0,0,.6),0 0 0 1px rgba(0,0,0,.04);transition:transform .45s cubic-bezier(.2,.8,.2,1)}
.mfl-fcard:hover .mfl-panel{transform:scale(1.02)}
.mfl-panel-row{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
.mfl-panel-k{font-size:10px;color:#6e655e}
.mfl-wallet-total{font-size:22px;letter-spacing:-.035em;margin-top:2px;font-variant-numeric:tabular-nums;animation:mfl-swap .45s cubic-bezier(.2,.8,.2,1)}
.mfl-wallet-g{font-size:9px;color:#3d8c56;margin-top:2px}
.mfl-wallet-h{margin-top:12px;font-size:10px;font-weight:500;align-items:center}
.mfl-link{font-size:10px;color:#1c1412;text-decoration:underline;text-underline-offset:2px}
.mfl-cur{display:inline-flex;align-items:center;gap:5px;font-size:10px;font-weight:500}
.mfl-wallet-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:6px}
.mfl-wtile{display:flex;flex-direction:column;gap:3px;padding:8px;border-radius:5px;background:#f2efea;transition:background-color .2s,box-shadow .2s,transform .2s;animation:mfl-swap .4s cubic-bezier(.2,.8,.2,1)}
.mfl-wtile:hover{background:#ebe6df}
.mfl-wtile.is-sel{background:#fff;box-shadow:0 0 0 1px color-mix(in srgb,var(--mfl-brand) 55%,transparent),0 6px 14px -8px rgba(0,0,0,.3)}
.mfl-wtile b{font-size:12.5px;font-weight:500;letter-spacing:-.02em;font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mfl-wtile em{font-style:normal;font-size:8.5px;color:#3d8c56}
.mfl-wtile em.is-off{color:#9b8f86}
.mfl-flag{border-radius:50%}
.mfl-spend-sum{margin-top:12px;align-items:flex-end}
.mfl-spend-sum b{font-size:20px;font-weight:400;letter-spacing:-.035em;font-variant-numeric:tabular-nums;display:inline-block;animation:mfl-swap .45s cubic-bezier(.2,.8,.2,1)}
.mfl-spend-sum p span{font-size:9px;color:#8a8079;white-space:nowrap}
.mfl-spend-legend{display:flex;gap:8px;font-size:8.5px;color:#6e655e;padding-bottom:4px}
.mfl-spend-legend span{display:inline-flex;align-items:center;gap:3px}
.mfl-spend-legend i{width:7px;height:7px;border-radius:2px}
.mfl-meter{height:3px;margin-top:8px;border-radius:3px;background:#ece8e2;overflow:hidden}
.mfl-meter i{display:block;height:100%;background:var(--mfl-brand);border-radius:3px;transition:width .6s cubic-bezier(.2,.8,.2,1)}
.mfl-heat{display:grid;gap:4px;margin-top:10px}
.mfl-heat-col{display:grid;gap:4px;justify-items:center}
.mfl-cell{width:100%;aspect-ratio:1;max-width:22px;border-radius:4px;transition:transform .2s,box-shadow .2s;animation:mfl-cell .5s cubic-bezier(.2,.8,.2,1) backwards}
.mfl-cell:hover,.mfl-cell.is-on{transform:scale(1.18);box-shadow:0 0 0 1.5px #fbfaf7,0 0 0 3px var(--mfl-brand)}
.mfl-root .lv0{background:#ebe8e3}
.mfl-root .lv1{background:#d3cec7}
.mfl-root .lv2{background:#a8a29b}
.mfl-root .lv3{background:#5e5752}
.mfl-root .lv4{background:#221d1b}
.mfl-heat-m{font-size:7.5px;color:#8a8079;margin-top:1px}
.mfl-heat-tip{margin-top:8px;min-height:14px;font-size:9.5px;color:#6e655e}
.mfl-heat-tip b{color:#1c1412;font-weight:500}

/* ---- cta + footer ---- */
.mfl-cta{display:flex;flex-direction:column;align-items:center;text-align:center;padding:130px 16px 110px}
.mfl-cta-mark{display:grid;place-items:center;width:58px;height:58px;border-radius:14px;background:var(--mfl-brand);box-shadow:inset 0 1px 0 rgba(255,255,255,.18),0 20px 40px -18px rgba(0,0,0,.7)}
.mfl-cta-mark svg{animation:mfl-spin 14s linear infinite}
.mfl-cta .mfl-cta-row{margin-top:30px}
.mfl-foot{max-width:1440px;margin:0 auto;padding:56px 16px 22px;border-top:1px solid color-mix(in srgb,var(--mfl-cream) 12%,transparent)}
.mfl-foot-top{display:grid;grid-template-columns:2fr repeat(3,1fr);gap:28px}
.mfl-foot .mfl-logo{color:var(--mfl-cream)}
.mfl-foot .mfl-logo-mark{background:var(--mfl-brand)}
.mfl-foot-brand p{margin-top:14px;max-width:240px;font-size:12.5px;color:color-mix(in srgb,var(--mfl-cream) 55%,transparent)}
.mfl-foot-col p{font-size:12px;color:color-mix(in srgb,var(--mfl-cream) 50%,transparent);margin-bottom:12px}
.mfl-foot-col li+li{margin-top:8px}
.mfl-foot-col a,.mfl-foot-soc a{font-size:14px;color:var(--mfl-cream);background:linear-gradient(currentColor,currentColor) 0 100%/0 1px no-repeat;transition:background-size .3s}
.mfl-foot-col a:hover,.mfl-foot-soc a:hover{background-size:100% 1px}
.mfl-wordmark{margin-top:56px;font-size:clamp(80px,19vw,300px);line-height:.8;letter-spacing:-.07em;font-weight:500;color:color-mix(in srgb,var(--mfl-cream) 8%,transparent);user-select:none;white-space:nowrap}
.mfl-wordmark span{color:color-mix(in srgb,var(--mfl-brand) 70%,transparent)}
.mfl-foot-bot{display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-top:20px;padding-top:16px;border-top:1px solid color-mix(in srgb,var(--mfl-cream) 10%,transparent);font-size:12px;color:color-mix(in srgb,var(--mfl-cream) 50%,transparent)}
.mfl-foot-soc{display:flex;gap:16px}
.mfl-foot-soc a{font-size:12px}

/* ---- dialog ---- */
.mfl-modal{position:fixed;inset:0;z-index:100;display:grid;place-items:center;padding:16px;background:rgba(20,8,6,.55);backdrop-filter:blur(6px);animation:mfl-fade .25s ease}
.mfl-dialog{position:relative;width:min(100%,440px);max-height:calc(100svh - 32px);overflow:auto;padding:28px;border-radius:12px;background:var(--mfl-paper);color:var(--mfl-ink);box-shadow:0 40px 100px -30px rgba(0,0,0,.7);animation:mfl-pop .35s cubic-bezier(.2,.8,.2,1)}
.mfl-dialog h2{margin-top:16px;font-size:28px;line-height:1.05;letter-spacing:-.045em;font-weight:400}
.mfl-dialog-sub{margin-top:8px;font-size:13px;color:var(--mfl-muted)}
.mfl-dialog form{display:flex;flex-direction:column}
.mfl-dialog label{display:flex;flex-direction:column;gap:6px;margin-top:14px;font-size:12px;font-weight:500;flex:1}
.mfl-dialog input,.mfl-dialog select{height:42px;padding:0 12px;border-radius:5px;border:1px solid color-mix(in srgb,var(--mfl-ink) 14%,transparent);background:#fbfaf7;font-size:14px;font-weight:400;outline:none;transition:border-color .2s,box-shadow .2s;width:100%;box-sizing:border-box}
.mfl-dialog input:focus,.mfl-dialog select:focus{border-color:var(--mfl-brand);box-shadow:0 0 0 3px color-mix(in srgb,var(--mfl-brand) 18%,transparent)}
.mfl-dialog input[aria-invalid="true"]{border-color:#c0392b}
.mfl-dialog-row{display:flex;gap:10px}
.mfl-err{min-height:18px;margin:10px 0 6px;font-size:12px;color:#b03a2e}
.mfl-x{position:absolute;right:14px;top:14px;width:30px;height:30px;display:grid;place-items:center;border-radius:50%;transition:background-color .2s}
.mfl-x:hover{background:rgba(0,0,0,.06)}
.mfl-done{display:flex;flex-direction:column;align-items:center;text-align:center;padding:12px 0 4px}
.mfl-done-mark{display:grid;place-items:center;width:64px;height:64px;border-radius:16px;background:var(--mfl-brand);color:#fff;animation:mfl-pop .5s cubic-bezier(.3,1.6,.4,1)}
.mfl-done-mark svg{animation:mfl-spin 6s linear infinite}
.mfl-done p{margin:10px 0 22px;font-size:14px;color:var(--mfl-muted);max-width:320px}

/* ---- reveal ---- */
.mfl-rise{transition:opacity .9s cubic-bezier(.2,.8,.2,1),transform .9s cubic-bezier(.2,.8,.2,1)}
.mfl-rise.mfl-pre{opacity:0;transform:translateY(24px)}

/* ---- keyframes ---- */
@keyframes mfl-rise{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}
@keyframes mfl-pop{from{opacity:0;transform:scale(.94) translateY(-4px)}to{opacity:1;transform:none}}
@keyframes mfl-fade{from{opacity:0}to{opacity:1}}
@keyframes mfl-swap{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@keyframes mfl-run{from{stroke-dashoffset:1000}to{stroke-dashoffset:0}}
@keyframes mfl-bob{0%,100%{transform:translateY(0) rotate(-4deg)}50%{transform:translateY(-10px) rotate(3deg)}}
@keyframes mfl-float{0%,100%{transform:translateY(0) rotate(0deg)}50%{transform:translateY(-12px) rotate(1.5deg)}}
@keyframes mfl-shadow{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(.86);opacity:.7}}
@keyframes mfl-drop{from{opacity:0;transform:translateY(60px) scale(.9) rotate(-8deg)}to{opacity:1;transform:none}}
@keyframes mfl-led{0%{opacity:.35}25%{opacity:1;filter:brightness(1.6)}100%{opacity:1}}
@keyframes mfl-ring{0%{opacity:.9;transform:scale(.6)}100%{opacity:0;transform:scale(2.4)}}
@keyframes mfl-ping{0%{box-shadow:0 0 0 0 rgba(123,211,137,.6)}80%,100%{box-shadow:0 0 0 7px rgba(123,211,137,0)}}
@keyframes mfl-cell{from{opacity:0;transform:scale(.4)}to{opacity:1;transform:none}}
@keyframes mfl-spin{to{transform:rotate(360deg)}}
@keyframes mfl-flare{from{opacity:.75;transform:rotate(24deg) translateY(0)}to{opacity:1;transform:rotate(34deg) translateY(18px)}}
@keyframes mfl-satin-a{from{transform:translate(0,0) scale(1)}to{transform:translate(-30px,18px) scale(1.06)}}
@keyframes mfl-satin-b{from{transform:translate(0,0) scaleX(1)}to{transform:translate(12px,-10px) scaleX(1.15)}}

/* ---- small screens ---- */
@media (max-width:980px){
.mfl-hero-foot{flex-direction:column;align-items:stretch}
.mfl-cards{overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:4px;margin:0 -20px;padding-left:20px;padding-right:20px}
.mfl-stat{flex:none;scroll-snap-align:start}
.mfl-stage{min-height:0;padding-top:clamp(250px,40vw,360px)}
.mfl-device{top:20px;bottom:auto}
.mfl-rings{bottom:auto;top:calc(20px + clamp(230px,24vw,330px)/2)}
.mfl-float-tile{display:none}
.mfl-foot-top{grid-template-columns:1fr 1fr}
.mfl-foot-brand{grid-column:1/-1}
}
@media (max-width:640px){
.mfl-root{padding:8px 8px 0}
.mfl-nav{padding:8px 8px 0}
.mfl-nav-r .mfl-btn--brand{display:none}
.mfl-hero-head{padding-top:92px}
.mfl-stats{grid-template-columns:1fr;margin-top:70px}
.mfl-statnum+.mfl-statnum{border-left:0;border-top:1px solid color-mix(in srgb,var(--mfl-cream) 22%,transparent)}
.mfl-dialog-row{flex-direction:column;gap:0}
.mfl-callout{left:-10%;top:-6%}
.mfl-fmedia{height:310px}
}

/* ---- reduced motion ---- */
@media (prefers-reduced-motion:reduce){
.mfl-root *,.mfl-root *::before,.mfl-root *::after{animation:none !important;transition:none !important}
.mfl-rise.mfl-pre{opacity:1;transform:none}
}
`

type PointerEv = React.PointerEvent<HTMLElement>
type AnchorEv = React.MouseEvent<HTMLAnchorElement>
type ChangeEv = React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
type FormEv = React.FormEvent<HTMLFormElement>
