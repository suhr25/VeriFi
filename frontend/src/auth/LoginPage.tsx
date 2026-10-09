import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import {
  AlertTriangle, ArrowLeft, ArrowRight, Check, CheckCircle2, Eye, EyeOff, LoaderCircle, Lock, Mail, Send, User,
} from "lucide-react";
import { apiUrl, authApi, publicApi, type OverviewCompany, type PublicOverview, type SessionUser } from "../services/api";
import { BrandMark } from "../components/Brand";
import { inr } from "../lib/format";
import { prefersReducedMotion } from "../lib/motion";
import "./login.css";

type Mode = "signin" | "signup";

const TRAIL_MS = 7000;

export function LoginPage({ onAuthenticated, initialMode = "signin" }: { onAuthenticated: (user: SessionUser) => void; initialMode?: Mode }) {
  const [overview, setOverview] = useState<PublicOverview | null>(null);
  const [leaving, setLeaving] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    publicApi.overview().then(setOverview)
      .catch(() => setOverview({ companies: [], google_signin_available: false, email_signin_available: false }));
  }, []);

  // The background follows the pointer by a few pixels - depth without
  // moving anything the user is reading or clicking.
  useEffect(() => {
    if (prefersReducedMotion() || !window.matchMedia("(pointer: fine)").matches) return;
    let frame = 0;
    const onMove = (e: PointerEvent) => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const el = root.current;
        if (!el) return;
        el.style.setProperty("--px", ((e.clientX / window.innerWidth) - .5).toFixed(3));
        el.style.setProperty("--py", ((e.clientY / window.innerHeight) - .5).toFixed(3));
      });
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => { window.removeEventListener("pointermove", onMove); cancelAnimationFrame(frame); };
  }, []);

  const finish = (user: SessionUser) => {
    // Hold the success state briefly, then fade the page before the workspace mounts.
    window.setTimeout(() => setLeaving(true), prefersReducedMotion() ? 0 : 260);
    window.setTimeout(() => onAuthenticated(user), prefersReducedMotion() ? 0 : 620);
  };

  const companies = overview?.companies ?? [];
  const quarters = companies.reduce((n, c) => n + c.quarters_filed, 0);

  return (
    <div className={`vf-login ${leaving ? "leaving" : ""}`} ref={root}>
      <div className="vf-bg" aria-hidden="true"><div className="vf-glow" /><div className="vf-grid" /></div>

      <header className="vf-top vf-in" style={{ ["--d" as string]: "60ms" }}>
        <div className="vf-brand">
          <BrandMark size={30} />
          <div><strong>Veri<span>Fi</span></strong><small>Financial research</small></div>
        </div>
        {companies.length > 0 && (
          <span className="vf-status"><i />NSE filings · {companies.length} companies · {quarters} quarterly results</span>
        )}
      </header>

      <main className="vf-stage">
        <section className="vf-scene" aria-label="About VeriFi">
          <h1>
            <span className="vf-in" style={{ ["--d" as string]: "200ms" }}>Company financials,</span>
            <span className="vf-in vf-accent" style={{ ["--d" as string]: "280ms" }}>checked against the filings.</span>
          </h1>
          <div className="vf-trail-wrap vf-in vf-blur" style={{ ["--d" as string]: "380ms" }}>
            <EvidenceTrail overview={overview} />
          </div>
        </section>

        <section className="vf-panel-col" aria-label="Sign in">
          <div className="vf-panel vf-in vf-rise" style={{ ["--d" as string]: "320ms" }}>
            <AuthForm initialMode={initialMode} onDone={finish} overview={overview} />
          </div>
          <p className="vf-legal vf-in" style={{ ["--d" as string]: "800ms" }}>
            Figures are taken from companies' published results. Research, not investment advice.
          </p>
        </section>
      </main>

      <Tape companies={companies} />
    </div>
  );
}

// ---- Ticker tape: every company's real figure and check result -----------------------

function Tape({ companies }: { companies: OverviewCompany[] }) {
  const items = companies.filter((c) => c.revenue_ttm);
  if (!items.length) return <div className="vf-tape empty" aria-hidden="true" />;
  const row = items.map((c) => {
    const passed = c.checks.filter((k) => k.status === "verified").length;
    return (
      <span className="vf-tick" key={c.nse}>
        <b>{c.nse}</b>
        <span>{inr(c.revenue_ttm)}</span>
        <em className={c.verification_status === "verified" ? "ok" : "warn"}>
          {c.verification_status === "verified" ? "✓" : "!"} {passed}/{c.checks.length} checks
        </em>
      </span>
    );
  });
  return (
    <footer className="vf-tape vf-in" style={{ ["--d" as string]: "700ms" }} aria-label="Revenue over the last 12 months and consistency checks, by company">
      <div className="vf-tape-label">REV · TTM</div>
      <div className="vf-tape-track">
        <div className="vf-tape-run">{row}</div>
        <div className="vf-tape-run" aria-hidden="true">{row}</div>
      </div>
    </footer>
  );
}

