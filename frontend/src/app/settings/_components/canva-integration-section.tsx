"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import apiClient from "@/lib/api-client";
import { Button } from "@/components/ui/button";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

export default function CanvaIntegrationSection() {
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [canvaUserId, setCanvaUserId] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const status = await apiClient.getCanvaStatus();
      setConnected(status.connected);
      setCanvaUserId(status.canva_user_id);
    } catch (err) {
      console.error("Failed to fetch Canva status:", err);
      setError("Unable to load Canva connection status.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  function handleConnect() {
    const token = apiClient.getToken();
    if (!token) {
      setError("You must be logged in to connect Canva.");
      return;
    }
    window.location.href = `${API_URL}/auth/canva?token=${encodeURIComponent(token)}`;
  }

  async function handleDisconnect() {
    setDisconnecting(true);
    setError(null);
    try {
      await apiClient.disconnectCanva();
      setConnected(false);
      setCanvaUserId(null);
    } catch (err) {
      console.error("Failed to disconnect Canva:", err);
      setError("Failed to disconnect Canva. Please try again.");
    } finally {
      setDisconnecting(false);
    }
  }

  return (
    <section className="bg-[var(--color-surface)] rounded-2xl border border-[var(--color-card-border)] p-6 backdrop-blur-xl">
      {/* Section Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-8 h-8 rounded-full bg-[var(--color-background)] flex items-center justify-center">
          {/* Canva icon (simplified "C" mark) */}
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" fill="#7D2AE8" />
            <text
              x="12"
              y="16"
              textAnchor="middle"
              fill="white"
              fontSize="12"
              fontWeight="bold"
              fontFamily="system-ui, sans-serif"
            >
              C
            </text>
          </svg>
        </div>
        <h2
          className="text-sm font-bold uppercase tracking-wider text-[var(--color-text)]"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Canva Integration
        </h2>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center gap-3">
          <div className="h-4 w-32 rounded bg-[var(--color-background)] animate-pulse" />
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-[var(--color-text-secondary)]">
            {connected
              ? "Your Canva account is connected. ListingJet can export branded templates directly to your Canva workspace."
              : "Connect your Canva account to export branded listing templates directly into your Canva workspace."}
          </p>

          {error && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-sm text-red-400"
            >
              {error}
            </motion.p>
          )}

          {connected ? (
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <span className="text-sm text-[var(--color-text)]">
                  Connected
                  {canvaUserId && (
                    <span className="text-[var(--color-text-secondary)] ml-1.5">
                      ({canvaUserId})
                    </span>
                  )}
                </span>
              </div>
              <Button
                variant="danger"
                onClick={handleDisconnect}
                loading={disconnecting}
                className="text-xs px-4 py-2 min-h-[36px]"
              >
                Disconnect
              </Button>
            </div>
          ) : (
            <Button onClick={handleConnect} variant="secondary">
              <svg className="w-4 h-4 mr-1" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" fill="#7D2AE8" />
                <text
                  x="12"
                  y="16"
                  textAnchor="middle"
                  fill="white"
                  fontSize="12"
                  fontWeight="bold"
                  fontFamily="system-ui, sans-serif"
                >
                  C
                </text>
              </svg>
              Connect Canva
            </Button>
          )}
        </div>
      )}
    </section>
  );
}
