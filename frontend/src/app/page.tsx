"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { Nav } from "@/components/layout/nav";
import { trackEvent } from "@/lib/analytics";

/* ───────────────────────── data ───────────────────────── */

const services = [
  {
    title: "AI Photo Analysis",
    desc: "Smart ranking, room detection, quality scoring, and MLS compliance checks — all automated.",
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0Z" />
      </svg>
    ),
  },
  {
    title: "Listing Descriptions",
    desc: "Dual-tone AI copywriting: formal MLS descriptions plus engaging marketing copy.",
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
      </svg>
    ),
  },
  {
    title: "Video Tours",
    desc: "Automated property tour videos generated from your best photos with professional narration.",
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" />
      </svg>
    ),
  },
  {
    title: "3D Floorplans",
    desc: "AI-generated floor plans that give buyers spatial context before they visit.",
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="m21 7.5-9-5.25L3 7.5m18 0-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
      </svg>
    ),
  },
  {
    title: "Social Content",
    desc: "Instagram, Facebook, and TikTok-ready cuts with your branding and optimal aspect ratios.",
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 1 0 0 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186 9.566-5.314m-9.566 7.5 9.566 5.314m0 0a2.25 2.25 0 1 0 3.935 2.186 2.25 2.25 0 0 0-3.935-2.186Zm0-12.814a2.25 2.25 0 1 0 3.933-2.185 2.25 2.25 0 0 0-3.933 2.185Z" />
      </svg>
    ),
  },
  {
    title: "MLS Export",
    desc: "One-click export to MLS with compliant formatting, plus downloadable marketing packages.",
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
      </svg>
    ),
  },
  {
    title: "Virtual Staging",
    desc: "Transform empty rooms into beautifully furnished spaces with AI staging in 6 design styles.",
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 21v-4.875c0-.621.504-1.125 1.125-1.125h5.25c.621 0 1.125.504 1.125 1.125V21m0 0h4.5V3.545M12.75 21h7.5M10.5 21V8.25a1.125 1.125 0 0 1 .375-.838l5.25-4.5a1.125 1.125 0 0 1 1.5 0l5.25 4.5" />
      </svg>
    ),
  },
  {
    title: "AI Photo Editing",
    desc: "Remove yard signs, fix lighting, declutter rooms — one-click compliance auto-fix.",
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
      </svg>
    ),
  },
  {
    title: "CMA Reports",
    desc: "AI-generated Comparative Market Analysis with neighborhood comps and pricing insights.",
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
      </svg>
    ),
  },
  {
    title: "Property Microsites",
    desc: "Branded single-property websites with QR codes for yard signs and open houses.",
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418" />
      </svg>
    ),
  },
];

const steps = [
  {
    title: "Upload",
    desc: "Drag & drop photos or paste a Google Drive / Show & Tour delivery link",
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z" />
      </svg>
    ),
  },
  {
    title: "Analyze",
    desc: "AI processes, ranks, and tags every photo in seconds",
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23.693L5 14.5m14.8.8 1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0 1 12 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
      </svg>
    ),
  },
  {
    title: "Review",
    desc: "Preview your MLS and marketing packages, approve or adjust",
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
      </svg>
    ),
  },
  {
    title: "Deliver",
    desc: "Export to MLS, download bundles, or share social content instantly",
    icon: (
      <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
      </svg>
    ),
  },
];

const faqs = [
  {
    q: "What file formats do you support?",
    a: "JPEG, PNG, WebP, and HEIC. Photos up to 20MB each, up to 100 per listing.",
  },
  {
    q: "How long does processing take?",
    a: "Most listings are fully processed in under 5 minutes. Complex listings with video and floorplans may take up to 15 minutes.",
  },
  {
    q: "Can I use my own branding?",
    a: "Yes! Lite and Active Agent plans include full white-label support. Upload your logo, set brand colors, and choose your fonts.",
  },
  {
    q: "What MLS systems do you integrate with?",
    a: "We support RESO-compliant MLS systems. Export packages include properly formatted photos and descriptions.",
  },
  {
    q: "How do credits work?",
    a: "Each listing costs one credit. Plans include monthly credits, and you can purchase additional bundles at volume discounts.",
  },
  {
    q: "Is there a free trial?",
    a: "Our Free tier lets you process listings at $34 each with no subscription. Upgrade anytime for lower per-listing costs.",
  },
  {
    q: "Can you edit or stage listing photos?",
    a: "Yes! Our AI can remove yard signs, fix lighting, declutter rooms, and auto-fix MLS compliance issues. Virtual staging adds furniture to empty rooms in 6 design styles.",
  },
  {
    q: "What's included in a CMA report?",
    a: "Comparable sales in the area, price per sqft analysis, market trend narrative, and a branded PDF report styled with your brand kit.",
  },
  {
    q: "Do you support multiple languages?",
    a: "Yes — listing descriptions can be generated in 10 languages including Spanish, French, German, Portuguese, Chinese, Japanese, Korean, Italian, and Arabic.",
  },
  {
    q: "Can I create a website for a listing?",
    a: "Every delivered listing gets an auto-generated microsite with a photo gallery, video tour, property details, and a QR code for yard signs.",
  },
];

