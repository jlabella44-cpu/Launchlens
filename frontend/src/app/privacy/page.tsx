export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-[#F5F7FA] py-16 px-4">
      <div className="max-w-3xl mx-auto bg-white rounded-xl shadow-sm p-8 md:p-12">
        <h1
          className="text-3xl font-bold text-[var(--color-text)] mb-2"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Privacy Policy for ListingJet
        </h1>
        <p className="text-sm text-slate-400 mb-8">Last updated: April 4, 2026</p>

        <div className="prose prose-slate prose-sm max-w-none space-y-6 text-[var(--color-text-secondary)]">
          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">1. Introduction</h2>
            <p>
              Welcome to ListingJet (&ldquo;ListingJet,&rdquo; &ldquo;we,&rdquo; &ldquo;us,&rdquo; or &ldquo;our&rdquo;).
              ListingJet is an automated real estate marketing platform that utilizes advanced artificial intelligence to
              generate property descriptions, edit visual assets, and create marketing collateral. This Privacy Policy
              explains how we collect, use, disclose, and safeguard your information when you visit our website, use our
              application, or interact with our services.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">2. Information We Collect</h2>
            <p>
              We collect information that you provide directly to us, as well as data generated automatically when you
              use our platform.
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <strong>Account Data:</strong> When you register, we collect your name, email address, brokerage
                information, and account credentials.
              </li>
              <li>
                <strong>Property &amp; Asset Data:</strong> To provide our core services, we collect the property details,
                MLS numbers, floorplans, and visual assets (photos and videos) you upload to the platform.
              </li>
              <li>
                <strong>Billing Information:</strong> We use a third-party payment processor (Stripe) to handle payments.
                We do not store full credit card numbers on our servers; we only retain transaction history and billing
                addresses.
              </li>
              <li>
                <strong>Usage Data:</strong> We automatically collect data regarding your interaction with our platform,
                including IP addresses, browser types, interaction times, and navigation paths.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">
              3. Artificial Intelligence &amp; Third-Party Vendor Disclosures
            </h2>
            <p>
              ListingJet relies on third-party Artificial Intelligence (AI) vendors to process your assets and generate
              marketing materials. By uploading property data and images to our platform, you acknowledge that this data
              will be securely transmitted to these vendors for processing.
            </p>
            <p className="font-semibold text-[var(--color-text)]">Our Current AI Processing Partners:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <strong>Google Cloud Vision API</strong> &mdash; Initial image ingestion, bulk tagging, and basic visual
                scoring.
              </li>
              <li>
                <strong>OpenAI (GPT-4V / DALL-E 3)</strong> &mdash; Deep image analysis, automated 3D floorplan JSON generation,
                chapter marker extraction, compliance detection (identifying MLS violations such as visible yard
                signs or people), virtual staging of empty rooms, AI image editing (object removal, lighting
                enhancement), and CMA report narrative generation.
              </li>
              <li>
                <strong>Anthropic (Claude 3)</strong> &mdash; Dual-tone property descriptions (MLS-compliant and
                marketing-heavy) and social media captions based on property data.
              </li>
              <li>
                <strong>Kling AI</strong> &mdash; Image-to-video generation, rendering static property photos into
                dynamic video tours.
              </li>
              <li>
                <strong>ElevenLabs</strong> &mdash; AI-generated voiceover narration for video tours (when enabled
                in your Brand Kit settings or per-listing override).
              </li>
            </ul>
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 mt-3">
              <p className="font-semibold text-[var(--color-text)] text-sm mb-1">AI Data Usage &amp; Training</p>
              <p className="text-sm">
                We utilize API enterprise agreements with our AI vendors. Under these agreements, the data (images,
                floorplans, and property details) we transmit to OpenAI, Anthropic, Google Cloud, Kling AI, and ElevenLabs is{" "}
                <strong>strictly used for fulfilling your immediate request</strong> (e.g., generating a description or
                video). Our agreements stipulate that your submitted data and assets are{" "}
                <strong>not</strong> used by these vendors to train their foundational machine learning models.
              </p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">4. How We Use Your Data</h2>
            <p>We use the collected information for the following purposes:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>To operate, maintain, and deliver the ListingJet platform and generation pipelines.</li>
              <li>
                To process transactions and send related information, including confirmations and invoices.
              </li>
              <li>
                To detect and flag compliance violations within your uploaded assets before MLS syndication.
              </li>
              <li>
                To adapt our internal machine learning models to your specific organizational branding. When you override
                or adjust our AI&apos;s photo selections, our internal system logs these preferences to improve future
                asset scoring specifically for your account.
              </li>
              <li>To respond to your comments, questions, and customer service requests.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">5. Data Sharing and Disclosure</h2>
            <p>
              We do not sell your personal data. We may share your information in the following situations:
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <strong>Service Providers:</strong> With vendors (like AWS for S3 storage, Stripe for payments, and the
                AI providers listed in Section 3) who need access to such information to carry out work on our behalf.
              </li>
              <li>
                <strong>Legal Compliance:</strong> If required to do so by law or in response to valid requests by public
                authorities.
              </li>
              <li>
                <strong>Business Transfers:</strong> In connection with, or during negotiations of, any merger, sale of
                company assets, financing, or acquisition.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">6. Data Security and Retention</h2>
            <p>
              We implement industry-standard security measures, including database encryption at rest (AES-256),
              Row-Level Security (RLS) for tenant isolation, and TLS 1.2+ for all data in transit, to protect your
              personal information and property assets from unauthorized access.
            </p>
            <p>We retain your data according to the following schedule:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>
                <strong>Account &amp; listing data:</strong> Retained for as long as your account is active or as
                needed to provide services.
              </li>
              <li>
                <strong>Export bundles (ZIP packages):</strong> Automatically deleted after 90 days. Generated media
                links are delivered via time-bound presigned URLs.
              </li>
              <li>
                <strong>Webhook delivery logs:</strong> Automatically purged after 30 days.
              </li>
              <li>
                <strong>Account deletion requests:</strong> Processed within 30 days. All personal data, listing
                assets, and associated records are purged from our systems.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">7. Your Privacy Rights</h2>
            <p>
              Depending on your jurisdiction (such as California under the CCPA/CPRA), you may have the right to:
            </p>
            <ul className="list-disc pl-5 space-y-1">
              <li>Access the personal information we hold about you.</li>
              <li>Request the correction of inaccurate data.</li>
              <li>Request the deletion of your account and associated personal data.</li>
              <li>Opt-out of certain data processing activities.</li>
            </ul>
            <p>
              If you delete your account, your historical asset overrides used to train your organization&apos;s specific
              photo-scoring weights will be anonymized or purged in accordance with our data retention policies.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">8. Contact Us</h2>
            <p>
              If you have any questions, concerns, or requests regarding this Privacy Policy or our AI vendor usage,
              please contact us at:
            </p>
            <p className="font-semibold text-[var(--color-text)]">
              ListingJet Support<br />
              <a href="mailto:support@listingjet.ai" className="text-[#F97316] hover:underline font-normal">
                support@listingjet.ai
              </a>
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
