"use client";

import { useCallback, useRef, useState } from "react";
import { apiClient } from "@/lib/api-client";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  toolsUsed?: string[];
  feedback?: "up" | "down" | null;
}

interface SSEEvent {
  type: "session" | "text" | "tool_call" | "done" | "error";
  text?: string;
  tool?: string;
  session_id?: string;
  tools_used?: string[];
}

export function useHelpChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      return sessionStorage.getItem("help_chat_session_id");
    }
    return null;
  });
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming) return;

      const userMsg: ChatMessage = { role: "user", content: text.trim() };
      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);

      let currentSessionId = sessionId;
      let assistantText = "";

      try {
        const response = await apiClient.sendHelpMessage(text.trim(), currentSessionId || undefined);

        if (!response.ok) {
          const err = await response.json().catch(() => ({ detail: "Something went wrong" }));
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: err.detail || "Sorry, something went wrong. Please try again." },
          ]);
          setIsStreaming(false);
          return;
        }

        const reader = response.body?.getReader();
        if (!reader) {
          setIsStreaming(false);
          return;
        }

        const decoder = new TextDecoder();
        let buffer = "";
        let toolsUsed: string[] = [];

        // Add placeholder assistant message
        setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const jsonStr = line.slice(6).trim();
            if (!jsonStr) continue;

            try {
              const event: SSEEvent = JSON.parse(jsonStr);

              switch (event.type) {
                case "session":
                  if (event.session_id) {
                    currentSessionId = event.session_id;
                    setSessionId(event.session_id);
                    sessionStorage.setItem("help_chat_session_id", event.session_id);
                  }
                  break;

                case "text":
                  assistantText += event.text || "";
                  setMessages((prev) => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      role: "assistant",
                      content: assistantText,
                    };
                    return updated;
                  });
                  break;

                case "tool_call":
                  if (event.tool) toolsUsed.push(event.tool);
                  break;

                case "done":
                  if (event.tools_used) toolsUsed = event.tools_used;
                  setMessages((prev) => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      role: "assistant",
                      content: assistantText,
                      toolsUsed: toolsUsed.length > 0 ? toolsUsed : undefined,
                    };
                    return updated;
                  });
                  break;

                case "error":
                  assistantText = event.text || "Something went wrong.";
                  setMessages((prev) => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      role: "assistant",
                      content: assistantText,
                    };
                    return updated;
                  });
                  break;
              }
            } catch {
              // Skip malformed SSE lines
            }
          }
        }
      } catch {
        setMessages((prev) => {
          // If the last message is an empty assistant placeholder, replace it
          if (prev.length > 0 && prev[prev.length - 1].role === "assistant" && !prev[prev.length - 1].content) {
            const updated = [...prev];
            updated[updated.length - 1] = {
              role: "assistant",
              content: "Unable to connect. Please check your connection and try again.",
            };
            return updated;
          }
          return [...prev, { role: "assistant", content: "Unable to connect. Please check your connection and try again." }];
        });
      } finally {
        setIsStreaming(false);
      }
    },
    [isStreaming, sessionId]
  );

  const clearChat = useCallback(() => {
    if (sessionId) {
      apiClient.clearHelpHistory(sessionId).catch(() => {});
    }
    setMessages([]);
    const newSessionId = crypto.randomUUID();
    setSessionId(newSessionId);
    sessionStorage.setItem("help_chat_session_id", newSessionId);
  }, [sessionId]);

  const sendFeedback = useCallback(
    async (messageIndex: number, rating: "up" | "down") => {
      if (!sessionId) return;
      setMessages((prev) => {
        const updated = [...prev];
        if (updated[messageIndex]) {
          updated[messageIndex] = { ...updated[messageIndex], feedback: rating };
        }
        return updated;
      });
      await apiClient.sendHelpFeedback(sessionId, messageIndex, rating).catch(() => {});
    },
    [sessionId]
  );

  return {
    messages,
    isStreaming,
    sessionId,
    sendMessage,
    clearChat,
    sendFeedback,
  };
}
