import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  AlertTriangle, ArrowRight, Banknote, Building2, Calendar, ChevronRight, CircleDollarSign,
  Database, FileText, Landmark, Layers, ListOrdered, Loader2, PieChart, Scale, Search, Send, ShieldCheck,
  Sparkles, ThumbsDown, ThumbsUp, TrendingUp, Users,
} from "lucide-react";
import { ipoApi, type IpoDetail, type IpoSummary } from "../services/api";
import { Tabs } from "../components/Tabs";
import "./ipo.css";

const DASH = "—";

function formatDate(iso?: string | null): string {
  if (!iso) return DASH;
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function crore(value?: number | null): string {
  if (value == null || !Number.isFinite(value)) return DASH;
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 1 })} Cr`;
}

function rupees(value?: number | null): string {
  if (value == null || !Number.isFinite(value)) return DASH;
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function priceBand(ipo: IpoSummary): string {
  if (ipo.price_band_low == null && ipo.price_band_high == null) return DASH;
  if (ipo.price_band_low === ipo.price_band_high) return rupees(ipo.price_band_low);
  return `${rupees(ipo.price_band_low)} – ${rupees(ipo.price_band_high)}`;
}

const STATUS_LABEL: Record<string, string> = { upcoming: "Upcoming", open: "Open now", closed: "Closed", listed: "Listed" };

function StatusPill({ status }: { status: string }) {
  return <span className={`ipo-status ipo-status-${status}`}>{status === "open" && <i className="ipo-status-dot" />}{STATUS_LABEL[status] ?? status}</span>;
}

// ---- List view ---------------------------------------------------------------

export function IpoListView({ onOpen }: { onOpen: (ipoId: string) => void }) {
  const [ipos, setIpos] = useState<IpoSummary[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    ipoApi.list("mainboard").then((data) => { if (!cancelled) setIpos(data); })
      .catch((cause) => { if (!cancelled) setError(cause instanceof Error ? cause.message : String(cause)); });
    return () => { cancelled = true; };
  }, []);

  return <div className="view-anim">
    <section className="hero">
      <div>
        <div className="hero-kicker"><Sparkles size={14} /> IPO CENTRE</div>
        <h1>Mainboard IPOs</h1>
        <p>Official listing details and the full report for each IPO, with a search bar that answers questions straight from that report - never a guess.</p>
      </div>
      <div className="hero-note"><ShieldCheck size={17} /><span>Every answer is grounded in the stored report text for that IPO.</span></div>
    </section>

    {error && <div className="error-panel"><AlertTriangle size={18} /><div><strong>Could not load IPOs</strong><span>{error}</span></div></div>}

    {ipos === null && !error && <div className="ipo-grid">{[0, 1, 2].map((i) => <div className="ipo-card skeleton" key={i} />)}</div>}

    {ipos && ipos.length === 0 && <div className="empty-state large">
      <div className="empty-icon"><Building2 size={22} /></div>
      <h2>No mainboard IPOs added yet</h2>
      <p>No IPO is open right now. Once listing details and the official report for an IPO are added, it will appear here - with its full financials and a search bar grounded in that exact report.</p>
    </div>}

    {ipos && ipos.length > 0 && <div className="ipo-grid">
      {ipos.map((ipo) => (
        <button type="button" className="ipo-card" key={ipo.ipo_id} onClick={() => onOpen(ipo.ipo_id)}>
          <div className="ipo-card-top">
            <span className="ipo-card-mono">{ipo.company_name.slice(0, 1).toUpperCase()}</span>
            <StatusPill status={ipo.status} />
          </div>
          <strong className="ipo-card-name">{ipo.company_name}</strong>
          <span className="ipo-card-sub">{ipo.symbol} · {ipo.exchange} · <span className="ipo-board">Mainboard</span></span>
          <div className="ipo-card-stats">
            <div><span>Price band</span><strong>{priceBand(ipo)}</strong></div>
            <div><span>Issue size</span><strong>{crore(ipo.issue_size_cr)}</strong></div>
            <div><span>Lot size</span><strong>{ipo.lot_size ?? DASH}</strong></div>
          </div>
          <div className="ipo-card-dates"><Calendar size={13} /><span>{formatDate(ipo.open_date)} – {formatDate(ipo.close_date)}</span></div>
          <div className="ipo-card-cta">View report & ask questions <ArrowRight size={14} /></div>
        </button>
      ))}
    </div>}
  </div>;
}

// ---- Detail view --------------------------------------------------------------

type DetailTab = string;

// Known payload sections, in display order. Any payload key not listed here
// still gets a tab (see sections below) - this list just gives the common
// ones a proper label and icon instead of a humanized guess.
const SECTION_META: { key: string; label: string; icon: ReactNode }[] = [
  { key: "financials", label: "Financials", icon: <TrendingUp size={15} /> },
  { key: "balance_sheet", label: "Balance sheet", icon: <Landmark size={15} /> },
  { key: "cash_flow", label: "Cash flow", icon: <Banknote size={15} /> },
  { key: "order_book", label: "Order book", icon: <ListOrdered size={15} /> },
  { key: "segments", label: "Revenue by segment", icon: <PieChart size={15} /> },
  { key: "valuation", label: "Valuation", icon: <CircleDollarSign size={15} /> },
  { key: "subscription", label: "Subscription", icon: <Users size={15} /> },
  { key: "objects_of_issue", label: "Objects of the issue", icon: <Layers size={15} /> },
  { key: "strengths", label: "Strengths", icon: <ThumbsUp size={15} /> },
  { key: "concerns", label: "Concerns", icon: <ThumbsDown size={15} /> },
  { key: "risk_factors", label: "Risk factors", icon: <AlertTriangle size={15} /> },
  { key: "verdict", label: "Verdict", icon: <Scale size={15} /> },
];

function humanizeKey(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Payload sections are freeform JSON (structure varies IPO to IPO), so they
 * render generically: a list of objects becomes a table, a list of strings
 * becomes a list, anything else is shown as label/value pairs. */
function PayloadSection({ data }: { data: unknown }) {
  if (data == null) return null;
  if (Array.isArray(data)) {
    if (data.length === 0) return null;
    if (typeof data[0] === "object" && data[0] !== null) {
      const columns = Object.keys(data[0] as Record<string, unknown>);
      return <div className="table-wrap"><table><thead><tr>{columns.map((c) => <th key={c}>{humanizeKey(c)}</th>)}</tr></thead>
        <tbody>{(data as Record<string, unknown>[]).map((row, i) => <tr key={i}>{columns.map((c) => <td key={c}>{String(row[c] ?? DASH)}</td>)}</tr>)}</tbody></table></div>;
    }
    return <ul className="ipo-list">{data.map((item, i) => <li key={i}>{String(item)}</li>)}</ul>;
  }
  if (typeof data === "object") {
    return <div className="ipo-kv">{Object.entries(data as Record<string, unknown>).map(([k, v]) => <div key={k}><span>{humanizeKey(k)}</span><strong>{String(v)}</strong></div>)}</div>;
  }
  return <p>{String(data)}</p>;
}

function AskPanel({ ipoId, hasReport }: { ipoId: string; hasReport: boolean }) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [thread, setThread] = useState<{ question: string; answer: string; grounded: boolean }[]>([]);

  const ask = async () => {
    const trimmed = question.trim();
    if (!trimmed || loading) return;
    setLoading(true); setError("");
    try {
      const res = await ipoApi.ask(ipoId, trimmed);
      setThread((t) => [...t, { question: trimmed, answer: res.answer, grounded: res.grounded }]);
      setQuestion("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally { setLoading(false); }
  };

  return <div className="ipo-ask">
    <div className="ipo-ask-label"><Search size={15} /><label htmlFor="ipo-ask-input">Ask anything about this IPO's report</label></div>
    <div className="ipo-ask-row">
      <input id="ipo-ask-input" value={question} placeholder={hasReport ? "e.g. What is the company's revenue growth over the last 3 years?" : "No report stored yet"}
        disabled={!hasReport || loading} onChange={(e) => setQuestion(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask()} />
      <button type="button" className="button button-primary" onClick={ask} disabled={!hasReport || loading || !question.trim()}>
        {loading ? <><Loader2 size={15} className="spin" /> Thinking</> : <><Send size={15} /> Ask</>}
      </button>
    </div>
    {!hasReport && <p className="ipo-ask-hint">The official report for this IPO hasn't been added yet, so there's nothing to search.</p>}
    {error && <div className="error-panel" style={{ marginTop: 12 }}><AlertTriangle size={16} /><div><strong>Couldn't answer</strong><span>{error}</span></div></div>}
    {thread.length > 0 && <div className="ipo-thread">
      {thread.map((turn, i) => <div className="ipo-turn" key={i}>
        <div className="ipo-turn-q"><span className="ipo-turn-avatar">Q</span>{turn.question}</div>
        <div className="ipo-turn-a">
          <span className="ipo-turn-avatar a">A</span>
          <div><p>{turn.answer}</p><span className="ipo-turn-tag"><ShieldCheck size={11} /> {turn.grounded ? "Answered from the stored report" : "Showing the most relevant excerpt"}</span></div>
        </div>
      </div>)}
    </div>}
  </div>;
}

export function IpoDetailView({ ipoId, onBack }: { ipoId: string; onBack: () => void }) {
  const [ipo, setIpo] = useState<IpoDetail | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<DetailTab>("ask");

  useEffect(() => {
    let cancelled = false;
    setIpo(null); setError("");
    ipoApi.get(ipoId).then((data) => { if (!cancelled) setIpo(data); })
      .catch((cause) => { if (!cancelled) setError(cause instanceof Error ? cause.message : String(cause)); });
    return () => { cancelled = true; };
  }, [ipoId]);

  const sections = useMemo(() => {
    if (!ipo) return [] as { id: DetailTab; label: string; icon: ReactNode; render: () => ReactNode }[];
    const payload = ipo.payload ?? {};
    const has = (k: string) => Array.isArray(payload[k]) ? (payload[k] as unknown[]).length > 0 : payload[k] != null && payload[k] !== "";
    const list: { id: DetailTab; label: string; icon: ReactNode; render: () => ReactNode }[] = [
      { id: "ask", label: "Ask", icon: <Search size={15} />, render: () => <AskPanel ipoId={ipo.ipo_id} hasReport={ipo.has_report} /> },
    ];
    if (ipo.about || has("overview")) list.push({ id: "overview", label: "Overview", icon: <FileText size={15} />, render: () => <article className="report-text"><p>{ipo.about}</p><PayloadSection data={payload.overview} /></article> });
    const known = new Set(SECTION_META.map((m) => m.key));
    for (const meta of SECTION_META) {
      if (has(meta.key)) list.push({ id: meta.key, label: meta.label, icon: meta.icon, render: () => <article className="report-text"><PayloadSection data={payload[meta.key]} /></article> });
    }
    // Anything the author added that isn't in SECTION_META still gets a tab,
    // so a new payload shape never silently disappears from the page.
    for (const key of Object.keys(payload)) {
      if (key === "overview" || known.has(key) || !has(key)) continue;
      list.push({ id: key, label: humanizeKey(key), icon: <Sparkles size={15} />, render: () => <article className="report-text"><PayloadSection data={payload[key]} /></article> });
    }
    return list;
  }, [ipo]);

  if (error) return <div className="view-anim"><div className="error-panel"><AlertTriangle size={18} /><div><strong>Could not load this IPO</strong><span>{error}</span></div></div></div>;
  if (!ipo) return <div className="view-anim"><div className="ipo-card skeleton" style={{ maxWidth: 640 }} /></div>;

  const activeSection = sections.find((s) => s.id === tab) ?? sections[0];

  return <div className="view-anim">
    <button type="button" className="ipo-back" onClick={onBack}><ChevronRight size={14} style={{ transform: "rotate(180deg)" }} /> All mainboard IPOs</button>
    <section className="results-heading ipo-detail-head">
      <div>
        <div className="company-line"><span className="company-monogram">{ipo.company_name.slice(0, 1).toUpperCase()}</span><span>{ipo.company_name}</span><StatusPill status={ipo.status} /></div>
        <h2>{ipo.symbol} · {ipo.exchange} <span className="ipo-board">Mainboard</span></h2>
        <p>Open {formatDate(ipo.open_date)} · Close {formatDate(ipo.close_date)} · Listing {formatDate(ipo.listing_date)}</p>
      </div>
    </section>

    <div className="metrics-strip ipo-metrics">
      <div className="metric"><span className="eyebrow">Price band</span><strong>{priceBand(ipo)}</strong><span className="metric-detail">per share</span></div>
      <div className="metric"><span className="eyebrow">Lot size</span><strong>{ipo.lot_size ?? DASH}</strong><span className="metric-detail">shares / lot</span></div>
      <div className="metric"><span className="eyebrow">Issue size</span><strong>{crore(ipo.issue_size_cr)}</strong><span className="metric-detail">{ipo.fresh_issue_cr != null && ipo.ofs_cr != null ? `${crore(ipo.fresh_issue_cr)} fresh + ${crore(ipo.ofs_cr)} OFS` : "total"}</span></div>
      <div className="metric"><span className="eyebrow">Face value</span><strong>{rupees(ipo.face_value)}</strong><span className="metric-detail">{ipo.registrar || "—"}</span></div>
    </div>

    {!ipo.has_report && <div className="notice-strip"><Database size={15} /><span>Listing details are in - the full report hasn't been added yet, so the Ask box has nothing to search.</span></div>}

    {sections.length > 0 && <Tabs label="IPO detail sections" active={tab} onChange={setTab} tabs={sections.map(({ id, label, icon }) => ({ id, label, icon }))} />}
    <div className="result-panel panel-anim" key={tab}>{activeSection?.render()}</div>
  </div>;
}
