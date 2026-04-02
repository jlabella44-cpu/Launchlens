"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import apiClient from "@/lib/api-client";
import type { BrandKitResponse } from "@/lib/types";

import BrokerageInfoSection from "./_components/brokerage-info-section";
import BrandColorsSection from "./_components/brand-colors-section";
import TypographySection from "./_components/typography-section";
import BrandVoiceSection from "./_components/brand-voice-section";
import LogosSection from "./_components/logos-section";
import HudPreview from "./_components/hud-preview";

/* ─── Extended form state (includes raw_config fields) ─── */

interface BrandKitFormState {
  brokerage_name: string;
  agent_name: string;
  primary_color: string;
  secondary_color: string;
  font_primary: string;
  logo_url: string | null;
  headshot_url: string | null;
  team_logo_url: string | null;
  // Phase 2 fields (stored in raw_config)
  accent_color: string;
  background_color: string;
  font_secondary: string;
  brand_voice: string;
  brand_tone: string;
  voice_notes: string;
}

const DEFAULTS: BrandKitFormState = {
  brokerage_name: "",
  agent_name: "",
  primary_color: "#0F1B2D",
  secondary_color: "#FF6B2C",
  font_primary: "",
  logo_url: null,
  headshot_url: null,
  team_logo_url: null,
  accent_color: "",
  background_color: "",
  font_secondary: "",
  brand_voice: "",
  brand_tone: "",
  voice_notes: "",
};

/* ─── Upload helper (shared by logo, headshot, team-logo) ─── */

async function uploadToS3(
  getUrl: () => Promise<{ key: string; upload: Record<string, unknown> }>,
  file: File,
): Promise<string> {
  const { key, upload } = await getUrl();
  const presigned = upload as { url: string; fields: Record<string, string> };
  const fd = new FormData();
  Object.entries(presigned.fields).forEach(([k, v]) => fd.append(k, v));
  fd.append("file", file);
  const resp = await fetch(presigned.url, { method: "POST", body: fd });
  if (!resp.ok) {
    console.error("S3 upload failed:", resp.status);
  }
  return `s3://${key}`;
}

/* ─── Main component ─── */