// ---- Evidence trail: filings -> reported figure -> checks ------------------------------

/** Quarter-end labels counted back from the latest filed quarter. */
function quarterLabels(latestIso: string | null | undefined, count: number): string[] {
  if (!latestIso) return Array.from({ length: count }, () => "Quarterly results");
  const latest = new Date(latestIso);
  return Array.from({ length: count }, (_, i) => {
    const end = new Date(Date.UTC(latest.getUTCFullYear(), latest.getUTCMonth() - 3 * i + 1, 0));
    return `${end.toLocaleDateString("en-IN", { month: "short", year: "numeric", timeZone: "UTC" })} results`;
  });
}

/** The overview's check labels are full sentences; the diagram needs short ones. */
function shortCheck(label: string): string {
  const l = label.toLowerCase();
  if (l.includes("annual") && l.includes("revenue")) return "Quarters add up (revenue)";
  if (l.includes("annual") && (l.includes("profit") || l.includes("income"))) return "Quarters add up (profit)";
  if (l.includes("eps")) return "EPS consistent with profit";
  return label.length > 26 ? `${label.slice(0, 25)}…` : label;
}

const DOC_Y = [52, 112, 172, 232];
const CHECK_Y = [80, 150, 220];

function EvidenceTrail({ overview }: { overview: PublicOverview | null }) {
  const companies = useMemo(() => (overview?.companies ?? []).filter((c) => c.revenue_ttm && c.checks.length), [overview]);
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (companies.length < 2 || paused || prefersReducedMotion()) return;
    const id = window.setInterval(() => setIndex((i) => (i + 1) % companies.length), TRAIL_MS);
    return () => window.clearInterval(id);
  }, [companies.length, paused]);

  if (overview === null) return <div className="vf-trail skeleton" aria-busy="true" aria-label="Loading" />;

  const company = companies.length ? companies[index % companies.length] : null;
  return (
    <figure className={`vf-trail ${index > 0 ? "rotated" : ""}`} onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}>
      <figcaption className="vf-trail-head">
        <span className="vf-eyebrow">Evidence trail</span>
        <span className="vf-trail-co">{company ? company.name : "How a figure is checked"}</span>
        {companies.length > 1 && (
          <div className="vf-dots" role="tablist" aria-label="Choose a company">
            {companies.map((c, i) => (
              <button key={c.nse} type="button" role="tab" aria-selected={i === index % companies.length}
                aria-label={c.name} className={i === index % companies.length ? "on" : ""} onClick={() => setIndex(i)} />
            ))}
          </div>
        )}
      </figcaption>
      {companies.length > 1 && (
        <div className={`vf-autoplay ${paused ? "paused" : ""}`} aria-hidden="true">
          <span key={company?.nse} style={{ animationDuration: `${TRAIL_MS}ms` }} />
        </div>
      )}
      <TrailDiagram key={company?.nse ?? "generic"} company={company} />
    </figure>
  );
}

