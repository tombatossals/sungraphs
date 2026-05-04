import ThemeToggle from "./ThemeToggle";

export default function Header() {
  return (
    <header className="flex items-center justify-between px-4 py-3 md:px-6 md:py-4">
      <div className="flex items-center gap-3">
        <img src="/sun.png" alt="Sol" className="size-8 md:size-9" />
        <h1
          className="text-2xl tracking-widest text-[color:var(--text-h)] md:text-3xl"
          style={{ fontFamily: "'VT323', monospace" }}
        >
          Solar
        </h1>
      </div>
      <ThemeToggle />
    </header>
  );
}
