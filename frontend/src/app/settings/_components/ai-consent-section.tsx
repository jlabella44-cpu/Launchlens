"use client";

import { useState } from "react";
import apiClient from "@/lib/api-client";
import { useAuth } from "@/contexts/auth-context";
import { useToast } from "@/components/ui/toast";

export default function AiConsentSection() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [consent, setConsent] = useState<boolean>(Boolean(user?.ai_consent_at));
  const [saving, setSaving] = useState(false);

  async function handleToggle(next: boolean) {
    setSaving(true);
    const prev = consent;
    setConsent(next);
    try {
      await apiClient.updateAiConsent(next);
      toast(
        next
          ? "AI processing enabled for your account."
          : "AI processing disabled. New listings will skip AI features.",
        "success"
      );
    } catch (err) {
      setConsent(prev);
      toast(err instanceof Error ? err.message : "Failed to update consent", "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="bg-white rounded-xl p-6 shadow-sm">
      <h2
        className="text-lg font-semibold text-[var(--color-text)] mb-1"
        style={{ fontFamily: "var(--font-heading)" }}
      >
        AI Processing Consent
      </h2>
      <p className="text-sm text-[var(--color-text-secondary)] mb-4">
        Controls whether your listing photos and data are processed by third-party AI
        services (vision analysis, video generation, content writing). Turning this off
        disables AI features on new listings — existing listings are not affected.
      </p>

      <label className="flex items-start gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={consent}
          disabled={saving}
          onChange={(e) => handleToggle(e.target.checked)}
          className="mt-0.5 w-4 h-4 rounded border-slate-300 text-[#F97316] focus:ring-[#F97316]/30"
        />
        <span className="text-sm text-[var(--color-text)]">
          {consent ? "Enabled" : "Disabled"}
          {user?.ai_consent_at && (
            <span className="block text-xs text-[var(--color-text-secondary)] mt-1">
              Granted {new Date(user.ai_consent_at).toLocaleDateString()}
              {user.ai_consent_version ? ` (policy v${user.ai_consent_version})` : ""}
            </span>
          )}
        </span>
      </label>
    </section>
  );
}