function TrailDiagram({ company }: { company: OverviewCompany | null }) {
  const motion = !prefersReducedMotion();
  const docCount = company ? Math.min(4, Math.max(1, company.quarters_filed)) : 3;
  const docs = company ? quarterLabels(company.latest_quarter, docCount) : ["Quarterly results", "Annual report", "Exchange filing"];
  const docYs = DOC_Y.slice(0, docCount).map((y) => y + (4 - docCount) * 30);
  const checks = company
    ? company.checks.slice(0, 3).map((k) => ({
      label: shortCheck(k.label),
      ok: k.status === "verified",
      note: k.status === "verified" ? (k.difference_pct != null ? `within ${k.difference_pct.toFixed(2)}%` : "agrees") : k.status === "mismatch" ? "disagrees" : "not enough data",
    }))
    : [{ label: "Quarters add up", ok: true, note: "" }, { label: "EPS consistent", ok: true, note: "" }, { label: "Source linked", ok: true, note: "" }];
  const checkYs = CHECK_Y.slice(0, checks.length);
  const verified = company ? company.verification_status === "verified" : true;
  const extra = company ? company.quarters_filed - docCount : 0;
  const id = company?.nse ?? "generic";

  const docPath = (y: number) => `M160 ${y} C 202 ${y}, 202 150, 244 150`;
  const checkPath = (y: number) => `M396 150 C 424 150, 424 ${y}, 452 ${y}`;

  return (
    <svg className="vf-diagram" viewBox="0 0 640 300" preserveAspectRatio="xMinYMid meet" role="img"
      aria-label={company ? `${company.name}: ${docCount} filings feed reported revenue of ${inr(company.revenue_ttm)}, which passes ${checks.filter((c) => c.ok).length} of ${checks.length} checks.` : "Filings feed a reported figure, which is then checked against the company's other figures."}>
      <defs>
        <radialGradient id={`glow-${id}`} cx="50%" cy="50%" r="50%">
          <stop offset="0" stopColor="#3fd6c4" stopOpacity=".22" />
          <stop offset="1" stopColor="#3fd6c4" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Column captions */}
      <g className="et-caption">
        <text x="0" y="14">FILINGS</text>
        <text x="320" y="14" textAnchor="middle">REPORTED FIGURE</text>
        <text x="452" y="14">CHECKS</text>
      </g>

      {/* Connectors */}
      {docYs.map((y, i) => <path key={`d${i}`} id={`${id}-d${i}`} className="et-line" d={docPath(y)} pathLength={1} style={{ ["--i" as string]: i }} />)}
      {checkYs.map((y, i) => <path key={`c${i}`} id={`${id}-c${i}`} className={`et-line ${checks[i].ok ? "" : "warn"}`} d={checkPath(y)} pathLength={1} style={{ ["--i" as string]: i + 4 }} />)}

      {/* Travelling evidence */}
      {motion && docYs.map((_, i) => (
        <circle key={`dm${i}`} r="2.4" className="et-pulse" opacity="0">
          <animateMotion dur="2.8s" begin={`${1.2 + i * 0.45}s`} repeatCount="indefinite" calcMode="spline" keyTimes="0;1" keySplines=".45 0 .55 1">
            <mpath href={`#${id}-d${i}`} />
          </animateMotion>
          <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.12;.82;1" dur="2.8s" begin={`${1.2 + i * 0.45}s`} repeatCount="indefinite" />
        </circle>
      ))}
      {motion && checkYs.map((_, i) => (
        <circle key={`cm${i}`} r="2.4" className={`et-pulse ${checks[i].ok ? "" : "warn"}`} opacity="0">
          <animateMotion dur="2.8s" begin={`${2.4 + i * 0.45}s`} repeatCount="indefinite" calcMode="spline" keyTimes="0;1" keySplines=".45 0 .55 1">
            <mpath href={`#${id}-c${i}`} />
          </animateMotion>
          <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.12;.82;1" dur="2.8s" begin={`${2.4 + i * 0.45}s`} repeatCount="indefinite" />
        </circle>
      ))}

      {/* Filings */}
      {docYs.map((y, i) => (
        <g key={`doc${i}`} className="et-node" style={{ ["--i" as string]: i }} transform={`translate(0 ${y - 22})`}>
          <rect width="160" height="44" rx="8" className="et-box" />
          <path d="M14 13h8l4 4v14h-12z M22 13v4h4" className="et-doc-icon" />
          <text x="36" y="20" className="et-label">{docs[i]}</text>
          <text x="36" y="34" className="et-sub">NSE · XBRL</text>
        </g>
      ))}
      {extra > 0 && <text x="0" y="292" className="et-sub">+ {extra} earlier filing{extra > 1 ? "s" : ""}</text>}

      {/* Reported figure */}
      <circle cx="320" cy="150" r="96" fill={`url(#glow-${id})`} className="et-glow" />
      <g className="et-node et-figure" style={{ ["--i" as string]: 2 }}>
        <rect x="244" y="104" width="152" height="92" rx="10" className="et-box strong" />
        <text x="320" y="128" textAnchor="middle" className="et-caption-in">{company ? "REVENUE · 12 MONTHS" : "REPORTED FIGURE"}</text>
        <text x="320" y="160" textAnchor="middle" className="et-value">{company ? inr(company.revenue_ttm) : "Revenue"}</text>
        <text x="320" y="180" textAnchor="middle" className="et-sub">{company ? company.short_name : "profit, EPS"}</text>
      </g>

      {/* Checks */}
      {checks.map((c, i) => (
        <g key={`chk${i}`} className="et-node" style={{ ["--i" as string]: i + 5 }} transform={`translate(452 ${checkYs[i] - 20})`}>
          <rect width="188" height="40" rx="8" className={`et-box ${c.ok ? "" : "warn"}`} />
          <circle cx="18" cy="20" r="8" className={`et-check ${c.ok ? "" : "warn"}`} />
          {c.ok
            ? <path d="M14.2 20.2l2.6 2.6 5-5.4" className="et-check-mark" />
            : <path d="M18 15.5v5.2 M18 23.6v.1" className="et-check-mark" />}
          <text x="34" y={c.note ? 18 : 24} className="et-label">{c.label}</text>
          {c.note && <text x="34" y="31" className="et-sub">{c.note}</text>}
        </g>
      ))}

      {/* Verdict */}
      <g className="et-node et-verdict" style={{ ["--i" as string]: 9 }} transform="translate(452 252)">
        <rect width="188" height="30" rx="15" className={`et-pill ${verified ? "" : "warn"}`} />
        <text x="94" y="19.5" textAnchor="middle" className="et-pill-text">{verified ? "All checks pass" : "Shown with a flag"}</text>
      </g>
    </svg>
  );
}

