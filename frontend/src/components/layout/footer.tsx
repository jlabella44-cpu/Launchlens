import Link from "next/link";

const CURRENT_YEAR = new Date().getFullYear();

const PRODUCT_LINKS = [
  { href: "/pricing", label: "Pricing" },
  { href: "/demo", label: "Demo" },
  { href: "/register", label: "Get Started" },
];

const LEGAL_LINKS = [
  { href: "/privacy", label: "Privacy Policy" },
  { href: "mailto:support@listingjet.ai", label: "Contact Support" },
];

export function Footer() {
  return (
    <footer className="border-t border-slate-200/60 bg-[var(--color-surface)] mt-auto">
      <div className="max-w-6xl mx-auto px-6 py-10">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Brand */}
          <div>
            <Link
              href="/"
              className="text-lg font-bold text-[var(--color-primary)] tracking-wide"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              ListingJet
            </Link>
            <p className="mt-2 text-sm text-[var(--color-text-secondary)] max-w-xs">
              AI-powered listing media automation. From raw photos to marketing-ready assets in minutes.
            </p>
          </div>

          {/* Product */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
              Product
            </h3>
            <ul className="space-y-2">
              {PRODUCT_LINKS.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
              Legal
            </h3>
            <ul className="space-y-2">
              {LEGAL_LINKS.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-primary)] transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-8 pt-6 border-t border-slate-200/60 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-xs text-slate-400">
            &copy; {CURRENT_YEAR} ListingJet. All rights reserved.
          </p>
          <p className="text-xs text-slate-400">
            Powered by AI &mdash; Google Vision, OpenAI, Anthropic, Kling, ElevenLabs
          </p>
        </div>
      </div>
    </footer>
  );
}
