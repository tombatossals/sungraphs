import ThemeToggle from "./ThemeToggle";

export default function Header() {
  return (
    <header className="flex items-center justify-between px-4 md:px-6 h-[10vh] min-h-[60px]">
      <div className="flex items-center gap-3">
        <img src="/sun.png" alt="Sol" className="size-18 md:size-24" />
        <h1
          className="text-4xl md:text-5xl tracking-[-0.03em] text-[color:var(--text-h)]"
          style={{ fontFamily: "'Bebas Neue', sans-serif" }}
        >
          Solar
        </h1>
      </div>
      <ThemeToggle />
    </header>
  );
}
