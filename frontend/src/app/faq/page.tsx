"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";

const FAQ_DATA = [
  {
    category: "Getting Started",
    items: [
      {
        q: "What is ListingJet?",
        a: "ListingJet is an AI-powered real estate listing media platform. Upload your property photos and our 15-agent AI pipeline automatically curates, scores, and packages them into MLS bundles, branded flyers, listing descriptions, social media content, and video tours.",
      },
      {
        q: "How do I upload my first listing?",
        a: "Go to Dashboard > click 'New Listing' > enter the property address > drag and drop your photos (JPG or PNG, up to 50 files). The AI pipeline starts automatically after upload.",
      },
      {
        q: "What file formats are supported?",
        a: "We accept JPG and PNG images, up to 20MB each. You can upload up to 50 photos per listing.",
      },
      {
        q: "How long does processing take?",
        a: "Most listings complete in 5-15 minutes. The AI analyzes your photos, selects the best shots, and generates all marketing materials. You'll get an email when it's ready.",
      },
    ],
  },
  {
    category: "Listings & Pipeline",
    items: [
      {
        q: "What do the listing states mean?",
        a: "Upload: Photos being uploaded. Analyze: AI scoring and classifying photos. Review: Photos packaged and awaiting approval. Create: Generating descriptions, flyers, social content, and videos. Delivered: Everything is ready to download.",
      },
      {
        q: "My listing is stuck or failed — what do I do?",
        a: "Go to your listing detail page and click 'Retry Pipeline'. This restarts processing from where it left off. If it fails again, contact support — our team can investigate.",
      },
      {
        q: "Can I retry a failed listing?",
        a: "Yes. On the listing detail page, you'll see a 'Retry' button for any listing in a failed or timed-out state. Retrying doesn't cost additional credits.",
      },
      {
        q: "How does the AI photo selection work?",
        a: "Our AI uses computer vision to analyze each photo for quality, room type, composition, and commercial appeal. It selects the best 25 photos and ranks them with a hero shot first. You can review and reorder the selection before approval.",
      },
    ],
  },
  {
    category: "Credits & Billing",
    items: [
      {
        q: "How do credits work?",
        a: "Credits are the currency for all ListingJet services. Each service costs a different number of credits based on its complexity: a base listing is 12 credits, an AI video tour is 20 credits, virtual staging is 15 credits, a 3D floorplan is 8 credits, and so on. Credits are included monthly with your plan and can also be purchased in top-up bundles. Unused plan credits roll over to the next month (up to your plan's rollover cap). Purchased credits never expire.",
      },
      {
        q: "What plans are available?",
        a: "Free: $0/mo, pay-as-you-go credits at $0.50 each. Lite: $19/mo with 25 credits included (rollover cap 15). Active Agent: $49/mo with 75 credits included (rollover cap 50). Team: $99/mo with 250 credits included (rollover cap 150). Higher tiers get better per-credit rates on top-up bundles.",
      },
      {
        q: "How do I buy more credits?",
        a: "Go to Billing > Buy Credits. We offer bundles of 25, 50, 100, or 250 credits. Pricing is locked to your membership tier — higher tiers get lower per-credit rates. For example, on Active Agent a 100-credit bundle is $33.99 ($0.34/credit).",
      },
      {
        q: "What happens if I run out of credits?",
        a: "You won't be able to start new listings or activate add-ons until you purchase more credits or your monthly allocation renews. Existing listings in progress will continue to completion.",
      },
      {
        q: "How does the rollover cap work?",
        a: "At the end of each billing period, unused plan-granted credits carry over to the next month — up to your plan's rollover cap. Credits above the cap expire. Purchased (top-up) credits never expire and are not subject to the rollover cap. Plan-granted credits are always consumed first.",
      },
      {
        q: "How much does each service cost in credits?",
        a: "Base Listing: 12 credits. AI Video Tour: 20 credits. Virtual Staging: 15 credits. 3D Floorplan: 8 credits. AI Image Editing: 6 credits. CMA Report: 5 credits. Photo Compliance: 3 credits. Social Media Cuts: 3 credits. Social Content Pack: 2 credits. Microsite: 2 credits.",
      },
    ],
  },
  {
    category: "Team & Permissions",
    items: [
      {
        q: "How do I invite team members?",
        a: "Go to Settings > Team > click 'Invite Member'. Enter their email, set a temporary password, and choose their role. They'll be able to log in immediately.",
      },
      {
        q: "What are the different user roles?",
        a: "Admin: Full access including team management and review queue. Operator: Day-to-day operations. Agent: Can manage their own listings. Viewer: Read-only access to listings and analytics.",
      },
      {
        q: "Can I share listings with people outside my team?",
        a: "Yes. On any listing detail page, click 'Share' to grant read or edit access to specific users. You can also set blanket access grants for team members in Settings > Team.",
      },
    ],
  },
  {
    category: "Add-ons & Features",
    items: [
      {
        q: "What premium add-ons are available?",
        a: "AI Video Tour (20 credits): cinematic walkthroughs with narration. Virtual Staging (15 credits): furnish empty rooms in 6 styles. 3D Floorplan (8 credits): interactive dollhouse visualization. AI Image Editing (6 credits): remove objects, fix lighting. CMA Report (5 credits): AI-generated market analysis. Social Media Cuts (3 credits): platform-ready clips for TikTok, Instagram, and Facebook. Social Content Pack (2 credits): captions and hashtags. Microsite (2 credits): branded single-property website.",
      },
      {
        q: "What is the Brand Kit?",
        a: "Your Brand Kit customizes all generated content with your branding — logo, colors, agent name, and brokerage. Set it up in Settings and it applies automatically to flyers, videos, and social content.",
      },
      {
        q: "Does ListingJet support video tours?",
        a: "Yes. AI-generated video tours are available as an add-on. The AI selects the best photos, creates a cinematic sequence with transitions, and can add narration. Social-ready clips for TikTok and Instagram Reels are also generated.",
      },
    ],
  },
];

