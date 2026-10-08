import { useId } from "react";

/** VeriFi mark: a ledger of rising bars closed by a check - "the numbers,
 * verified". Drawn inline so it inherits no external asset. Each instance
 * gets its own gradient id: a shared id breaks every copy whenever the
 * first one on the page is hidden (display:none). */
export function BrandMark({ size = 28 }: { size?: number }) {
  const gid = `vf-g-${useId().replace(/:/g, "")}`;
  return (
    <svg className="brand-mark" width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#5fe0d0" />
          <stop offset="1" stopColor="#119486" />
        </linearGradient>
      </defs>
      <rect x="1" y="1" width="30" height="30" rx="9" fill={`url(#${gid})`} />
      <rect x="7.5" y="17" width="3.2" height="7.5" rx="1.6" fill="#0b2a2e" opacity=".55" />
      <rect x="12.6" y="13" width="3.2" height="11.5" rx="1.6" fill="#0b2a2e" opacity=".7" />
      <path d="M17.5 17.5l3 3.2 5.8-8.4" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Brand({ tagline = true, size = 28 }: { tagline?: boolean; size?: number }) {
  return (
    <div className="brand">
      <BrandMark size={size} />
      <div className="brand-copy">
        <strong>Veri<span>Fi</span></strong>
        {tagline && <small>Financial research</small>}
      </div>
    </div>
  );
}
