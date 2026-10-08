import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import {
  AlertTriangle, ArrowLeft, ArrowRight, BadgeCheck, Building2, CheckCircle2, Eye, EyeOff, FileText, Layers,
  LoaderCircle, Lock, Mail, ScanSearch, Send, ShieldCheck, Sparkles, User,
} from "lucide-react";
import { authApi, publicApi, type OverviewCompany, type PublicOverview, type SessionUser } from "../services/api";
import { BrandMark } from "../components/Brand";
import { inr } from "../lib/format";
import { prefersReducedMotion, useCountUp } from "../lib/motion";
import "./login.css";

type Mode = "signin" | "signup";

const STORY_MS = 7000;

const FEATURES = [
  { icon: ScanSearch, title: "Verified reports", body: "Ask about any company and get a structured report where every claim is checked against the source it came from - by a verifier that never sees the report." },
  { icon: Layers, title: "Industry view", body: "India's top IT companies side by side - revenue, growth, margins and profitability, computed from their own reported results." },
  { icon: ShieldCheck, title: "Straight from the filings", body: "Figures come from companies' published financial results. When a filing contradicts itself, you see the correction - never a silent fix." },
];

const fmtDate = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "";

export function LoginPage({ onAuthenticated, initialMode = "signin" }: { onAuthenticated: (user: SessionUser) => void; initialMode?: Mode }) {
  const [overview, setOverview] = useState<PublicOverview | null>(null);
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    publicApi.overview().then(setOverview)
      .catch(() => setOverview({ companies: [], google_signin_available: false, email_signin_available: false }));
  }, []);

  const spotlight = (e: React.MouseEvent<HTMLElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty("--mx", `${e.clientX - box.left}px`);
    e.currentTarget.style.setProperty("--my", `${e.clientY - box.top}px`);
  };

  const finish = (user: SessionUser) => {
    // Let the page fade out before the workspace mounts.
    setLeaving(true);
    window.setTimeout(() => onAuthenticated(user), prefersReducedMotion() ? 0 : 380);
  };

  return (
    <div className={`vf-login ${leaving ? "leaving" : ""}`}>
      <section className="vf-story" aria-label="About VeriFi" onMouseMove={spotlight}>
        <div className="vf-spot" aria-hidden="true" />
        <div className="vf-aurora" aria-hidden="true" />
        <div className="vf-grid" aria-hidden="true" />

        <header className="vf-top reveal" style={{ ["--d" as string]: "0ms" }}>
          <div className="vf-brand">
            <BrandMark size={34} />
            <div><strong>Veri<span>Fi</span></strong><small>Verified financial reports</small></div>
          </div>
          <span className="vf-live"><ShieldCheck size={13} />Every figure checked against its source</span>
        </header>

        <div className="vf-hero">
          <h1 aria-label="Every Number Has a Story.">
            <span className="vf-line"><span style={{ ["--d" as string]: "80ms" }}>Every Number</span></span>
            <span className="vf-line"><em style={{ ["--d" as string]: "200ms" }}>Has a Story.</em></span>
          </h1>
          <p className="vf-lede reveal" style={{ ["--d" as string]: "160ms" }}>
            VeriFi builds financial reports where no figure is taken on trust. Every number traces back to the
            document it came from, is cross-checked against the company's other reported figures, and is never invented.
          </p>
          <Stats overview={overview} />
        </div>

        <div className="vf-story-card-wrap reveal" style={{ ["--d" as string]: "260ms" }}>
          <NumberStory overview={overview} />
        </div>

        <ul className="vf-features">
          {FEATURES.map(({ icon: Icon, title, body }, i) => (
            <li key={title} className="reveal" style={{ ["--d" as string]: `${360 + i * 90}ms` }}>
              <span className="vf-feature-icon"><Icon size={17} /></span>
              <div><strong>{title}</strong><p>{body}</p></div>
            </li>
          ))}
        </ul>

      </section>

      <section className="vf-auth" aria-label="Sign in">
        <div className="vf-orbs" aria-hidden="true"><i /><i /><i /></div>
        <div className="vf-mobile-hero reveal" style={{ ["--d" as string]: "0ms" }}>
          <BrandMark size={30} />
          <div><strong>Veri<span>Fi</span></strong><small>Every Number Has a Story.</small></div>
        </div>
        <AuthCard initialMode={initialMode} onDone={finish} overview={overview} />
      </section>
    </div>
  );
}

// ---- Stats (real counts from the public overview) ---------------------------------

