"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
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
  const [form, setForm] = useState<BrandKitUpsertRequest>({
    brokerage_name: "",
    agent_name: "",
    primary_color: "#0F1B2D",
    secondary_color: "#FF6B2C",
    font_primary: "",
    logo_url: null,
  });

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
        <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-8">
          <div className="h-96 rounded-xl bg-white/50 animate-pulse" />
        </main>
      </>
    );
  }

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <h1
            className="text-3xl font-bold text-[var(--color-text)] mb-2"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Brand Kit
          </h1>
          <p className="text-[var(--color-text-secondary)] mb-8">
            Configure your branding for flyers, watermarks, and exports.
          </p>

          <div className="space-y-8">
            {/* Brokerage Info */}
            <GlassCard>
              <h2 className="text-lg font-semibold text-[var(--color-text)] mb-4">
                Brokerage Info
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  label="Brokerage Name"
                  placeholder="Acme Realty"
                  value={form.brokerage_name || ""}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, brokerage_name: e.target.value }))
                  }
                />
                <Input
                  label="Agent Name"
                  placeholder="Jane Smith"
                  value={form.agent_name || ""}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, agent_name: e.target.value }))
                  }
                />
              </div>
            </GlassCard>

            {/* Brand Colors */}
            <GlassCard>
              <h2 className="text-lg font-semibold text-[var(--color-text)] mb-4">
                Brand Colors
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <ColorPicker
                  label="Primary Color"
                  value={form.primary_color || "#0F1B2D"}
                  onChange={(color) =>
                    setForm((f) => ({ ...f, primary_color: color }))
                  }
                />
                <ColorPicker
                  label="Secondary Color"
                  value={form.secondary_color || "#FF6B2C"}
                  onChange={(color) =>
                    setForm((f) => ({ ...f, secondary_color: color }))
                  }
                />
              </div>
            </GlassCard>

            {/* Typography */}
            <GlassCard>
              <h2 className="text-lg font-semibold text-[var(--color-text)] mb-4">
                Typography
              </h2>
              <Select
                label="Primary Font"
                options={FONT_OPTIONS}
                value={form.font_primary || ""}
                onChange={(e) =>
                  setForm((f) => ({ ...f, font_primary: e.target.value }))
                }
              />
            </GlassCard>

            {/* Logo */}
            <GlassCard>
              <h2 className="text-lg font-semibold text-[var(--color-text)] mb-4">
                Logo
              </h2>
              {form.logo_url ? (
                <div className="flex items-center gap-4 mb-4">
                  <img
                    src={form.logo_url}
                    alt="Brand logo"
                    className="w-16 h-16 object-contain rounded-lg border border-white/20"
                  />
                  <Button
                    variant="secondary"
                    onClick={() => setForm((f) => ({ ...f, logo_url: null }))}
                  >
                    Remove
                  </Button>
                </div>
              ) : (
                <p className="text-sm text-[var(--color-text-secondary)] mb-4">
                  No logo uploaded yet. Upload a PNG logo for your flyers and watermarks.
                </p>
              )}
              <Input
                label="Logo URL"
                placeholder="https://..."
                value={form.logo_url || ""}
                onChange={(e) =>
                  setForm((f) => ({ ...f, logo_url: e.target.value || null }))
                }
              />
            </GlassCard>

            {/* Live Preview */}
            <GlassCard>
              <h2 className="text-lg font-semibold text-[var(--color-text)] mb-4">
                Preview
              </h2>
              <div
                className="p-6 rounded-lg border border-white/20"
                style={{ backgroundColor: form.primary_color || "#0F1B2D" }}
              >
                <p
                  className="text-white text-xl font-bold"
                  style={{ fontFamily: form.font_primary || "inherit" }}
                >
                  {form.brokerage_name || "Your Brokerage"}
                </p>
                <p className="text-white/80 text-sm mt-1">
                  {form.agent_name || "Agent Name"}
                </p>
                <div
                  className="mt-3 inline-block px-4 py-1.5 rounded-full text-white text-sm font-medium"
                  style={{ backgroundColor: form.secondary_color || "#FF6B2C" }}
                >
                  Schedule Showing
                </div>
              </div>
            </GlassCard>

            {/* Save */}
            <div className="flex items-center gap-4">
              <Button onClick={handleSave} disabled={saving}>
                {saving ? "Saving..." : "Save Brand Kit"}
              </Button>
              {saved && (
                <motion.span
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="text-green-600 text-sm font-medium"
                >
                  Saved successfully
                </motion.span>
              )}
            </div>
          </div>
        </motion.div>
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
