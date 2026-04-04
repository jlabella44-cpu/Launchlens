export default function ChangelogPage() {
  return (
    <div className="min-h-screen bg-[#F5F7FA] py-16 px-4">
      <div className="max-w-3xl mx-auto">
        <h1
          className="text-3xl font-bold text-[var(--color-text)] mb-2"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Changelog
        </h1>
        <p className="text-sm text-[var(--color-text-secondary)] mb-10">
          New features, improvements, and fixes for ListingJet.
        </p>

        <div className="space-y-8">
          <article className="bg-white rounded-xl shadow-sm p-6 md:p-8">
            <div className="flex items-center gap-3 mb-3">
              <span className="px-2.5 py-0.5 rounded-full bg-[#F97316]/10 text-[#F97316] text-xs font-semibold">
                New
              </span>
              <time className="text-xs text-slate-400">April 3, 2026</time>
            </div>
            <h2 className="text-lg font-semibold text-[var(--color-text)] mb-2">
              Pre-Launch Security &amp; Compliance Audit
            </h2>
            <ul className="list-disc pl-5 space-y-1 text-sm text-[var(--color-text-secondary)]">
              <li>httpOnly cookie authentication for enhanced session security</li>
              <li>Account lockout after 5 failed login attempts</li>
              <li>Password reset flow via email</li>
              <li>GDPR/CCPA account deletion endpoint</li>
              <li>Privacy Policy and Terms of Service pages</li>
              <li>Consent tracking on registration</li>
              <li>Database performance indexes for faster queries</li>
              <li>Stripe error handling with proper HTTP status codes</li>
              <li>Accessible toast notifications with ARIA roles</li>
              <li>RDS encryption at rest enabled</li>
            </ul>
          </article>

          <article className="bg-white rounded-xl shadow-sm p-6 md:p-8">
            <div className="flex items-center gap-3 mb-3">
              <span className="px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold">
                Improvement
              </span>
              <time className="text-xs text-slate-400">April 2, 2026</time>
            </div>
            <h2 className="text-lg font-semibold text-[var(--color-text)] mb-2">
              Analytics Dashboard &amp; Credit Charts
            </h2>
            <ul className="list-disc pl-5 space-y-1 text-sm text-[var(--color-text-secondary)]">
              <li>Pipeline performance overview with success rates</li>
              <li>Daily listing creation timeline chart</li>
              <li>Credit transaction history with charting</li>
              <li>Monthly usage breakdown on dashboard</li>
            </ul>
          </article>

          <article className="bg-white rounded-xl shadow-sm p-6 md:p-8">
            <div className="flex items-center gap-3 mb-3">
              <span className="px-2.5 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-semibold">
                Launch
              </span>
              <time className="text-xs text-slate-400">March 2026</time>
            </div>
            <h2 className="text-lg font-semibold text-[var(--color-text)] mb-2">
              ListingJet Beta
            </h2>
            <ul className="list-disc pl-5 space-y-1 text-sm text-[var(--color-text-secondary)]">
              <li>AI-powered photo analysis with Google Vision and OpenAI</li>
              <li>Dual-tone property descriptions (MLS + marketing)</li>
              <li>AI video tours powered by Kling</li>
              <li>3D floorplan generation</li>
              <li>Social media content pack</li>
              <li>MLS compliance detection</li>
              <li>Credit-based billing with Stripe</li>
              <li>Team collaboration and listing sharing</li>
              <li>Brand kit customization</li>
            </ul>
          </article>
        </div>
      </div>
    </div>
  );
}
