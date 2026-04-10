"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Nav } from "@/components/layout/nav";
import { ProtectedRoute } from "@/components/layout/protected-route";
import { useToast } from "@/components/ui/toast";
import apiClient from "@/lib/api-client";
import type { SupportTicket, SupportTicketDetail, SupportMessage } from "@/lib/types";

const CATEGORIES = [
  { value: "billing", label: "Billing" },
  { value: "technical", label: "Technical" },
  { value: "listing", label: "Listing" },
  { value: "account", label: "Account" },
  { value: "other", label: "Other" },
];

const PRIORITIES = [
  { value: "low", label: "Low" },
  { value: "normal", label: "Normal" },
  { value: "high", label: "High" },
  { value: "urgent", label: "Urgent" },
];

const STATUS_COLORS: Record<string, string> = {
  open: "bg-orange-100 text-orange-700",
  in_progress: "bg-blue-100 text-blue-700",
  resolved: "bg-green-100 text-green-700",
  closed: "bg-slate-100 text-slate-500",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${STATUS_COLORS[status] || STATUS_COLORS.open}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function SupportPage() {
  const { toast } = useToast();
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<SupportTicketDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [ticketsError, setTicketsError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);

  // Create form
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("other");
  const [priority, setPriority] = useState("normal");
  const [creating, setCreating] = useState(false);

  const fetchTickets = useCallback(async () => {
    setTicketsError(null);
    try {
      const res = await apiClient.getSupportTickets(statusFilter === "all" ? undefined : statusFilter);
      setTickets(res.items);
    } catch (err) {
      setTicketsError(err instanceof Error ? err.message : "Failed to load tickets");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    document.title = "Support | ListingJet";
    fetchTickets();
  }, [fetchTickets]);

  async function selectTicket(id: string) {
    setSelectedId(id);
    setDetailLoading(true);
    try {
      const d = await apiClient.getSupportTicket(id);
      setDetail(d);
    } catch {
      toast("Failed to load ticket", "error");
    } finally {
      setDetailLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!subject.trim() || !description.trim()) return;
    setCreating(true);
    try {
      const ticket = await apiClient.createSupportTicket({ subject, description, category, priority });
      setTickets((prev) => [ticket, ...prev]);
      setShowCreate(false);
      setSubject("");
      setDescription("");
      setCategory("other");
      setPriority("normal");
      selectTicket(ticket.id);
      toast("Ticket created", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to create ticket", "error");
    } finally {
      setCreating(false);
    }
  }

  async function handleReply() {
    if (!reply.trim() || !selectedId) return;
    setSending(true);
    try {
      const msg = await apiClient.addSupportMessage(selectedId, reply);
      setDetail((prev) => prev ? { ...prev, messages: [...prev.messages, msg] } : prev);
      setReply("");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to send reply", "error");
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <Nav />
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-[var(--color-text)]" style={{ fontFamily: "var(--font-heading)" }}>
              Support
            </h1>
            <p className="text-sm text-[var(--color-text-secondary)] mt-1">
              Get help from our team. Try the AI chat first — click the bubble in the bottom right.
            </p>
          </div>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="px-4 py-2 rounded-lg text-sm font-semibold text-white transition-all"
            style={{ background: "linear-gradient(135deg, #F97316, #FB923C)" }}
          >
            {showCreate ? "Cancel" : "New Ticket"}
          </button>
        </div>

        {/* Create form */}
        <AnimatePresence>
          {showCreate && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden mb-6">
              <form onSubmit={handleCreate} className="p-5 rounded-2xl border border-[var(--color-card-border)] bg-[var(--color-surface)] space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-1">Subject</label>
                  <input type="text" value={subject} onChange={(e) => setSubject(e.target.value)} required maxLength={255} placeholder="Brief description of your issue"
                    className="w-full px-3 py-2 rounded-lg border border-[var(--color-card-border)] bg-[var(--color-bg)] text-[var(--color-text)] text-sm focus:outline-none focus:border-[#F97316]" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-1">Category</label>
                    <select value={category} onChange={(e) => setCategory(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-[var(--color-card-border)] bg-[var(--color-bg)] text-[var(--color-text)] text-sm focus:outline-none focus:border-[#F97316]">
                      {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-1">Priority</label>
                    <select value={priority} onChange={(e) => setPriority(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-[var(--color-card-border)] bg-[var(--color-bg)] text-[var(--color-text)] text-sm focus:outline-none focus:border-[#F97316]">
                      {PRIORITIES.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider mb-1">Description</label>
                  <textarea value={description} onChange={(e) => setDescription(e.target.value)} required rows={4} maxLength={5000} placeholder="Describe your issue in detail..."
                    className="w-full px-3 py-2 rounded-lg border border-[var(--color-card-border)] bg-[var(--color-bg)] text-[var(--color-text)] text-sm focus:outline-none focus:border-[#F97316] resize-none" />
                </div>
                <button type="submit" disabled={creating}
                  className="px-5 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-50" style={{ background: "linear-gradient(135deg, #F97316, #FB923C)" }}>
                  {creating ? "Creating..." : "Create Ticket"}
                </button>
              </form>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Filter tabs */}
        <div className="flex gap-2 mb-4">
          {["all", "open", "resolved", "closed"].map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-colors ${statusFilter === s ? "bg-[#F97316] text-white" : "bg-[var(--color-surface)] text-[var(--color-text-secondary)] border border-[var(--color-card-border)]"}`}>
              {s === "all" ? "All" : s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
            </button>
          ))}
        </div>

        {/* Two-panel layout */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.5fr] gap-6">
          {/* Ticket list */}
          <div className="space-y-2">
            {loading ? (
              [1, 2, 3].map((i) => <div key={i} className="h-16 rounded-xl bg-[var(--color-surface)] animate-pulse border border-[var(--color-card-border)]" />)
            ) : ticketsError ? (
              <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-900/10 dark:border-red-900/40 p-4 text-center">
                <p className="text-sm text-red-700 dark:text-red-300 mb-3">
                  Couldn&apos;t load tickets. {ticketsError}
                </p>
                <button
                  onClick={() => { setLoading(true); fetchTickets(); }}
                  className="px-4 py-1.5 rounded-full bg-[#F97316] hover:bg-[#ea580c] text-white text-xs font-semibold transition-colors"
                >
                  Retry
                </button>
              </div>
            ) : tickets.length === 0 ? (
              <p className="text-sm text-[var(--color-text-secondary)] text-center py-8">No tickets yet. Try the AI chat first!</p>
            ) : (
              tickets.map((t) => (
                <div key={t.id} onClick={() => selectTicket(t.id)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all ${selectedId === t.id ? "border-[#F97316]/40 bg-orange-50/30 dark:bg-orange-900/10" : "border-[var(--color-card-border)] bg-[var(--color-surface)] hover:border-[var(--color-text-secondary)]/30"}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-[var(--color-text)] truncate">{t.subject}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <StatusBadge status={t.status} />
                        <span className="text-[10px] text-[var(--color-text-secondary)]">{t.category}</span>
                        {t.chat_session_id && <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">AI Escalated</span>}
                      </div>
                    </div>
                    <span className="text-[10px] text-[var(--color-text-secondary)] whitespace-nowrap">{timeAgo(t.updated_at)}</span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Ticket detail */}
          <div className="rounded-2xl border border-[var(--color-card-border)] bg-[var(--color-surface)] min-h-[400px]">
            {!selectedId ? (
              <div className="flex items-center justify-center h-full text-sm text-[var(--color-text-secondary)]">
                Select a ticket to view details
              </div>
            ) : detailLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="w-5 h-5 border-2 border-[#F97316] border-t-transparent rounded-full animate-spin" />
              </div>
            ) : detail ? (
              <div className="flex flex-col h-full">
                {/* Header */}
                <div className="p-4 border-b border-[var(--color-card-border)]">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-semibold text-[var(--color-text)]">{detail.subject}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <StatusBadge status={detail.status} />
                        <span className="text-xs text-[var(--color-text-secondary)]">{detail.category} / {detail.priority}</span>
                      </div>
                    </div>
                    {detail.resolution_note && (
                      <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg px-3 py-2 max-w-xs">
                        <p className="text-[10px] font-semibold text-green-700 dark:text-green-400 uppercase">Resolution</p>
                        <p className="text-xs text-green-800 dark:text-green-300">{detail.resolution_note}</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {detail.messages.map((msg) => (
                    <div key={msg.id} className={`flex ${msg.is_admin_reply ? "justify-start" : "justify-end"}`}>
                      <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                        msg.is_admin_reply
                          ? "bg-blue-50 dark:bg-blue-900/20 text-[var(--color-text)] rounded-bl-md"
                          : "bg-[var(--color-bg)] border border-[var(--color-card-border)] text-[var(--color-text)] rounded-br-md"
                      }`}>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[10px] font-semibold text-[var(--color-text-secondary)]">
                            {msg.is_admin_reply ? "ListingJet Support" : msg.user_name || "You"}
                          </span>
                          <span className="text-[10px] text-[var(--color-text-secondary)]">
                            {new Date(msg.created_at).toLocaleString()}
                          </span>
                        </div>
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                        {msg.chat_transcript && msg.chat_transcript.length > 0 && (
                          <details className="mt-2 pt-2 border-t border-[var(--color-card-border)]">
                            <summary className="text-[10px] text-blue-600 cursor-pointer font-semibold">AI Chat Context ({msg.chat_transcript.length} messages)</summary>
                            <div className="mt-2 space-y-1 max-h-40 overflow-y-auto">
                              {msg.chat_transcript.map((m, i) => (
                                <p key={i} className="text-[11px] text-[var(--color-text-secondary)]">
                                  <span className="font-semibold">{m.role === "user" ? "User" : "AI"}:</span> {m.content.slice(0, 200)}{m.content.length > 200 ? "..." : ""}
                                </p>
                              ))}
                            </div>
                          </details>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Reply */}
                {detail.status !== "closed" && (
                  <div className="p-4 border-t border-[var(--color-card-border)]">
                    <div className="flex gap-2">
                      <textarea value={reply} onChange={(e) => setReply(e.target.value)} rows={2} placeholder="Type your reply..."
                        className="flex-1 px-3 py-2 rounded-lg border border-[var(--color-card-border)] bg-[var(--color-bg)] text-[var(--color-text)] text-sm resize-none focus:outline-none focus:border-[#F97316]" />
                      <button onClick={handleReply} disabled={!reply.trim() || sending}
                        className="px-4 py-2 rounded-lg text-sm font-semibold text-white self-end disabled:opacity-50" style={{ background: "linear-gradient(135deg, #F97316, #FB923C)" }}>
                        {sending ? "..." : "Send"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      </main>
    </>
  );
}

export default function SupportPageWrapper() {
  return (
    <ProtectedRoute>
      <SupportPage />
    </ProtectedRoute>
  );
}
