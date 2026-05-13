const footerLinks = ["Product", "Docs", "API", "Security", "Privacy", "Contact"];

export default function Footer() {
  return (
    <footer className="bg-graphite text-white">
      <div className="max-w-6xl mx-auto px-4 py-10">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2">
            <img
              src="/assets/alexandria/svg/alexandria-wordmark-monochrome.svg"
              onError={(e) => {
                const img = e.currentTarget;
                img.src = "/assets/alexandria/png/alexandria-wordmark-monochrome.png";
                img.onerror = null;
              }}
              alt="Alexandria"
              className="block h-7 w-auto object-contain invert brightness-200"
            />
            <p className="text-xs text-white/60 max-w-sm leading-relaxed">
              AI memory and context engine with admission control and verifiable proof.
            </p>
          </div>

          <nav className="flex flex-wrap gap-x-5 gap-y-2">
            {footerLinks.map((link) => (
              <a
                key={link}
                href={`#${link.toLowerCase()}`}
                className="text-xs text-white/70 hover:text-white transition-colors"
              >
                {link}
              </a>
            ))}
          </nav>
        </div>

        <div className="mt-8 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-white/10 pt-6">
          <p className="text-xs text-white/50">© 2024 Alexandria, Inc.</p>
          <div className="h-7 w-7 rounded-full border border-white/30 flex items-center justify-center text-xs font-semibold">
            A
          </div>
        </div>
      </div>
    </footer>
  );
}