// ---- Auth form ------------------------------------------------------------------------------

/** Lucide has no brand logos (by design); Google's own 4-colour "G" mark. */
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

/** Error area that opens smoothly instead of pushing the form down in one jump. */
function FormError({ message }: { message: string }) {
  return (
    <div className={`vf-error ${message ? "show" : ""}`} role="alert" aria-live="assertive">
      <div>{message && <><AlertTriangle size={15} /><span>{message}</span></>}</div>
    </div>
  );
}

function AuthForm({ initialMode, onDone, overview }: { initialMode: Mode; onDone: (u: SessionUser) => void; overview: PublicOverview | null }) {
  const [mode, setMode] = useState<Mode>(initialMode);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  const [busy, setBusy] = useState<"form" | "demo" | null>(null);
  const [success, setSuccess] = useState(false);
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

  const succeed = (user: SessionUser) => { setSuccess(true); onDone(user); };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (busy || success) return;
    setBusy("form"); setError("");
    try {
      succeed(mode === "signin" ? await authApi.login(email, password) : await authApi.signup(name, email, password));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
      setBusy(null);
    }
  };

  const demo = async () => {
    if (busy || success) return;
    setBusy("demo"); setError("");
    try { succeed(await authApi.demo()); } catch (cause) {
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

  const edit = (setter: (v: string) => void) => (e: React.ChangeEvent<HTMLInputElement>) => { setter(e.target.value); if (error) setError(""); };

  const strength = password.length === 0 ? 0 : password.length < 8 ? 1 : /[^A-Za-z0-9]/.test(password) && password.length >= 12 ? 3 : 2;
  const showGoogle = overview?.google_signin_available ?? false;
  const showEmailLink = overview?.email_signin_available ?? false;
  const invalid = !!error && busy === null;

  if (linkMode) {
    return (
      <div className="vf-form">
        <div className="vf-form-head vf-in" style={{ ["--d" as string]: "0ms" }}>
          <h2>Sign in with an email link</h2>
          <p>We'll send a one-time link to your inbox. No password needed.</p>
        </div>
        {linkSent ? (
          <div className="vf-link-sent vf-in" style={{ ["--d" as string]: "60ms" }}>
            <span className="vf-link-sent-icon"><CheckCircle2 size={22} /></span>
            <strong>Check your inbox</strong>
            <p>We sent a sign-in link to <b>{email}</b>. It works once and expires in 15 minutes.</p>
            <button type="button" className="vf-text-link" onClick={() => { setLinkMode(false); setLinkSent(false); setLinkError(""); }}>
              <ArrowLeft size={14} /> Back to sign in
            </button>
          </div>
        ) : (
          <form onSubmit={sendLink} className="vf-in" style={{ ["--d" as string]: "60ms" }}>
            <label className="vf-field">
              <span>Email</span>
              <div className={`vf-input ${linkError ? "invalid" : ""}`}>
                <Mail size={16} />
                <input type="email" value={email} onChange={(e) => { setEmail(e.target.value); setLinkError(""); }} autoComplete="email" required placeholder="you@example.com" autoFocus aria-invalid={!!linkError} />
              </div>
            </label>
            <FormError message={linkError} />
            <button type="submit" className="vf-primary" disabled={linkBusy || !email.trim()}>
              {linkBusy ? <><LoaderCircle size={16} className="spin" /> Sending…</> : <><Send size={15} /> Send sign-in link</>}
            </button>
            <button type="button" className="vf-text-link vf-back" onClick={() => { setLinkMode(false); setLinkError(""); }}>
              <ArrowLeft size={14} /> Back to password sign-in
            </button>
          </form>
        )}
      </div>
    );
  }

  let i = 0;
  const step = () => ({ ["--d" as string]: `${520 + (i++) * 45}ms` });

  return (
    <div className="vf-form">
      <div className="vf-form-head vf-in" style={step()}>
        <h2>{mode === "signin" ? "Sign in to VeriFi" : "Create your account"}</h2>
        <p>{mode === "signin" ? "Your saved research is available on any device." : "Free. Your research is saved to your account."}</p>
      </div>

      <div className="vf-seg vf-in" role="tablist" aria-label="Sign in or create account" style={step()}>
        <span className="vf-seg-pill" style={{ transform: `translateX(${mode === "signin" ? 0 : 100}%)` }} aria-hidden="true" />
        <button type="button" role="tab" aria-selected={mode === "signin"} onClick={() => setMode("signin")}>Sign in</button>
        <button type="button" role="tab" aria-selected={mode === "signup"} onClick={() => setMode("signup")}>Create account</button>
      </div>

      {showGoogle && (
        <div className="vf-in" style={step()}>
          <a className="vf-google" href={apiUrl("/api/auth/google/login")}>
            <GoogleMark /> {mode === "signin" ? "Continue with Google" : "Sign up with Google"}
          </a>
          <div className="vf-or"><span>or use email</span></div>
        </div>
      )}

      <form onSubmit={submit}>
        {mode === "signup" && (
          <label className="vf-field vf-in" style={step()}>
            <span>Name</span>
            <div className="vf-input"><User size={16} /><input ref={firstField} value={name} onChange={edit(setName)} autoComplete="name" required maxLength={80} placeholder="Your name" /></div>
          </label>
        )}
        <label className="vf-field vf-in" style={step()}>
          <span>Email</span>
          <div className={`vf-input ${invalid ? "invalid" : ""}`}>
            <Mail size={16} />
            <input ref={mode === "signin" ? firstField : undefined} type="email" value={email} onChange={edit(setEmail)} autoComplete="email" required placeholder="you@example.com" aria-invalid={invalid} />
          </div>
        </label>
        <label className="vf-field vf-in" style={step()}>
          <span>Password</span>
          <div className={`vf-input ${invalid ? "invalid" : ""}`}>
            <Lock size={16} />
            <input type={showPassword ? "text" : "password"} value={password} onChange={edit(setPassword)}
              autoComplete={mode === "signin" ? "current-password" : "new-password"} required minLength={mode === "signup" ? 8 : undefined}
              onKeyUp={(e) => setCapsLock(e.getModifierState("CapsLock"))} onBlur={() => setCapsLock(false)}
              placeholder={mode === "signup" ? "At least 8 characters" : "Your password"} aria-invalid={invalid} />
            <button type="button" className={`vf-eye ${showPassword ? "shown" : ""}`} onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? "Hide password" : "Show password"}>
              <Eye size={16} className="vf-eye-on" /><EyeOff size={16} className="vf-eye-off" />
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

        <FormError message={error} />

        <div className="vf-in" style={step()}>
          <button type="submit" className={`vf-primary ${success && busy === "form" ? "success" : ""}`} disabled={!!busy || success}>
            {success && busy === "form"
              ? <><Check size={16} /> Signed in</>
              : busy === "form"
                ? <><LoaderCircle size={16} className="spin" /> {mode === "signin" ? "Signing in…" : "Creating account…"}</>
                : <>{mode === "signin" ? "Sign in" : "Create account"} <ArrowRight size={16} className="vf-arrow" /></>}
          </button>

          {showEmailLink && mode === "signin" && (
            <button type="button" className="vf-text-link vf-link-toggle" onClick={() => { setLinkMode(true); setError(""); }}>
              <Mail size={13} /> Email me a sign-in link instead
            </button>
          )}
        </div>
      </form>

      <div className="vf-guest vf-in" style={step()}>
        <span>No account needed</span>
        <button type="button" className="vf-text-link vf-guest-btn" onClick={demo} disabled={!!busy || success} title="A 2-hour guest session">
          {busy === "demo" ? <LoaderCircle size={14} className="spin" /> : null}
          {success && busy === "demo" ? <><Check size={14} /> Opening workspace</> : <>Continue as guest <ArrowRight size={14} className="vf-arrow" /></>}
        </button>
      </div>
    </div>
  );
}
