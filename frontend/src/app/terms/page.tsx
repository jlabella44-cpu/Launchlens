export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-[#F5F7FA] py-16 px-4">
      <div className="max-w-3xl mx-auto bg-white rounded-xl shadow-sm p-8 md:p-12">
        <h1
          className="text-3xl font-bold text-[var(--color-text)] mb-2"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Terms of Service for ListingJet
        </h1>
        <p className="text-sm text-slate-400 mb-8">Effective date: April 3, 2026</p>

        <div className="prose prose-slate prose-sm max-w-none space-y-6 text-[var(--color-text-secondary)]">
          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">1. Acceptance of Terms</h2>
            <p>
              By creating an account, accessing, or using the ListingJet platform (&ldquo;ListingJet,&rdquo;
              &ldquo;we,&rdquo; &ldquo;us,&rdquo; or &ldquo;our&rdquo;), you agree to be bound by these Terms of
              Service (&ldquo;Terms&rdquo;). If you are using the platform on behalf of a real estate brokerage,
              agency, or organization, you represent that you have the authority to bind that organization to these
              Terms.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">2. Description of Service</h2>
            <p>
              ListingJet is an automated, AI-driven real estate marketing platform. We provide tools for processing
              real estate visual assets, generating property descriptions, creating 3D floorplans, rendering video
              tours, and delivering final marketing and MLS-compliant bundles. The Service is provided on a
              subscription and/or per-credit basis as described on our Pricing page.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">
              3. Account Registration and Security
            </h2>
            <p>
              You are responsible for maintaining the confidentiality of your account credentials and for all
              activities that occur under your account. ListingJet utilizes isolated database architecture and
              Row-Level Security (RLS) to secure tenant data, but you must immediately notify us of any unauthorized
              use of your account or security breaches.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">
              4. Billing, Payments, and Credits
            </h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>
                <strong>Payment Processing:</strong> All payments are processed securely through our third-party
                payment provider (Stripe). By purchasing a subscription or processing credits, you authorize
                ListingJet to charge your selected payment method.
              </li>
              <li>
                <strong>Credits &amp; Usage:</strong> Processing properties through our AI pipelines consumes
                credits. Credits are deducted upon the successful initiation of a property workflow. Unused credits
                roll over month-to-month subject to your plan&apos;s rollover cap. Cancelled listings receive a
                credit refund.
              </li>
              <li>
                <strong>Refunds:</strong> Due to the direct computational costs incurred by third-party AI vendors
                for processing assets, completed pipeline generations are non-refundable.
              </li>
              <li>
                <strong>Pricing Changes:</strong> We reserve the right to change pricing with 30 days&apos; notice.
                Material changes will be communicated via email before they take effect.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">
              5. User Content and Asset Ownership
            </h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>
                <strong>Your Uploads:</strong> You retain full ownership of all property data, photos, floorplans,
                and other assets you upload to ListingJet (&ldquo;User Content&rdquo;). You represent and warrant
                that you have the necessary rights, licenses, and permissions from the property owner or copyright
                holder to upload and process these assets.
              </li>
              <li>
                <strong>License to Process:</strong> By uploading User Content, you grant ListingJet a limited,
                worldwide, non-exclusive license to host, process, and transmit your data to our third-party AI
                partners strictly for the purpose of generating your requested marketing materials.
              </li>
              <li>
                <strong>Generated Outputs:</strong> You own the final generated marketing copy, video tours, and
                processed images, subject to the licensing terms of our underlying AI providers.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">
              6. Artificial Intelligence and MLS Compliance
            </h2>
            <p className="font-semibold text-[var(--color-text)]">AI Tooling</p>
            <p>
              ListingJet employs advanced artificial intelligence &mdash; including OpenAI, Anthropic, Google Cloud
              Vision, Kling AI, and ElevenLabs &mdash; to generate content, analyze images, render video tours, and
              produce voiceover narration. While we strive for high-quality outputs, AI-generated content may
              occasionally contain errors or inaccuracies. You are strictly responsible for reviewing all generated
              descriptions and assets before publication. Our enterprise agreements with these vendors stipulate that
              your data is not used for model training, as detailed in our{" "}
              <a href="/privacy" className="text-[#F97316] hover:underline">Privacy Policy</a>.
            </p>
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mt-3">
              <p className="font-semibold text-amber-900 text-sm mb-1">MLS Compliance Disclaimer</p>
              <p className="text-sm text-amber-800">
                ListingJet includes a compliance detection engine designed to flag potential Multiple Listing Service
                (MLS) violations (e.g., visible yard signs, branding, or people in photos).{" "}
                <strong>
                  This tool is provided as a best-effort assistant. ListingJet does not guarantee complete compliance
                  with your specific local MLS rules.
                </strong>{" "}
                You act as the final publisher and assume all liability for any MLS fines, penalties, or rejections
                resulting from uploaded assets.
              </p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">7. Acceptable Use</h2>
            <p>You agree not to use ListingJet to:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>Upload illegal, explicit, or unauthorized content</li>
              <li>Upload content you do not have the right to use or distribute</li>
              <li>Use the Service to generate misleading, fraudulent, or deceptive listing materials</li>
              <li>
                Reverse engineer, decompile, or attempt to extract the source code or AI prompts of the platform
              </li>
              <li>Attempt to bypass rate limits, payment webhooks, or orchestration pipelines</li>
              <li>Share account credentials or API keys with unauthorized parties</li>
              <li>
                Resell the service as a standalone API or white-label product without explicit written consent from
                ListingJet
              </li>
              <li>
                Use the Service in violation of any applicable real estate regulations, Fair Housing laws, or MLS
                rules
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">
              8. Service Availability and AI Vendor Uptime
            </h2>
            <p>
              Because our platform relies heavily on third-party generative AI APIs, ListingJet&apos;s availability
              and processing times are subject to the uptime of these vendors. We do not guarantee uninterrupted
              service and are not liable for pipeline delays or failures caused by upstream API outages, rate limits,
              or third-party provider maintenance windows.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">9. Termination</h2>
            <p>
              Either party may terminate the agreement at any time. You can cancel your subscription via the Billing
              page or by contacting support. We reserve the right to suspend or terminate your account immediately,
              without prior notice, if you breach these Terms. Upon termination, your access to the platform will
              cease and your historical data, customized AI photo-scoring weights, and uploaded assets will be slated
              for deletion in accordance with our{" "}
              <a href="/privacy" className="text-[#F97316] hover:underline">Privacy Policy</a> retention schedule.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">10. Limitation of Liability</h2>
            <p>
              To the maximum extent permitted by law, ListingJet and its affiliates shall not be liable for any
              indirect, incidental, special, consequential, or punitive damages, including loss of profits, data, or
              business opportunities, arising out of your use of or inability to use the platform. Our total
              liability for any claim shall not exceed the amount you paid us in the 12 months preceding the claim.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">11. Changes to Terms</h2>
            <p>
              We may update these Terms from time to time. Material changes will be communicated via email or an
              in-app notice at least 30 days before they take effect. Continued use of the Service after changes
              become effective constitutes acceptance of the updated Terms.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">12. Governing Law</h2>
            <p>
              These Terms shall be governed by and construed in accordance with the laws of the State of Delaware,
              without regard to its conflict of law provisions. Any disputes shall be resolved through binding
              arbitration in accordance with the rules of the American Arbitration Association, except that either
              party may seek injunctive relief in any court of competent jurisdiction.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">13. Contact Information</h2>
            <p>
              For legal inquiries or questions regarding these Terms, please contact us at:
            </p>
            <p className="font-semibold text-[var(--color-text)]">
              ListingJet Legal<br />
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
