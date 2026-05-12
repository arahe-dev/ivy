import { Search } from "lucide-react";

const navItems = ["Memory", "Context", "Sources", "Recall"];

interface HeaderProps {
  activeNav: string;
  setActiveNav: (nav: string) => void;
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  onSearchSubmit: (query?: string) => void;
  serviceLabel: string;
}

export default function Header({
  activeNav,
  setActiveNav,
  searchQuery,
  setSearchQuery,
  onSearchSubmit,
  serviceLabel,
}: HeaderProps) {
  return (
    <header className="sticky top-4 z-50 mx-4 lg:mx-auto max-w-6xl">
      <div className="flex items-center rounded-xl border border-mist bg-white px-4 py-2.5 shadow-sm">
        {/* Logo */}
        <div className="flex items-center shrink-0">
          <img
            src="/assets/alexandria/svg/alexandria-wordmark-primary.svg"
            onError={(e) => {
              const img = e.currentTarget;
              img.src = "/assets/alexandria/png/alexandria-wordmark-primary.png";
              img.onerror = null;
            }}
            alt="Alexandria"
            className="block h-[42px] w-auto object-contain"
          />
        </div>

        {/* Divider */}
        <div className="hidden sm:block h-[38px] w-px bg-mist ml-6 mr-6" />

        {/* Search */}
        <div className="hidden md:flex flex-1 items-center gap-2 rounded-lg border border-mist bg-ivory px-3 py-1.5 max-w-md">
          <Search className="h-4 w-4 text-ink-secondary" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                onSearchSubmit(searchQuery);
              }
            }}
            placeholder="Ask anything or search your memory…"
            className="flex-1 bg-transparent text-sm text-ink placeholder:text-ink-secondary/60 outline-none"
          />
          <span className="hidden lg:inline-flex items-center rounded-md border border-mist bg-white px-1.5 py-0.5 text-[11px] font-medium text-ink-secondary">
            ⌘ K
          </span>
        </div>

        {/* Nav */}
        <nav className="hidden sm:flex items-center gap-1 ml-auto">
          {navItems.map((item) => (
            <button
              key={item}
              onClick={() => setActiveNav(item)}
              className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
                activeNav === item
                  ? "bg-ink text-white"
                  : "text-ink-secondary hover:bg-ivory"
              }`}
            >
              {item}
            </button>
          ))}
        </nav>

        {/* Avatar */}
        <div className="hidden sm:flex h-8 w-8 items-center justify-center rounded-full bg-ink text-white text-sm font-semibold ml-3">
          A
        </div>
      </div>
      <div className="mt-2 flex justify-end">
        <span className="rounded-full border border-mist bg-white/80 px-2.5 py-1 text-[11px] font-medium text-ink-secondary shadow-sm">
          {serviceLabel}
        </span>
      </div>
    </header>
  );
}