function BrandKitSettings() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [form, setForm] = useState<BrandKitFormState>(DEFAULTS);

  // Preserve unknown raw_config keys across saves
  const rawConfigExtrasRef = useRef<Record<string, unknown>>({});

  // Upload states
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [uploadingTeamLogo, setUploadingTeamLogo] = useState(false);
  const [uploadingHeadshot, setUploadingHeadshot] = useState(false);

  // Local previews (ObjectURLs before S3 confirms)
  const [brokerageLogoPreview, setBrokerageLogoPreview] = useState<string | null>(null);
  const [teamLogoPreview, setTeamLogoPreview] = useState<string | null>(null);
  const [headshotPreview, setHeadshotPreview] = useState<string | null>(null);

  useEffect(() => { document.title = "Brand Kit | ListingJet"; }, []);

  /* ─── Load existing brand kit ─── */
  useEffect(() => {
    apiClient
      .getBrandKit()
      .then((kit: BrandKitResponse | null) => {
        if (kit) {
          const rc = kit.raw_config || {};
          // Extract known raw_config keys, preserve the rest
          const {
            headshot_url, team_logo_url,
            accent_color, background_color, font_secondary,
            brand_voice, brand_tone, voice_notes,
            ...extras
          } = rc as Record<string, unknown>;
          rawConfigExtrasRef.current = extras;

          setForm({
            brokerage_name: kit.brokerage_name || "",
            agent_name: kit.agent_name || "",
            primary_color: kit.primary_color || "#0F1B2D",
            secondary_color: kit.secondary_color || "#FF6B2C",
            font_primary: kit.font_primary || "",
            logo_url: kit.logo_url || null,
            headshot_url: (headshot_url as string) || null,
            team_logo_url: (team_logo_url as string) || null,
            accent_color: (accent_color as string) || "",
            background_color: (background_color as string) || "",
            font_secondary: (font_secondary as string) || "",
            brand_voice: (brand_voice as string) || "",
            brand_tone: (brand_tone as string) || "",
            voice_notes: (voice_notes as string) || "",
          });
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  /* ─── Upload handlers ─── */

  const handleBrokerageLogoUpload = useCallback(async (file: File) => {
    if (!file.type.startsWith("image/")) return;
    setBrokerageLogoPreview(URL.createObjectURL(file));
    setUploadingLogo(true);
    try {
      const s3Key = await uploadToS3(() => apiClient.getLogoUploadUrl(), file);
      setForm((f) => ({ ...f, logo_url: s3Key }));
    } catch (err) {
      console.error("Logo upload failed:", err);
    } finally {
      setUploadingLogo(false);
    }
  }, []);

  const handleTeamLogoUpload = useCallback(async (file: File) => {
    if (!file.type.startsWith("image/")) return;
    setTeamLogoPreview(URL.createObjectURL(file));
    setUploadingTeamLogo(true);
    try {
      const s3Key = await uploadToS3(() => apiClient.getTeamLogoUploadUrl(), file);
      setForm((f) => ({ ...f, team_logo_url: s3Key }));
    } catch (err) {
      console.error("Team logo upload failed:", err);
    } finally {
      setUploadingTeamLogo(false);
    }
  }, []);

  const handleHeadshotUpload = useCallback(async (file: File) => {
    if (!file.type.startsWith("image/")) return;
    setHeadshotPreview(URL.createObjectURL(file));
    setUploadingHeadshot(true);
    try {
      const s3Key = await uploadToS3(() => apiClient.getHeadshotUploadUrl(), file);
      setForm((f) => ({ ...f, headshot_url: s3Key }));
    } catch (err) {
      console.error("Headshot upload failed:", err);
    } finally {
      setUploadingHeadshot(false);
    }
  }, []);

  /* ─── Save ─── */

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    try {
      const {
        headshot_url, team_logo_url,
        accent_color, background_color, font_secondary,
        brand_voice, brand_tone, voice_notes,
        ...topLevel
      } = form;
      await apiClient.upsertBrandKit({
        ...topLevel,
        raw_config: {
          ...rawConfigExtrasRef.current,
          headshot_url,
          team_logo_url,
          accent_color,
          background_color,
          font_secondary,
          brand_voice,
          brand_tone,
          voice_notes,
        },
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error("Failed to save brand kit:", err);
    } finally {
      setSaving(false);
    }
  }

  /* ─── Loading skeleton ─── */

  if (loading) {
    return (
      <>
        <Nav />
        <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
          <div className="h-96 rounded-2xl bg-[var(--color-surface)] animate-pulse border border-[var(--color-card-border)]" />
        </main>
      </>
    );
  }

  /* ─── Render ─── */

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-[1200px] mx-auto w-full px-4 sm:px-6 py-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          {/* Header */}
          <div className="mb-10">
            <div className="flex items-center gap-2 mb-2">
              <svg className="w-5 h-5 text-[#F97316]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span className="text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-secondary)] font-semibold">
                Configuration Protocol
              </span>
            </div>
            <h1
              className="text-4xl font-bold text-[var(--color-text)]"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              Brand Kit
            </h1>
            <p className="text-base text-[var(--color-text-secondary)] mt-2">
              Calibrate your visual signature for the real estate stratosphere.
            </p>
          </div>

          {/* Two-column layout: 7/5 split matching Stitch */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Left: Form Sections */}
            <div className="lg:col-span-7 space-y-6">
              <BrokerageInfoSection
                form={form}
                setForm={setForm}
                onHeadshotUpload={handleHeadshotUpload}
                headshotPreview={headshotPreview}
                uploadingHeadshot={uploadingHeadshot}
              />
              <BrandColorsSection form={form} setForm={setForm} />
              <TypographySection form={form} setForm={setForm} />
              <BrandVoiceSection form={form} setForm={setForm} />
              <LogosSection
                form={form}
                setForm={setForm}
                onBrokerageLogoUpload={handleBrokerageLogoUpload}
                onTeamLogoUpload={handleTeamLogoUpload}
                brokerageLogoPreview={brokerageLogoPreview}
                teamLogoPreview={teamLogoPreview}
                uploadingLogo={uploadingLogo}
                uploadingTeamLogo={uploadingTeamLogo}
              />
            </div>

            {/* Right: Live HUD Preview */}
            <div className="lg:col-span-5">
              <HudPreview
                form={form}
                brokerageLogoPreview={brokerageLogoPreview}
                headshotPreview={headshotPreview}
                teamLogoPreview={teamLogoPreview}
                saving={saving}
                saved={saved}
                onSave={handleSave}
              />
            </div>
          </div>
        </motion.div>

        {/* Footer */}
        <footer className="mt-16 pt-6 border-t border-[var(--color-card-border)] flex items-center justify-between text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)]">
          <span>ListingJet Command</span>
          <div className="flex gap-6">
            <span>Flight Manual</span>
            <span>Ground Control</span>
            <span>Hangar Support</span>
          </div>
        </footer>
      </main>
    </>
  );
}

export default function SettingsPage() {
  return (
    <ProtectedRoute>
      <BrandKitSettings />
    </ProtectedRoute>
  );
}