function Stat({ value, label, delay }: { value: number; label: string; delay: number }) {
  const shown = useCountUp(value, 1400);
  return (
    <div className="vf-stat reveal" style={{ ["--d" as string]: `${delay}ms` }}>
      <strong>{shown == null ? "—" : Math.round(shown).toLocaleString("en-IN")}</strong>
      <span>{label}</span>
    </div>
  );
}

function Stats({ overview }: { overview: PublicOverview | null }) {
  const companies = overview?.companies ?? [];
  if (!companies.length) return null;
  const checks = companies.reduce((n, c) => n + c.checks.filter((k) => k.status === "verified").length, 0);
  const quarters = companies.reduce((n, c) => n + c.quarters_filed, 0);
  return (
    <div className="vf-stats">
      <Stat value={companies.length} label="companies covered" delay={300} />
      <Stat value={quarters} label="quarterly reports read" delay={380} />
      <Stat value={checks} label="report checks passed" delay={460} />
      <Stat value={0} label="figures invented" delay={540} />
    </div>
  );
}

// ---- The traced number ---------------------------------------------------------------

function NumberStory({ overview }: { overview: PublicOverview | null }) {
  const companies = useMemo(
    () => (overview?.companies ?? []).filter((c) => c.revenue_ttm && c.checks.length),
    [overview],
  );
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (companies.length < 2 || paused || prefersReducedMotion()) return;
    const id = window.setInterval(() => setIndex((i) => (i + 1) % companies.length), STORY_MS);
    return () => window.clearInterval(id);
  }, [companies.length, paused]);

  if (overview === null) return <div className="vf-story-card skeleton" aria-busy="true" />;

  if (!companies.length) {
    // No live data reachable: explain the idea without inventing a figure.
    return (
      <div className="vf-story-card">
        <span className="vf-eyebrow">How a number earns its place</span>
        <ol className="vf-steps static">
          <li className="done"><FileText size={15} /><span>Taken from the company's own filing with the exchange</span></li>
          <li className="done"><ShieldCheck size={15} /><span>Reconciled with its other reported figures</span></li>
          <li className="done"><BadgeCheck size={15} /><span>Shown with its source - or not shown at all</span></li>
        </ol>
      </div>
    );
  }

  const company = companies[index % companies.length];
  return (
    <div className="vf-story-card" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}>
      <div className="vf-story-head">
        <span className="vf-eyebrow">Trace a real number</span>
        <div className="vf-dots" role="tablist" aria-label="Choose a company">
          {companies.map((c, i) => (
            <button key={c.nse} type="button" role="tab" aria-selected={i === index % companies.length}
              aria-label={c.name} className={i === index % companies.length ? "on" : ""} onClick={() => setIndex(i)} />
          ))}
        </div>
      </div>
      {companies.length > 1 && (
        <div className={`vf-autoplay ${paused ? "paused" : ""}`} aria-hidden="true">
          <span key={company.nse} style={{ animationDuration: `${STORY_MS}ms` }} />
        </div>
      )}
      <StoryBody key={company.nse} company={company} />
    </div>
  );
}

function StoryBody({ company }: { company: OverviewCompany }) {
  const figure = useCountUp(company.revenue_ttm ?? null, 1100);
  const steps = [
    { icon: FileText, text: `${company.quarters_filed} quarterly results, straight from the company's filings`, detail: company.latest_quarter ? `latest: quarter ended ${fmtDate(company.latest_quarter)}` : "" },
    ...company.checks.slice(0, 3).map((k) => ({
      icon: k.status === "verified" ? ShieldCheck : AlertTriangle,
      text: k.label,
      detail: k.status === "verified" ? (k.difference_pct != null ? `agrees within ${k.difference_pct.toFixed(2)}%` : "agrees") : k.status === "mismatch" ? "disagrees - flagged for review" : "not enough data to check",
      status: k.status,
    })),
  ];
  const verified = company.verification_status === "verified";
  return (
    <div className="vf-story-body">
      <div className="vf-figure">
        <span className="vf-figure-label">{company.name} · revenue, last 12 months</span>
        <strong aria-label={inr(company.revenue_ttm)}>{figure == null ? "—" : inr(figure)}</strong>
      </div>
      <ol className="vf-steps">
        {steps.map((s, i) => {
          const Icon = s.icon;
          return (
            <li key={s.text} className={`step ${"status" in s && s.status !== "verified" ? "warn" : ""}`} style={{ ["--i" as string]: i }}>
              <span className="step-icon"><Icon size={14} /></span>
              <div><span>{s.text}</span>{s.detail && <small>{s.detail}</small>}</div>
            </li>
          );
        })}
      </ol>
      <div className={`vf-stamp ${verified ? "" : "warn"}`} style={{ ["--i" as string]: steps.length }}>
        {verified ? <BadgeCheck size={16} /> : <AlertTriangle size={16} />}
        {verified ? "Verified against its filings" : "Shown with a flag - a check disagrees"}
      </div>
    </div>
  );
}