function FAQItem({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border-b border-[var(--color-card-border)] last:border-b-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between py-4 text-left"
      >
        <span className="text-sm font-medium text-[var(--color-text)] pr-4">{question}</span>
        <svg
          className={`w-4 h-4 shrink-0 text-[var(--color-text-secondary)] transition-transform ${open ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <motion.div
        initial={false}
        animate={{ height: open ? "auto" : 0, opacity: open ? 1 : 0 }}
        transition={{ duration: 0.2 }}
        className="overflow-hidden"
      >
        <p className="text-sm text-[var(--color-text-secondary)] pb-4 leading-relaxed">
          {answer}
        </p>
      </motion.div>
    </div>
  );
}

export default function FAQPage() {
  useEffect(() => { document.title = "FAQ | ListingJet"; }, []);

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-3xl mx-auto w-full px-4 sm:px-6 py-12">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <div className="text-center mb-10">
            <h1 className="text-4xl font-bold text-[var(--color-text)]" style={{ fontFamily: "var(--font-heading)" }}>
              Frequently Asked Questions
            </h1>
            <p className="text-[var(--color-text-secondary)] mt-2">
              Everything you need to know about ListingJet.
            </p>
          </div>

          <div className="space-y-8">
            {FAQ_DATA.map((section) => (
              <div key={section.category}>
                <h2 className="text-lg font-semibold text-[var(--color-text)] mb-3" style={{ fontFamily: "var(--font-heading)" }}>
                  {section.category}
                </h2>
                <div className="rounded-2xl border border-[var(--color-card-border)] bg-[var(--color-surface)] px-5">
                  {section.items.map((item) => (
                    <FAQItem key={item.q} question={item.q} answer={item.a} />
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* CTA */}
          <div className="text-center mt-12 p-8 rounded-2xl border border-[var(--color-card-border)] bg-[var(--color-surface)]">
            <h3 className="text-lg font-semibold text-[var(--color-text)]" style={{ fontFamily: "var(--font-heading)" }}>
              Still have questions?
            </h3>
            <p className="text-sm text-[var(--color-text-secondary)] mt-2 mb-4">
              Our AI assistant can answer most questions instantly, or you can create a support ticket.
            </p>
            <div className="flex justify-center gap-3">
              <Link href="/support"
                className="px-5 py-2.5 rounded-lg text-sm font-semibold text-white" style={{ background: "linear-gradient(135deg, #F97316, #FB923C)" }}>
                Contact Support
              </Link>
              <Link href="/demo"
                className="px-5 py-2.5 rounded-lg text-sm font-semibold border border-[var(--color-card-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text)]">
                Try the Demo
              </Link>
            </div>
          </div>
        </motion.div>
      </main>
    </>
  );
}
