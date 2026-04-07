"use client";

import { useEffect, useState, useCallback } from "react";
import apiClient from "@/lib/api-client";
import { useToast } from "@/components/ui/toast";

type Platform = "instagram" | "facebook" | "tiktok";

interface SocialAccount {
  id: string;
  platform: string;
  platform_username: string;
}

const PLATFORM_CONFIG: Record<Platform, { label: string; color: string; icon: React.ReactNode }> = {
  instagram: {
    label: "Instagram",
    color: "text-pink-500",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
        <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
      </svg>
    ),
  },
  facebook: {
    label: "Facebook",
    color: "text-blue-500",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
      </svg>
    ),
  },
  tiktok: {
    label: "TikTok",
    color: "text-slate-800 dark:text-slate-200",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
        <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 00-.79-.05 6.34 6.34 0 00-6.34 6.34 6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.33-6.34V9.15a8.15 8.15 0 004.78 1.52V7.22a4.85 4.85 0 01-1.01-.53z" />
      </svg>
    ),
  },
};

const PLATFORMS: Platform[] = ["instagram", "facebook", "tiktok"];

export default function ConnectedAccountsSection() {
  const { toast } = useToast();
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [inputs, setInputs] = useState<Record<Platform, string>>({
    instagram: "",
    facebook: "",
    tiktok: "",
  });
  const [saving, setSaving] = useState<Record<Platform, boolean>>({
    instagram: false,
    facebook: false,
    tiktok: false,
  });
  const [removing, setRemoving] = useState<Record<Platform, boolean>>({
    instagram: false,
    facebook: false,
    tiktok: false,
  });

  const load = useCallback(async () => {
    try {
      const data = await apiClient.getSocialAccounts();
      setAccounts(data as SocialAccount[]);
      // Pre-fill inputs from connected accounts
      const prefill: Record<Platform, string> = { instagram: "", facebook: "", tiktok: "" };
      (data as SocialAccount[]).forEach((a) => {
        const p = a.platform as Platform;
        if (PLATFORMS.includes(p)) prefill[p] = a.platform_username;
      });
      setInputs(prefill);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  function getAccount(platform: Platform): SocialAccount | undefined {
    return accounts.find((a) => a.platform === platform);
  }

  async function handleSave(platform: Platform) {
    const username = inputs[platform].trim();
    if (!username) {
      toast("Enter a username first", "error");
      return;
    }
    setSaving((s) => ({ ...s, [platform]: true }));
    try {
      // Remove existing if any, then create fresh
      const existing = getAccount(platform);
      if (existing) {
        await apiClient.deleteSocialAccount(existing.id);
      }
      await apiClient.saveSocialAccount(platform, username);
      toast(`${PLATFORM_CONFIG[platform].label} account saved`, "success");
      await load();
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Save failed", "error");
    } finally {
      setSaving((s) => ({ ...s, [platform]: false }));
    }
  }

  async function handleRemove(platform: Platform) {
    const existing = getAccount(platform);
    if (!existing) return;
    setRemoving((r) => ({ ...r, [platform]: true }));
    try {
      await apiClient.deleteSocialAccount(existing.id);
      toast(`${PLATFORM_CONFIG[platform].label} account removed`, "success");
      setInputs((i) => ({ ...i, [platform]: "" }));
      await load();
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Remove failed", "error");
    } finally {
      setRemoving((r) => ({ ...r, [platform]: false }));
    }
  }

  return (
    <section className="bg-white rounded-xl p-6 shadow-sm">
      <div className="mb-5">
        <h2
          className="text-lg font-semibold text-[var(--color-text)] mb-1"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Connected Social Accounts
        </h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Link your social handles so they appear on post previews.
        </p>
        <p className="text-xs text-slate-400 mt-1 italic">
          Auto-posting coming soon — for now, copy captions and download clips from the Social Post Hub.
        </p>
      </div>

      <div className="space-y-4">
        {PLATFORMS.map((platform) => {
          const config = PLATFORM_CONFIG[platform];
          const connected = getAccount(platform);
          return (
            <div
              key={platform}
              className="flex items-center gap-3 p-3 rounded-xl border border-slate-100 dark:border-white/10 bg-slate-50 dark:bg-white/5"
            >
              {/* Icon */}
              <span className={`shrink-0 ${config.color}`}>{config.icon}</span>

              {/* Label */}
              <span className="w-24 shrink-0 text-sm font-medium text-[var(--color-text)]">
                {config.label}
              </span>

              {/* Username input */}
              <div className="flex-1 relative">
                <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 text-sm">@</span>
                <input
                  type="text"
                  value={inputs[platform]}
                  onChange={(e) => setInputs((i) => ({ ...i, [platform]: e.target.value }))}
                  placeholder="username"
                  className="w-full pl-6 pr-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-white/20 bg-white dark:bg-[rgba(15,27,45,0.6)] text-[var(--color-text)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/30 placeholder:text-slate-300"
                  onKeyDown={(e) => { if (e.key === "Enter") handleSave(platform); }}
                />
              </div>

              {/* Status badge */}
              {connected ? (
                <span className="shrink-0 text-[10px] font-semibold text-green-600 bg-green-50 dark:bg-green-950/40 dark:text-green-400 px-2 py-0.5 rounded-full">
                  Connected
                </span>
              ) : (
                <span className="shrink-0 text-[10px] font-semibold text-slate-400 bg-slate-100 dark:bg-white/10 px-2 py-0.5 rounded-full">
                  Not set
                </span>
              )}

              {/* Save button */}
              <button
                onClick={() => handleSave(platform)}
                disabled={saving[platform]}
                className="shrink-0 px-3 py-1.5 rounded-lg bg-[#F97316] hover:bg-[#ea580c] text-white text-xs font-semibold transition-colors disabled:opacity-50"
              >
                {saving[platform] ? "Saving..." : "Save"}
              </button>

              {/* Remove button */}
              {connected && (
                <button
                  onClick={() => handleRemove(platform)}
                  disabled={removing[platform]}
                  className="shrink-0 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-white/20 text-xs font-semibold text-slate-500 hover:text-red-500 hover:border-red-200 transition-colors disabled:opacity-50"
                >
                  {removing[platform] ? "..." : "Remove"}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