/* ───────────────────── component ──────────────────────── */

export default function Home() {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const handleSmoothScroll = (e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
    e.preventDefault();
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="min-h-screen bg-[#F1F5F9]">
      <Nav />

      {/* ─── 1. Hero ─── */}
      <section className="relative overflow-hidden bg-[#0B1120]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 lg:py-32 grid lg:grid-cols-2 gap-12 items-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <h1
              className="text-5xl lg:text-7xl font-bold text-white leading-tight"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              Put Your Listings on Autopilot
            </h1>
            <p className="mt-6 text-lg text-slate-400 max-w-xl leading-relaxed">
              AI-powered listing media automation for elite real estate professionals. Upload photos, get MLS-ready packages, marketing bundles, and social content — in minutes.
            </p>
            <div className="mt-6 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#F97316]/10 border border-[#F97316]/20">
              <span className="w-2 h-2 rounded-full bg-[#F97316] animate-pulse" />
              <span className="text-sm font-semibold text-[#F97316]">Founding 200</span>
              <span className="text-sm text-slate-400">— 30% off for life for early adopters</span>
            </div>
            <div className="mt-4 flex flex-wrap gap-4">
              <Link
                href="/register"
                onClick={() => trackEvent("cta_click", { location: "hero", label: "upload_first_listing" })}
                className="inline-flex items-center justify-center px-8 py-3.5 bg-[#F97316] hover:bg-[#EA580C] text-white font-semibold rounded-full transition-colors text-base"
              >
                Upload Your First Listing Free
              </Link>
              <a
                href="#workflow"
                onClick={(e) => handleSmoothScroll(e, "workflow")}
                className="inline-flex items-center justify-center px-8 py-3.5 border border-white/30 text-white font-semibold rounded-full hover:bg-white/10 transition-colors text-base"
              >
                See How It Works
              </a>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="hidden lg:block"
          >
            <div className="relative rounded-2xl overflow-hidden border border-white/10 shadow-2xl transform rotate-2 translate-x-6">
              <img
                src="/images/hero-dashboard.jpg"
                alt="ListingJet dashboard showing real estate analytics, property photo grid, and AI generation progress"
                className="w-full h-full object-cover"
              />
              {/* HUD Overlay */}
              <div className="absolute top-4 left-4 bg-white/80 backdrop-blur-md rounded-xl px-4 py-2 shadow-lg">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-[#F97316] rounded-full animate-pulse" />
                  <span className="text-[10px] font-bold uppercase tracking-widest text-slate-700">Processing Listing_084</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ─── 2. Social Proof Bar ─── */}
      <section className="bg-white border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center"
          >
            {[
              { value: "500+", label: "Listings Processed" },
              { value: "10x", label: "Faster Than Manual" },
              { value: "98%", label: "Approval Rate" },
              { value: "24/7", label: "Automated Processing" },
            ].map((stat, i) => (
              <div key={i}>
                <div className="text-3xl lg:text-4xl font-bold text-slate-900" style={{ fontFamily: "var(--font-heading)" }}>
                  {stat.value}
                </div>
                <div className="mt-1 text-sm text-slate-500">{stat.label}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ─── 2b. Testimonials ─── */}
      <section className="bg-[#0B1120]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                quote: "ListingJet cut my listing prep from 3 hours to 15 minutes. My clients think I hired a marketing team.",
                name: "Sarah M.",
                title: "Keller Williams, Phoenix",
              },
              {
                quote: "The AI descriptions are better than what I was writing manually. The dual-tone feature is genius.",
                name: "Marcus T.",
                title: "RE/MAX, Austin",
              },
              {
                quote: "I used to pay $400 per listing for photos and marketing. Now it's $29/month for unlimited. No brainer.",
                name: "Jennifer L.",
                title: "Coldwell Banker, Miami",
              },
            ].map((t, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6"
              >
                <div className="flex gap-1 mb-3">
                  {[...Array(5)].map((_, j) => (
                    <svg key={j} className="w-4 h-4 text-[#F97316]" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                  ))}
                </div>
                <p className="text-sm text-slate-300 leading-relaxed mb-4">&ldquo;{t.quote}&rdquo;</p>
                <div>
                  <p className="text-sm font-semibold text-white">{t.name}</p>
                  <p className="text-xs text-slate-500">{t.title}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── 3. Services Grid ─── */}
      <section id="services" className="bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 lg:py-28">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-14"
          >
            <h2 className="text-3xl lg:text-4xl font-bold text-slate-900" style={{ fontFamily: "var(--font-heading)" }}>
              Everything Your Listings Need
            </h2>
            <p className="mt-4 text-slate-500 max-w-2xl mx-auto">
              From photo intelligence to social content, ListingJet handles the entire listing media pipeline so you can focus on selling.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {services.map((svc, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="bg-white rounded-2xl border border-slate-100 p-6 hover:shadow-lg hover:-translate-y-1 transition-all"
              >
                <div className="text-[#F97316] mb-4">{svc.icon}</div>
                <h3 className="text-lg font-bold text-slate-900">{svc.title}</h3>
                <p className="mt-2 text-sm text-slate-500 leading-relaxed">{svc.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── 4. How It Works ─── */}
      <section id="workflow" className="bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 lg:py-28">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-14"
          >
            <h2 className="text-3xl lg:text-4xl font-bold text-slate-900" style={{ fontFamily: "var(--font-heading)" }}>
              How It Works
            </h2>
            <p className="mt-4 text-slate-500">From photos to packages in four steps</p>
          </motion.div>

          <div className="relative grid grid-cols-1 lg:grid-cols-4 gap-10 lg:gap-6">
            {/* Connecting dotted line (desktop only) */}
            <div className="hidden lg:block absolute top-14 left-[12.5%] right-[12.5%] border-t-2 border-dashed border-slate-200" />

            {steps.map((step, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="relative flex flex-col items-center text-center"
              >
                <div className="relative z-10 w-12 h-12 rounded-full bg-[#F97316] flex items-center justify-center text-white font-bold text-lg mb-4">
                  {i + 1}
                </div>
                <div className="text-slate-600 mb-3">{step.icon}</div>
                <h3 className="text-lg font-bold text-slate-900">{step.title}</h3>
                <p className="mt-2 text-sm text-slate-500 max-w-xs">{step.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── 5. Benefits ─── */}
      <section className="bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 lg:py-28">
          {/* Stat blocks */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-20"
          >
            {[
              { title: "10x Faster", desc: "From upload to delivery in minutes, not hours" },
              { title: "White Label", desc: "Your brand, your logo, zero ListingJet watermarks on paid plans" },
              { title: "Always Consistent", desc: "Every listing gets the same professional treatment, every time" },
            ].map((b, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="bg-white rounded-2xl border border-slate-100 p-8 text-center"
              >
                <h3 className="text-2xl font-bold text-slate-900" style={{ fontFamily: "var(--font-heading)" }}>
                  {b.title}
                </h3>
                <p className="mt-3 text-slate-500">{b.desc}</p>
              </motion.div>
            ))}
          </motion.div>

          {/* Feature row 1: image left, text right */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="grid lg:grid-cols-2 gap-12 items-center mb-20"
          >
            <div className="rounded-2xl overflow-hidden aspect-video border border-slate-100 shadow-lg bg-slate-100">
              <img
                src="/images/photo-intelligence.jpg"
                alt="Before and after: dark unedited room transformed into a brightly lit, professionally enhanced space"
                className="w-full h-full object-cover"
              />
            </div>
            <div>
              <h3 className="text-2xl lg:text-3xl font-bold text-slate-900" style={{ fontFamily: "var(--font-heading)" }}>
                Smart Photo Intelligence
              </h3>
              <p className="mt-4 text-slate-500 leading-relaxed">
                Our AI doesn&apos;t just organize photos — it understands them. Room detection, quality scoring, hero selection, and MLS compliance checks happen automatically.
              </p>
            </div>
          </motion.div>

          {/* Feature row 2: text left, image right */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="grid lg:grid-cols-2 gap-12 items-center"
          >
            <div className="order-2 lg:order-1">
              <h3 className="text-2xl lg:text-3xl font-bold text-slate-900" style={{ fontFamily: "var(--font-heading)" }}>
                Built for Teams
              </h3>
              <p className="mt-4 text-slate-500 leading-relaxed">
                From solo agents to large brokerages. White-label branding, credit-based billing, and MLS integrations that scale with your business.
              </p>
            </div>
            <div className="order-1 lg:order-2 rounded-2xl overflow-hidden aspect-video border border-slate-100 shadow-lg bg-slate-100">
              <img
                src="/images/built-for-teams.jpg"
                alt="Team collaboration dashboard with agent profiles, shared listing analytics, and credit usage metrics"
                className="w-full h-full object-cover"
              />
            </div>
          </motion.div>
        </div>
      </section>

      {/* ─── 6. Pricing Preview ─── */}
      <section id="pricing" className="bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 lg:py-28">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-14"
          >
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#F97316]/10 border border-[#F97316]/20 mb-4">
              <span className="w-2 h-2 rounded-full bg-[#F97316] animate-pulse" />
              <span className="text-sm font-bold text-[#F97316]">Founding 200: 30% off for life</span>
            </div>
            <h2 className="text-3xl lg:text-4xl font-bold text-slate-900" style={{ fontFamily: "var(--font-heading)" }}>
              Simple, Transparent Pricing
            </h2>
            <p className="mt-4 text-slate-500 max-w-2xl mx-auto">
              Start free and scale as you grow. No hidden fees, no surprises. First 200 subscribers lock in founding pricing.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {[
              {
                name: "Free",
                price: "$0",
                period: "/mo",
                desc: "$34/listing, AI analysis, 30-day hosting",
                highlighted: false,
              },
              {
                name: "Lite",
                price: "$9",
                period: "/mo",
                desc: "$24/listing, permanent hosting, your branding",
                highlighted: false,
              },
              {
                name: "Active Agent",
                price: "$29",
                period: "/mo",
                desc: "1 included listing, $17 additional, full white-label",
                highlighted: true,
              },
            ].map((plan, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className={`bg-white rounded-2xl p-8 text-center transition-all ${
                  plan.highlighted
                    ? "border-2 border-[#F97316] shadow-lg shadow-orange-100"
                    : "border border-slate-100"
                }`}
              >
                <h3 className="text-lg font-bold text-slate-900">{plan.name}</h3>
                <div className="mt-4">
                  <span className="text-4xl font-bold text-slate-900" style={{ fontFamily: "var(--font-heading)" }}>
                    {plan.price}
                  </span>
                  <span className="text-slate-400">{plan.period}</span>
                </div>
                <p className="mt-4 text-sm text-slate-500">{plan.desc}</p>
              </motion.div>
            ))}
          </div>

          <div className="text-center mt-10">
            <Link href="/pricing" className="text-[#F97316] hover:text-[#EA580C] font-semibold transition-colors">
              View Full Pricing →
            </Link>
          </div>
        </div>
      </section>

      {/* ─── 7. FAQ ─── */}
      <section id="faq" className="bg-slate-50">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-20 lg:py-28">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center mb-14"
          >
            <h2 className="text-3xl lg:text-4xl font-bold text-slate-900" style={{ fontFamily: "var(--font-heading)" }}>
              Frequently Asked Questions
            </h2>
          </motion.div>

          <div className="space-y-3">
            {faqs.map((faq, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
              >
                <button
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="w-full bg-white rounded-2xl border border-slate-100 p-5 text-left flex items-center justify-between gap-4 hover:shadow-md transition-all"
                >
                  <span className="font-semibold text-slate-900">{faq.q}</span>
                  <motion.span
                    animate={{ rotate: openFaq === i ? 180 : 0 }}
                    transition={{ duration: 0.2 }}
                    className="shrink-0 text-slate-400"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                    </svg>
                  </motion.span>
                </button>
                <motion.div
                  initial={false}
                  animate={{
                    height: openFaq === i ? "auto" : 0,
                    opacity: openFaq === i ? 1 : 0,
                  }}
                  transition={{ duration: 0.3 }}
                  className="overflow-hidden"
                >
                  <div className="px-5 pb-4 pt-2 text-sm text-slate-500 leading-relaxed">
                    {faq.a}
                  </div>
                </motion.div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── 8. Final CTA ─── */}
      <section className="bg-[#0B1120]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-20 lg:py-28">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="text-center"
          >
            <h2
              className="text-3xl lg:text-5xl font-bold text-white"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              Ready to Launch Your Listings?
            </h2>
            <p className="mt-4 text-lg text-slate-400 max-w-xl mx-auto">
              Join the Founding 200 and lock in 30% off for life. Upload your first listing in 60 seconds.
            </p>
            <div className="mt-10">
              <Link
                href="/register"
                onClick={() => trackEvent("cta_click", { location: "footer", label: "upload_first_listing" })}
                className="inline-flex items-center justify-center px-10 py-4 bg-[#F97316] hover:bg-[#EA580C] text-white font-semibold rounded-full transition-colors text-lg"
              >
                Upload Your First Listing Free
              </Link>
            </div>
            <p className="mt-5 text-sm text-slate-500">
              No credit card required. Free tier available. Cancel anytime.
            </p>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
