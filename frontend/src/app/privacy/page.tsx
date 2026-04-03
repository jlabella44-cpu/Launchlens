export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-[#F5F7FA] py-16 px-4">
      <div className="max-w-3xl mx-auto bg-white rounded-xl shadow-sm p-8 md:p-12">
        <h1
          className="text-3xl font-bold text-[var(--color-text)] mb-2"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Privacy Policy
        </h1>
        <p className="text-sm text-slate-400 mb-8">Last updated: April 3, 2026</p>

        <div className="prose prose-slate prose-sm max-w-none space-y-6 text-[var(--color-text-secondary)]">
          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">1. Information We Collect</h2>
            <p>
              When you create an account, we collect your name, email address, company name,
              and billing information. When you use our services, we collect property listing
              data (addresses, photos, metadata) that you upload.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">2. How We Use Your Information</h2>
            <p>We use your information to:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>Provide, maintain, and improve our listing automation services</li>
              <li>Process payments and manage your subscription</li>
              <li>Send transactional emails (welcome, pipeline status, billing)</li>
              <li>Generate AI-powered listing content, photo analysis, and video tours</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">3. Third-Party AI Services</h2>
            <p>
              To deliver our AI-powered features, your listing data (photos, property details)
              is processed by the following third-party providers:
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <strong>Google Cloud Vision API</strong> &mdash; Photo analysis, room detection,
                and quality scoring
              </li>
              <li>
                <strong>OpenAI (GPT-4V)</strong> &mdash; Photo analysis and listing content generation
              </li>
              <li>
                <strong>Anthropic (Claude)</strong> &mdash; Listing descriptions, marketing copy,
                and social media content
              </li>
              <li>
                <strong>Kling AI</strong> &mdash; AI-generated video tours from listing photos
              </li>
              <li>
                <strong>ElevenLabs</strong> &mdash; Voiceover narration for video tours (when enabled)
              </li>
            </ul>
            <p>
              We apply a PII filter before sending data to these providers. Personal information
              such as agent names, emails, phone numbers, and seller details is stripped from
              all AI requests. These providers process data under their respective privacy
              policies and data processing agreements.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">4. Data Storage and Security</h2>
            <p>
              Your data is stored on encrypted AWS infrastructure (RDS with AES-256 encryption
              at rest, S3 with server-side encryption). All data is transmitted over TLS 1.2+.
              We use bcrypt for password hashing and httpOnly cookies for session management.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">5. Data Retention</h2>
            <ul className="list-disc pl-5 space-y-1">
              <li>Account data: retained while your account is active</li>
              <li>Listing assets (photos, videos): retained while the listing exists</li>
              <li>Export bundles: automatically deleted after 90 days</li>
              <li>Webhook delivery logs: automatically deleted after 30 days</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">6. Your Rights (GDPR / CCPA)</h2>
            <p>You have the right to:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <strong>Access</strong> your personal data &mdash; available via your account
                settings and the API
              </li>
              <li>
                <strong>Delete</strong> your account and all associated data &mdash; use the
                &ldquo;Delete Account&rdquo; option in settings, or contact support
              </li>
              <li>
                <strong>Export</strong> your data in a machine-readable format &mdash; contact
                support@listingjet.ai
              </li>
              <li>
                <strong>Withdraw consent</strong> for data processing at any time by deleting
                your account
              </li>
            </ul>
            <p>
              Deletion requests are processed within 30 days. We will purge all personal data,
              listing assets, and associated records from our systems and third-party providers.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">7. Cookies</h2>
            <p>
              We use httpOnly session cookies for authentication. We do not use third-party
              tracking cookies or advertising pixels. A localStorage flag is used for theme
              preference only.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">8. Contact</h2>
            <p>
              For privacy inquiries, data access requests, or deletion requests, contact us at{" "}
              <a href="mailto:support@listingjet.ai" className="text-[#F97316] hover:underline">
                support@listingjet.ai
              </a>.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
