"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import apiClient from "@/lib/api-client";
import type { InviteInfoResponse } from "@/lib/types";

type InviteStatus =
  | { state: "loading" }
  | { state: "ready"; info: InviteInfoResponse }
  | { state: "missing" }
  | { state: "invalid" }
  | { state: "expired" }
  | { state: "error"; message: string };

export default function AcceptInvitePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)]">
          <div className="w-8 h-8 border-2 border-[var(--color-cta)] border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <AcceptInviteForm />
    </Suspense>
  );
}

function AcceptInviteForm() {
  const { acceptInvite } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<InviteStatus>({ state: "loading" });
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    document.title = "Accept Invitation | ListingJet";
  }, []);

  useEffect(() => {
    if (!token) {
      setStatus({ state: "missing" });
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const info = await apiClient.getInviteInfo(token);
        if (!cancelled) {
          setStatus({ state: "ready", info });
          // Prefill name if the inviter provided one. InviteInfoResponse
          // doesn't currently carry the invitee's name, so this stays blank
          // until the invitee types it.
        }
      } catch (err) {
        if (cancelled) return;
        const status = (err as { status?: number } | null)?.status;
        if (status === 404) {
          setStatus({ state: "invalid" });
        } else if (status === 410) {
          setStatus({ state: "expired" });
        } else {
          setStatus({
            state: "error",
            message: err instanceof Error ? err.message : "Failed to load invitation",
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;

    if (password.length < 8) {
      setSubmitError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setSubmitError("Passwords don't match.");
      return;
    }

    setSubmitError(null);
    setSubmitting(true);
    try {
      await acceptInvite(token, password, name.trim() || undefined);
      router.push("/dashboard");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to accept invitation";
      setSubmitError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)] px-4 py-10">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <svg
            className="w-7 h-7 text-[var(--color-cta)]"
            viewBox="0 0 24 24"
            fill="currentColor"
          >
            <path d="M3.5 18.5L9.5 12.5L13 16L22 6L20.5 4.5L13 12L9.5 8.5L2 16L3.5 18.5Z" />
          </svg>
          <span
            className="text-xl font-bold text-[var(--color-text)]"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            ListingJet
          </span>
        </div>

        <div className="rounded-2xl border border-[var(--color-card-border)] bg-[var(--color-surface)] p-8 shadow-xl">
          {status.state === "loading" && (
            <div className="py-10 flex flex-col items-center">
              <div className="w-6 h-6 border-2 border-[var(--color-cta)] border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-sm text-[var(--color-text-secondary)]">
                Loading your invitation…
              </p>
            </div>
          )}

          {status.state === "missing" && (
            <InviteError
              title="Invitation link missing"
              body="This link doesn't include an invitation token. Double-check the URL in your invite email."
            />
          )}

          {status.state === "invalid" && (
            <InviteError
              title="Invitation not found"
              body="This invitation is no longer valid. It may have already been accepted, or the link may have been revoked. Ask your admin to send a fresh invite."
            />
          )}

          {status.state === "expired" && (
            <InviteError
              title="Invitation expired"
              body="This invitation has expired. Invitations are valid for 72 hours — ask your admin to send a fresh one."
            />
          )}

          {status.state === "error" && (
            <InviteError
              title="Something went wrong"
              body={`We couldn't load your invitation. ${status.message}`}
            />
          )}

          {status.state === "ready" && (
            <>
              <h1
                className="text-2xl font-bold text-[var(--color-text)] mb-1"
                style={{ fontFamily: "var(--font-heading)" }}
              >
                You&apos;re invited
              </h1>
              <p className="text-sm text-[var(--color-text-secondary)] mb-6">
                {status.info.inviter_name ? (
                  <>
                    <span className="font-semibold text-[var(--color-text)]">
                      {status.info.inviter_name}
                    </span>{" "}
                    invited you to join{" "}
                  </>
                ) : (
                  "You've been invited to join "
                )}
                <span className="font-semibold text-[var(--color-text)]">
                  {status.info.tenant_name}
                </span>{" "}
                on ListingJet. Set a password below to accept.
              </p>

              <div className="mb-5 p-3 rounded-lg bg-[var(--color-bg)] border border-[var(--color-card-border)] text-xs text-[var(--color-text-secondary)]">
                Invitation for{" "}
                <span className="font-semibold text-[var(--color-text)]">
                  {status.info.email}
                </span>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label
                    htmlFor="invite-name"
                    className="block text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-1.5"
                  >
                    Your name (optional)
                  </label>
                  <input
                    id="invite-name"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-[var(--color-card-border)] bg-[var(--color-bg)] text-[var(--color-text)] text-sm focus:outline-none focus:border-[#F97316] transition-colors"
                    placeholder="Jane Doe"
                    autoComplete="name"
                  />
                </div>

                <div>
                  <label
                    htmlFor="invite-password"
                    className="block text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-1.5"
                  >
                    Create password *
                  </label>
                  <input
                    id="invite-password"
                    type="password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-[var(--color-card-border)] bg-[var(--color-bg)] text-[var(--color-text)] text-sm focus:outline-none focus:border-[#F97316] transition-colors"
                    placeholder="At least 8 characters"
                    autoComplete="new-password"
                  />
                </div>

                <div>
                  <label
                    htmlFor="invite-confirm"
                    className="block text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-1.5"
                  >
                    Confirm password *
                  </label>
                  <input
                    id="invite-confirm"
                    type="password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-[var(--color-card-border)] bg-[var(--color-bg)] text-[var(--color-text)] text-sm focus:outline-none focus:border-[#F97316] transition-colors"
                    placeholder="Type it again"
                    autoComplete="new-password"
                  />
                </div>

                {submitError && (
                  <div className="rounded-lg bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-900/40 px-3 py-2 text-sm text-red-700 dark:text-red-300">
                    {submitError}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full px-5 py-2.5 rounded-lg text-sm font-semibold text-white transition-all disabled:opacity-50"
                  style={{
                    fontFamily: "var(--font-heading)",
                    background: "linear-gradient(135deg, #F97316, #FB923C)",
                  }}
                >
                  {submitting ? "Accepting…" : "Accept invitation"}
                </button>
              </form>
            </>
          )}
        </div>

        <p className="text-center text-xs text-[var(--color-text-secondary)] mt-6">
          Already have an account?{" "}
          <Link href="/login" className="text-[var(--color-cta)] font-semibold">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

function InviteError({ title, body }: { title: string; body: string }) {
  return (
    <div className="py-4">
      <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center mx-auto mb-4">
        <svg
          className="w-6 h-6 text-red-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.268 16.5c-.77.833.192 2.5 1.732 2.5z"
          />
        </svg>
      </div>
      <h2
        className="text-lg font-bold text-[var(--color-text)] text-center mb-2"
        style={{ fontFamily: "var(--font-heading)" }}
      >
        {title}
      </h2>
      <p className="text-sm text-[var(--color-text-secondary)] text-center">
        {body}
      </p>
      <div className="mt-6 text-center">
        <Link
          href="/login"
          className="text-sm font-semibold text-[var(--color-cta)]"
        >
          Back to sign in
        </Link>
      </div>
    </div>
  );
}