// ---- Auth card -----------------------------------------------------------------------------

/** Lucide has no brand logos (by design); Google's own 4-colour "G" mark,
 * reproduced at the size Google's branding guidelines call for next to
 * "Continue with Google" text. */
function GoogleMark({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 18 18" aria-hidden="true">
      <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.9c1.7-1.57 2.7-3.87 2.7-6.62Z" />
      <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.9-2.26c-.8.54-1.84.86-3.06.86-2.35 0-4.34-1.59-5.05-3.72H.95v2.33A9 9 0 0 0 9 18Z" />
      <path fill="#FBBC05" d="M3.95 10.7a5.4 5.4 0 0 1 0-3.4V4.97H.95a9 9 0 0 0 0 8.06l3-2.33Z" />
      <path fill="#EA4335" d="M9 3.58c1.32 0 2.51.46 3.44 1.35l2.58-2.58A9 9 0 0 0 .95 4.97l3 2.33C4.66 5.17 6.65 3.58 9 3.58Z" />
    </svg>
  );
}

function AuthCard({ initialMode, onDone, overview }: { initialMode: Mode; onDone: (u: SessionUser) => void; overview: PublicOverview | null }) {
  const [mode, setMode] = useState<Mode>(initialMode);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  const [busy, setBusy] = useState<"form" | "demo" | null>(null);
  const [error, setError] = useState("");
  const [linkMode, setLinkMode] = useState(false);
  const [linkBusy, setLinkBusy] = useState(false);
  const [linkSent, setLinkSent] = useState(false);
  const [linkError, setLinkError] = useState("");
  const firstField = useRef<HTMLInputElement>(null);

  const switched = useRef(false);
  useEffect(() => {
    setError("");
    // Focus the first field when the user switches tabs, and on first load
    // only with a mouse/trackpad - on phones it would pop the keyboard open.
    if (switched.current || window.matchMedia("(pointer: fine)").matches) firstField.current?.focus({ preventScroll: true });
    switched.current = true;
  }, [mode]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setBusy("form"); setError("");
    try {
      onDone(mode === "signin" ? await authApi.login(email, password) : await authApi.signup(name, email, password));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
      setBusy(null);
    }
  };

  const demo = async () => {
    if (busy) return;
    setBusy("demo"); setError("");
    try { onDone(await authApi.demo()); } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
      setBusy(null);
    }
  };

  const sendLink = async (event: FormEvent) => {
    event.preventDefault();
    if (linkBusy || !email.trim()) return;
    setLinkBusy(true); setLinkError("");
    try {
      await authApi.sendMagicLink(email.trim());
      setLinkSent(true);
    } catch (cause) {
      setLinkError(cause instanceof Error ? cause.message : String(cause));
    } finally { setLinkBusy(false); }
  };

  const strength = password.length === 0 ? 0 : password.length < 8 ? 1 : /[^A-Za-z0-9]/.test(password) && password.length >= 12 ? 3 : 2;
  const showGoogle = overview?.google_signin_available ?? false;
  const showEmailLink = overview?.email_signin_available ?? false;

  if (linkMode) {
    return (
      <div className="vf-card reveal" style={{ ["--d" as string]: "120ms" }}>
        <h2>Email me a sign-in link</h2>
        <p className="vf-card-sub">No password needed - we'll email you a one-time link.</p>
        {linkSent ? (
          <div className="vf-link-sent">
            <CheckCircle2 size={30} />
            <strong>Check your inbox</strong>
            <p>We sent a sign-in link to <b>{email}</b>. It expires in 15 minutes and works once.</p>
            <button type="button" className="vf-text-btn" onClick={() => { setLinkMode(false); setLinkSent(false); setLinkError(""); }}>
              <ArrowLeft size={14} /> Back to sign in
            </button>
          </div>
        ) : (
          <form onSubmit={sendLink}>
            <label className="vf-field">
              <span>Email</span>
              <div className="vf-input"><Mail size={16} /><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required placeholder="you@example.com" autoFocus /></div>
            </label>
            <div className="vf-error" role="alert" aria-live="assertive">
              {linkError && <><AlertTriangle size={15} /><span>{linkError}</span></>}
            </div>
            <button type="submit" className="vf-primary" disabled={linkBusy || !email.trim()}>
              {linkBusy ? <LoaderCircle size={17} className="spin" /> : <Send size={16} />} Send sign-in link
            </button>
            <button type="button" className="vf-text-btn vf-link-back" onClick={() => { setLinkMode(false); setLinkError(""); }}>
              <ArrowLeft size={14} /> Back to password sign-in
            </button>
          </form>
        )}
      </div>
    );
  }

  return (
    <div className="vf-card reveal" style={{ ["--d" as string]: "120ms" }}>
      <h2>{mode === "signin" ? "Welcome back" : "Create your account"}</h2>
      <p className="vf-card-sub">{mode === "signin" ? "Sign in to your research workspace." : "Free, and takes ten seconds."}</p>

      {showGoogle && (
        <>
          <a className="vf-google" href="/api/auth/google/login">
            <GoogleMark /> Continue with Google
          </a>
          <div className="vf-or"><span>or</span></div>
        </>
      )}

      <div className="vf-seg" role="tablist" aria-label="Sign in or create account">
        <span className="vf-seg-pill" style={{ transform: `translateX(${mode === "signin" ? 0 : 100}%)` }} aria-hidden="true" />
        <button type="button" role="tab" aria-selected={mode === "signin"} onClick={() => setMode("signin")}>Sign in</button>
        <button type="button" role="tab" aria-selected={mode === "signup"} onClick={() => setMode("signup")}>Create account</button>
      </div>

      <form onSubmit={submit} noValidate={false}>
        {mode === "signup" && (
          <label className="vf-field">
            <span>Name</span>
            <div className="vf-input"><User size={16} /><input ref={firstField} value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" required maxLength={80} placeholder="Your name" /></div>
          </label>
        )}
        <label className="vf-field">
          <span>Email</span>
          <div className="vf-input"><Mail size={16} /><input ref={mode === "signin" ? firstField : undefined} type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required placeholder="you@example.com" /></div>
        </label>
        <label className="vf-field">
          <span>Password</span>
          <div className="vf-input">
            <Lock size={16} />
            <input type={showPassword ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === "signin" ? "current-password" : "new-password"} required minLength={mode === "signup" ? 8 : undefined}
              onKeyUp={(e) => setCapsLock(e.getModifierState("CapsLock"))} onBlur={() => setCapsLock(false)}
              placeholder={mode === "signup" ? "At least 8 characters" : "Your password"} />
            <button type="button" className="vf-eye" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? "Hide password" : "Show password"}>
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          {capsLock && <div className="vf-caps"><AlertTriangle size={12} /> Caps Lock is on</div>}
          {mode === "signup" && (
            <div className={`vf-strength s${strength}`} aria-live="polite">
              <i /><i /><i />
              <small>{["", "Too short", "Good", "Strong"][strength]}</small>
            </div>
          )}
        </label>

        <div className="vf-error" role="alert" aria-live="assertive">
          {error && <><AlertTriangle size={15} /><span>{error}</span></>}
        </div>

        <button type="submit" className="vf-primary" disabled={!!busy}>
          {busy === "form" ? <LoaderCircle size={17} className="spin" /> : null}
          {mode === "signin" ? "Sign in" : "Create account"}
          {busy !== "form" && <ArrowRight size={16} className="vf-arrow" />}
        </button>

        {showEmailLink && mode === "signin" && (
          <button type="button" className="vf-text-btn vf-link-toggle" onClick={() => { setLinkMode(true); setError(""); }}>
            <Mail size={13} /> Email me a sign-in link instead
          </button>
        )}
      </form>

      <div className="vf-or"><span>or</span></div>

      <button type="button" className="vf-demo" onClick={demo} disabled={!!busy}>
        <span className="vf-demo-icon">{busy === "demo" ? <LoaderCircle size={18} className="spin" /> : <Sparkles size={18} />}</span>
        <span className="vf-demo-copy">
          <strong>Explore in demo mode</strong>
          <small>No account needed · the full workspace · 2‑hour session</small>
        </span>
        <ArrowRight size={16} className="vf-arrow" />
      </button>

      <p className="vf-fine">
        <Building2 size={12} /> Figures from companies' published financial results. Research, not investment advice.
      </p>
    </div>
  );
}
