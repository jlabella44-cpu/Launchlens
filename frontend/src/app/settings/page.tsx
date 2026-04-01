"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { Input } from "@/components/ui/input";
import { ColorPicker } from "@/components/ui/color-picker";
import { Select } from "@/components/ui/select";
import apiClient from "@/lib/api-client";
import type { BrandKitResponse, BrandKitUpsertRequest } from "@/lib/types";

const FONT_OPTIONS = [
  { value: "", label: "Select a font..." },
  { value: "Cinzel", label: "Cinzel" },
  { value: "Josefin Sans", label: "Josefin Sans" },
  { value: "Playfair Display", label: "Playfair Display" },
  { value: "Montserrat", label: "Montserrat" },
  { value: "Lato", label: "Lato" },
  { value: "Roboto", label: "Roboto" },
  { value: "Open Sans", label: "Open Sans" },
];

function BrandKitSettings() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState<BrandKitUpsertRequest>({
    brokerage_name: "",
    agent_name: "",
    primary_color: "#0F1B2D",
    secondary_color: "#FF6B2C",
    font_primary: "",
    logo_url: null,
  });

  useEffect(() => { document.title = "Brand Kit | ListingJet"; }, []);

  useEffect(() => {
    apiClient
      .getBrandKit()
      .then((kit: BrandKitResponse | null) => {
        if (kit) {
          setForm({
            brokerage_name: kit.brokerage_name || "",
            agent_name: kit.agent_name || "",
            primary_color: kit.primary_color || "#0F1B2D",
            secondary_color: kit.secondary_color || "#FF6B2C",
            font_primary: kit.font_primary || "",
            logo_url: kit.logo_url,
          });
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const [logoPreview, setLogoPreview] = useState<string | null>(null);

  const handleLogoUpload = useCallback(async (file: File) => {
    if (!file.type.startsWith("image/")) return;
    const localUrl = URL.createObjectURL(file);
    setLogoPreview(localUrl);
    setUploading(true);
    try {
      const { key, upload } = await apiClient.getLogoUploadUrl();
      const presigned = upload as { url: string; fields: Record<string, string> };
      const fd = new FormData();
      Object.entries(presigned.fields).forEach(([k, v]) => fd.append(k, v));
      fd.append("file", file);
      const resp = await fetch(presigned.url, { method: "POST", body: fd });
      if (!resp.ok) {
        console.error("S3 upload failed:", resp.status, await resp.text().catch(() => ""));
      }
      const s3Key = `s3://${key}`;
      setForm((f) => ({ ...f, logo_url: s3Key }));
    } catch (err) {
      console.error("Logo upload failed:", err);
      setForm((f) => ({ ...f, logo_url: "pending-upload" }));
    } finally {
      setUploading(false);
    }
  }, []);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    try {
      await apiClient.upsertBrandKit(form);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error("Failed to save brand kit:", err);
    } finally {
      setSaving(false);
    }
  }

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

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 py-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          {/* Header */}
          <p className="text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-secondary)] font-semibold mb-1">
            Configuration Protocol
          </p>
          <h1
            className="text-3xl font-bold text-[var(--color-text)] mb-1"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Brand Kit
          </h1>
          <p className="text-sm text-[var(--color-text-secondary)] mb-8">
            Calibrate your visual signature for the real estate stratosphere.
          </p>

          {/* Two-column layout */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
            {/* Left: Form Sections */}
            <div className="lg:col-span-3 space-y-6">
              {/* Brokerage Info */}
              <div className="bg-[var(--color-surface)] rounded-2xl border border-[var(--color-card-border)] p-6">
                <div className="flex items-center gap-2 mb-4">
                  <span className="w-8 h-8 rounded-full bg-[var(--color-background)] flex items-center justify-center text-sm">🏢</span>
                  <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--color-text)]">
                    Brokerage Info
                  </h2>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)] mb-2">
                      Brokerage Name
                    </label>
                    <input
                      type="text"
                      value={form.brokerage_name || ""}
                      onChange={(e) => setForm((f) => ({ ...f, brokerage_name: e.target.value }))}
                      placeholder="Skyline Realty Group"
                      className="w-full px-4 py-2.5 rounded-lg border border-[var(--color-input-border)] bg-[var(--color-input-bg)] text-[var(--color-text)] focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316] transition-all text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)] mb-2">
                      Agent Name
                    </label>
                    <input
                      type="text"
                      value={form.agent_name || ""}
                      onChange={(e) => setForm((f) => ({ ...f, agent_name: e.target.value }))}
                      placeholder="Capt. Jordan Sterling"
                      className="w-full px-4 py-2.5 rounded-lg border border-[var(--color-input-border)] bg-[var(--color-input-bg)] text-[var(--color-text)] focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316] transition-all text-sm"
                    />
                  </div>
                </div>
              </div>

              {/* Brand Colors */}
              <div className="bg-[var(--color-surface)] rounded-2xl border border-[var(--color-card-border)] p-6">
                <div className="flex items-center gap-2 mb-4">
                  <span className="w-8 h-8 rounded-full bg-[var(--color-background)] flex items-center justify-center text-sm">🎨</span>
                  <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--color-text)]">
                    Brand Colors
                  </h2>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)] mb-2">
                      Primary Main Navy
                    </label>
                    <ColorPicker
                      label=""
                      value={form.primary_color || "#0F1B2D"}
                      onChange={(color) => setForm((f) => ({ ...f, primary_color: color }))}
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)] mb-2">
                      Afterburner Accent
                    </label>
                    <ColorPicker
                      label=""
                      value={form.secondary_color || "#FF6B2C"}
                      onChange={(color) => setForm((f) => ({ ...f, secondary_color: color }))}
                    />
                  </div>
                </div>
              </div>

              {/* Typography */}
              <div className="bg-[var(--color-surface)] rounded-2xl border border-[var(--color-card-border)] p-6">
                <div className="flex items-center gap-2 mb-4">
                  <span className="w-8 h-8 rounded-full bg-[var(--color-background)] flex items-center justify-center text-sm font-bold text-[var(--color-text-secondary)]">Ty</span>
                  <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--color-text)]">
                    Typography
                  </h2>
                </div>
                <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  System Font Family
                </label>
                <Select
                  label=""
                  options={FONT_OPTIONS}
                  value={form.font_primary || ""}
                  onChange={(e) => setForm((f) => ({ ...f, font_primary: e.target.value }))}
                />
              </div>

              {/* Logo */}
              <div className="bg-[var(--color-surface)] rounded-2xl border border-[var(--color-card-border)] p-6">
                <div className="flex items-center gap-2 mb-4">
                  <span className="w-8 h-8 rounded-full bg-[var(--color-background)] flex items-center justify-center text-sm">📐</span>
                  <h2 className="text-sm font-bold uppercase tracking-wider text-[var(--color-text)]">
                    Logo
                  </h2>
                </div>
                {form.logo_url || logoPreview ? (
                  <div className="flex items-center gap-4 mb-4">
                    <img
                      src={logoPreview || form.logo_url || ""}
                      alt="Brand logo"
                      className="w-16 h-16 object-contain rounded-xl border border-[var(--color-card-border)]"
                    />
                    <div className="flex-1">
                      <label className="block text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-secondary)] mb-2">
                        Logo URL / Source
                      </label>
                      <input
                        type="text"
                        value={form.logo_url || ""}
                        readOnly
                        className="w-full px-4 py-2.5 rounded-lg border border-[var(--color-input-border)] bg-[var(--color-background)] text-sm text-[var(--color-text-secondary)] truncate"
                      />
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        className="px-3 py-1.5 rounded-full border border-[var(--color-border)] text-xs font-medium text-[var(--color-text-secondary)] hover:border-[var(--color-text-secondary)] transition-colors"
                      >
                        Replace Asset
                      </button>
                      <button
                        onClick={() => { setForm((f) => ({ ...f, logo_url: null })); setLogoPreview(null); }}
                        className="px-3 py-1.5 rounded-full border border-red-200 text-xs font-medium text-red-500 hover:border-red-300 transition-colors"
                      >
                        Remove
                      </button>
                    </div>
                    {uploading && <span className="text-xs text-slate-400">Uploading...</span>}
                  </div>
                ) : (
                  <div
                    className={`relative flex flex-col items-center justify-center gap-2 p-8 rounded-xl border-2 border-dashed transition-colors cursor-pointer ${
                      dragOver
                        ? "border-[#F97316] bg-[#F97316]/5"
                        : "border-[var(--color-border)] hover:border-[var(--color-text-secondary)]"
                    }`}
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={(e) => {
                      e.preventDefault();
                      setDragOver(false);
                      const file = e.dataTransfer.files[0];
                      if (file) handleLogoUpload(file);
                    }}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <svg className="w-8 h-8 text-[var(--color-text-secondary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                    </svg>
                    <p className="text-sm text-[var(--color-text-secondary)]">
                      {uploading ? "Uploading..." : "Drag & drop your logo, or click to browse"}
                    </p>
                    <p className="text-[10px] text-[var(--color-text-secondary)]">PNG, JPG, WebP, or SVG</p>
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/svg+xml"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleLogoUpload(file);
                  }}
                />
              </div>
            </div>

            {/* Right: Live HUD Preview */}
            <div className="lg:col-span-2">
              <div className="sticky top-24">
                <p className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)] font-semibold mb-3">
                  Live HUD Preview
                </p>
                <div className="bg-[var(--color-surface)] rounded-2xl border border-[var(--color-card-border)] overflow-hidden shadow-sm">
                  {/* Property Image */}
                  <div className="aspect-[4/3] bg-gradient-to-br from-slate-200 to-slate-100 flex items-center justify-center relative">
                    <svg className="w-12 h-12 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                    </svg>
                    {(logoPreview || form.logo_url) && (
                      <img
                        src={logoPreview || form.logo_url || ""}
                        alt="Logo"
                        className="absolute top-3 left-3 w-8 h-8 object-contain rounded"
                      />
                    )}
                    <span
                      className="absolute top-3 right-3 px-2 py-0.5 rounded text-[10px] font-bold text-white"
                      style={{ backgroundColor: form.secondary_color || "#FF6B2C" }}
                    >
                      $1,350,000
                    </span>
                  </div>

                  {/* Card Content */}
                  <div className="p-4">
                    <h3
                      className="text-lg font-bold text-[var(--color-text)]"
                      style={{ fontFamily: form.font_primary || "var(--font-heading)" }}
                    >
                      The Stratos Villa
                    </h3>
                    <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">742 Aurelia Way, Los Angeles</p>
                    <div className="flex items-center justify-between mt-2">
                      <span
                        className="text-[10px] uppercase tracking-wider font-bold"
                        style={{ color: form.secondary_color || "#FF6B2C" }}
                      >
                        Supersonic
                      </span>
                    </div>

                    <div className="flex items-center gap-4 mt-3 text-xs text-[var(--color-text-secondary)]">
                      <span><strong className="text-[var(--color-text)]">5</strong> 🛏</span>
                      <span><strong className="text-[var(--color-text)]">4.5</strong> 🛁</span>
                      <span><strong className="text-[var(--color-text)]">5,400</strong> sqft</span>
                    </div>

                    <p className="text-xs text-[var(--color-text-secondary)] mt-3 leading-relaxed">
                      Experience uncompromised altitude with this architectural marvel. Engineered for elite living with seamless glass transitions...
                    </p>

                    <div className="flex items-center gap-2 mt-4 pt-3 border-t border-[var(--color-card-border)]">
                      <div className="w-7 h-7 rounded-full bg-[var(--color-border)]" />
                      <div>
                        <p className="text-[10px] text-[var(--color-text-secondary)] uppercase tracking-wider">Listed By</p>
                        <p className="text-xs font-medium text-[var(--color-text)]">
                          {form.agent_name || "Agent Name"}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Save Button */}
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="w-full mt-6 py-3 rounded-full bg-[#F97316] hover:bg-[#ea580c] text-white font-semibold text-sm transition-colors flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg shadow-orange-200"
                >
                  {saving ? (
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      Save Brand Kit
                    </>
                  )}
                </button>
                {saved && (
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-center text-xs text-green-600 mt-2 font-medium"
                  >
                    Saved successfully
                  </motion.p>
                )}
                <p className="text-center text-[10px] text-[var(--color-text-secondary)] uppercase tracking-wider mt-3">
                  Flight Check: All Systems Nominal
                </p>
              </div>
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
