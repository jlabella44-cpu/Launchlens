"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { useToast } from "@/components/ui/toast";
import apiClient from "@/lib/api-client";
import type { MLSConnection, CreateMLSConnectionRequest } from "@/lib/types";

const EMPTY_FORM: CreateMLSConnectionRequest = {
  name: "",
  mls_board: "",
  reso_api_url: "",
  oauth_token_url: "",
  client_id: "",
  client_secret: "",
  bearer_token: null,
  config: {},
};

function MLSConnectionsPage() {
  const { toast } = useToast();

  const [connections, setConnections] = useState<MLSConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CreateMLSConnectionRequest>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const fetchConnections = useCallback(async () => {
    try {
      const data = await apiClient.getMLSConnections();
      setConnections(data);
    } catch {
      toast("Failed to load MLS connections", "error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    document.title = "MLS Connections | ListingJet";
    fetchConnections();
  }, [fetchConnections]);

  async function handleSave() {
    if (!form.name || !form.mls_board || !form.reso_api_url || !form.oauth_token_url || !form.client_id || !form.client_secret) {
      toast("Please fill in all required fields", "error");
      return;
    }
    setSaving(true);
    try {
      await apiClient.createMLSConnection(form);
      toast("MLS connection added", "success");
      setForm(EMPTY_FORM);
      setShowForm(false);
      fetchConnections();
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Failed to save", "error");
    } finally {
      setSaving(false);
    }
  }

  async function handleTest(id: string) {
    setTesting(id);
    try {
      const result = await apiClient.testMLSConnection(id);
      if (result.status === "ok") {
        toast("Connection test passed", "success");
      } else {
        toast(`Connection test failed: ${result.error}`, "error");
      }
      fetchConnections();
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Test failed", "error");
    } finally {
      setTesting(null);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this MLS connection?")) return;
    setDeleting(id);
    try {
      await apiClient.deleteMLSConnection(id);
      toast("Connection deleted", "success");
      fetchConnections();
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Failed to delete", "error");
    } finally {
      setDeleting(null);
    }
  }

  async function handleToggleActive(conn: MLSConnection) {
    try {
      await apiClient.updateMLSConnection(conn.id, { is_active: !conn.is_active });
      fetchConnections();
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Failed to update", "error");
    }
  }

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-8">
        {/* Breadcrumbs */}
        <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-slate-400 mb-6">
          <Link href="/settings" className="hover:text-[#F97316] transition-colors">Settings</Link>
          <span>/</span>
          <span className="text-slate-600">MLS Connections</span>
        </div>

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400 font-semibold mb-1">
              RESO Web API
            </p>
            <h1
              className="text-3xl font-bold text-[var(--color-text)]"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              MLS Connections
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Configure your MLS board credentials for one-click publish via RESO Web API
            </p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-5 py-2.5 rounded-full bg-[#F97316] hover:bg-[#ea6c12] text-white text-sm font-semibold transition-colors inline-flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Connection
          </button>
        </div>

        {/* Add Connection Form */}
        {showForm && (
          <div className="bg-white rounded-2xl border border-slate-100 p-6 mb-6">
            <h3 className="font-semibold text-[var(--color-text)] mb-4" style={{ fontFamily: "var(--font-heading)" }}>
              New MLS Connection
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs uppercase tracking-wider text-slate-400 font-semibold mb-1">Display Name *</label>
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. My CRMLS Connection"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316]"
                />
              </div>
              <div>
                <label className="block text-xs uppercase tracking-wider text-slate-400 font-semibold mb-1">MLS Board *</label>
                <input
                  value={form.mls_board}
                  onChange={(e) => setForm({ ...form, mls_board: e.target.value })}
                  placeholder="e.g. CRMLS, Bright MLS, Stellar MLS"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316]"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-xs uppercase tracking-wider text-slate-400 font-semibold mb-1">RESO API URL *</label>
                <input
                  value={form.reso_api_url}
                  onChange={(e) => setForm({ ...form, reso_api_url: e.target.value })}
                  placeholder="https://api.mlsboard.com/reso/odata"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316]"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-xs uppercase tracking-wider text-slate-400 font-semibold mb-1">OAuth2 Token URL *</label>
                <input
                  value={form.oauth_token_url}
                  onChange={(e) => setForm({ ...form, oauth_token_url: e.target.value })}
                  placeholder="https://api.mlsboard.com/oauth2/token"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316]"
                />
              </div>
              <div>
                <label className="block text-xs uppercase tracking-wider text-slate-400 font-semibold mb-1">Client ID *</label>
                <input
                  value={form.client_id}
                  onChange={(e) => setForm({ ...form, client_id: e.target.value })}
                  placeholder="Your OAuth2 client ID"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316]"
                />
              </div>
              <div>
                <label className="block text-xs uppercase tracking-wider text-slate-400 font-semibold mb-1">Client Secret *</label>
                <input
                  type="password"
                  value={form.client_secret}
                  onChange={(e) => setForm({ ...form, client_secret: e.target.value })}
                  placeholder="Your OAuth2 client secret"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316]"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-xs uppercase tracking-wider text-slate-400 font-semibold mb-1">
                  Static Bearer Token <span className="text-slate-300">(optional — alternative to OAuth2)</span>
                </label>
                <input
                  type="password"
                  value={form.bearer_token || ""}
                  onChange={(e) => setForm({ ...form, bearer_token: e.target.value || null })}
                  placeholder="Static API key if your MLS uses bearer tokens instead of OAuth2"
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#F97316]/30 focus:border-[#F97316]"
                />
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-6 py-2.5 rounded-full bg-[#0B1120] hover:bg-[#1a2744] text-white text-sm font-semibold transition-colors disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save Connection"}
              </button>
              <button
                onClick={() => { setShowForm(false); setForm(EMPTY_FORM); }}
                className="px-6 py-2.5 rounded-full border border-slate-200 text-sm text-slate-600 hover:border-slate-300 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Connections List */}
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="w-8 h-8 border-2 border-[#F97316] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : connections.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-100 p-12 text-center">
            <svg className="w-12 h-12 text-slate-200 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <h3 className="text-lg font-semibold text-slate-600 mb-1">No MLS connections yet</h3>
            <p className="text-sm text-slate-400 mb-4">
              Add your MLS board credentials to enable one-click publish via RESO Web API
            </p>
            <button
              onClick={() => setShowForm(true)}
              className="px-5 py-2.5 rounded-full bg-[#F97316] hover:bg-[#ea6c12] text-white text-sm font-semibold transition-colors"
            >
              Add Your First Connection
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {connections.map((conn) => (
              <div
                key={conn.id}
                className="bg-white rounded-2xl border border-slate-100 p-6 flex items-start justify-between"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-semibold text-[var(--color-text)]">{conn.name}</h3>
                    <span className="text-[9px] uppercase tracking-wider font-bold bg-slate-100 text-slate-500 px-2 py-0.5 rounded">
                      {conn.mls_board}
                    </span>
                    {conn.is_active ? (
                      <span className="text-[9px] uppercase tracking-wider font-bold bg-green-100 text-green-600 px-2 py-0.5 rounded">
                        Active
                      </span>
                    ) : (
                      <span className="text-[9px] uppercase tracking-wider font-bold bg-slate-100 text-slate-400 px-2 py-0.5 rounded">
                        Inactive
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 mb-1">{conn.reso_api_url}</p>
                  <p className="text-xs text-slate-400">
                    Client: {conn.client_id.slice(0, 8)}...
                    {conn.last_tested_at && (
                      <>
                        {" "}· Last tested: {new Date(conn.last_tested_at).toLocaleDateString()}{" "}
                        <span className={conn.last_test_status === "ok" ? "text-green-500" : "text-red-500"}>
                          ({conn.last_test_status})
                        </span>
                      </>
                    )}
                  </p>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() => handleTest(conn.id)}
                    disabled={testing === conn.id}
                    className="px-4 py-2 rounded-full border border-slate-200 text-xs font-semibold text-slate-600 hover:border-slate-300 transition-colors disabled:opacity-50"
                  >
                    {testing === conn.id ? "Testing..." : "Test"}
                  </button>
                  <button
                    onClick={() => handleToggleActive(conn)}
                    className="px-4 py-2 rounded-full border border-slate-200 text-xs font-semibold text-slate-600 hover:border-slate-300 transition-colors"
                  >
                    {conn.is_active ? "Deactivate" : "Activate"}
                  </button>
                  <button
                    onClick={() => handleDelete(conn.id)}
                    disabled={deleting === conn.id}
                    className="px-4 py-2 rounded-full border border-red-200 text-xs font-semibold text-red-500 hover:border-red-300 hover:bg-red-50 transition-colors disabled:opacity-50"
                  >
                    {deleting === conn.id ? "..." : "Delete"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Info Footer */}
        <div className="mt-8 p-6 rounded-2xl bg-slate-50 border border-slate-100">
          <h4 className="font-semibold text-sm text-slate-600 mb-2">About RESO Web API Integration</h4>
          <p className="text-xs text-slate-400 leading-relaxed">
            ListingJet connects to your MLS board using the RESO Web API v2 standard. This enables
            direct property listing submission and photo upload without leaving the platform. Your
            credentials are encrypted at rest and only used to communicate with your MLS board's API.
          </p>
          <p className="text-xs text-slate-400 leading-relaxed mt-2">
            Contact your MLS board's technology department to obtain your RESO API credentials.
            Most boards require a vendor certification process before granting production access.
          </p>
        </div>
      </main>
    </>
  );
}

export default function MLSConnectionsPageWrapper() {
  return (
    <ProtectedRoute>
      <MLSConnectionsPage />
    </ProtectedRoute>
  );
}
