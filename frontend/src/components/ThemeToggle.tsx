import { useEffect, useState } from "react";

function getInitialDark(): boolean {
  const stored = localStorage.getItem("sungraphs-dark");
  if (stored !== null) return stored === "true";
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function applyDark(dark: boolean) {
  document.documentElement.classList.toggle("dark", dark);
}

export default function ThemeToggle() {
  const [dark, setDark] = useState(() => {
    const initial = getInitialDark();
    applyDark(initial);
    return initial;
  });

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e: MediaQueryListEvent) => {
      if (localStorage.getItem("sungraphs-dark") === null) {
        setDark(e.matches);
      }
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const toggle = () => {
    const next = !dark;
    setDark(next);
    localStorage.setItem("sungraphs-dark", String(next));
    applyDark(next);
  };

  return (
    <button
      type="button"
      onClick={toggle}
      className="flex size-9 items-center justify-center cursor-pointer text-[color:var(--text-h)] hover:text-amber-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--text-soft)]"
      aria-label={dark ? "Activar modo claro" : "Activar modo oscuro"}
    >
      {dark ? (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="5" />
          <line x1="12" y1="1" x2="12" y2="3" />
          <line x1="12" y1="21" x2="12" y2="23" />
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
          <line x1="1" y1="12" x2="3" y2="12" />
          <line x1="21" y1="12" x2="23" y2="12" />
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>
      ) : (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      )}
    </button>
  );
}
