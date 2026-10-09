import { useEffect, useRef, useState } from "react";
import { ChevronDown, LogOut, Sparkles, UserPlus } from "lucide-react";
import type { SessionUser } from "../services/api";

export const initials = (name: string) =>
  name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]!.toUpperCase()).join("") || "?";

export function sessionEnds(user: SessionUser): string {
  return new Date(user.expires_at + (user.expires_at.endsWith("Z") ? "" : "Z"))
    .toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

export function UserMenu({ user, onSignOut }: { user: SessionUser; onSignOut: (next?: "signin" | "signup") => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const demo = user.kind === "demo";

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", close); };
  }, [open]);

  return (
    <div className="user-menu" ref={ref}>
      {demo && <span className="demo-pill">Guest session</span>}
      <button type="button" className="user-trigger" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span className={`top-avatar ${demo ? "demo" : ""}`}>{demo ? <Sparkles size={14} /> : initials(user.name)}</span>
        <ChevronDown size={14} className={open ? "flip" : ""} />
      </button>
      {open && (
        <div className="user-pop" role="menu">
          <div className="user-pop-head">
            <strong>{demo ? "Guest" : user.name}</strong>
            <small>{demo ? `Demo session · ends ${sessionEnds(user)}` : user.email}</small>
          </div>
          {demo && (
            <button type="button" role="menuitem" className="user-pop-item accent" onClick={() => onSignOut("signup")}>
              <UserPlus size={15} /> Create an account
            </button>
          )}
          <button type="button" role="menuitem" className="user-pop-item" onClick={() => onSignOut("signin")}>
            <LogOut size={15} /> {demo ? "End guest session" : "Sign out"}
          </button>
        </div>
      )}
    </div>
  );
}
