"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import ChatMessage, { MessageData } from "./ChatMessage";
import SuggestedPills from "../SuggestedPills";
import { usePersona } from "@/context/PersonaContext";
import {
  streamChat,
  fetchSuggestedQuestions,
  ApiError,
  SseCitation,
  Persona,
} from "@/lib/api";
import { Send, Square, RefreshCw, Sparkles } from "lucide-react";

interface ChatWindowProps {
  conversationId?: string | null;
  onConversationIdChange?: (id: string | null) => void;
}

const WELCOME_MESSAGE: MessageData = {
  id: "welcome-0",
  role: "assistant",
  content:
    "Welcome to Arthur Jarvis University Smart Portal. How can I assist you today with admissions, academic programmes, policies, or campus services?",
};

export default function ChatWindow({
  conversationId,
  onConversationIdChange,
}: ChatWindowProps) {
  const { persona } = usePersona();
  const [messages, setMessages] = useState<MessageData[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const initialQueryHandled = useRef(false);

  // Load suggested questions from backend on mount
  useEffect(() => {
    let cancelled = false;
    fetchSuggestedQuestions(5)
      .then((questions) => {
        if (!cancelled) setSuggestedQuestions(questions);
      })
      .catch((err) => {
        console.error("Failed to load suggested questions:", err);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Auto-scroll to newest message when messages state updates
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isGenerating]);

  // Reset messages when conversationId is reset to null by parent
  useEffect(() => {
    if (conversationId === null && messages.length > 1) {
      abortRef.current?.abort();
      abortRef.current = null;
      setIsGenerating(false);
      setMessages([WELCOME_MESSAGE]);
    }
  }, [conversationId]);

  const updateAssistantMessage = useCallback(
    (messageId: string, updater: (prev: MessageData) => MessageData) => {
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? updater(m) : m))
      );
    },
    []
  );

  const handleSend = useCallback(
    async (text: string) => {
      const queryText = (text ?? "").trim();
      if (!queryText || isGenerating) return;

      const userMsgId = `user-${Date.now()}`;
      const assistantMsgId = `assistant-${Date.now()}`;

      const userMsg: MessageData = {
        id: userMsgId,
        role: "user",
        content: queryText,
      };

      const assistantMsg: MessageData = {
        id: assistantMsgId,
        role: "assistant",
        content: "",
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setInput("");
      setIsGenerating(true);

      const controller = new AbortController();
      abortRef.current = controller;
      const citations: SseCitation[] = [];
      let assembledText = "";

      try {
        await streamChat(
          {
            query: queryText,
            persona: persona as Persona,
            conversation_id: conversationId ?? null,
          },
          {
            onCitation: (citation) => {
              if (citation && citation.source_title) {
                citations.push(citation);
                updateAssistantMessage(assistantMsgId, (prev) => ({
                  ...prev,
                  citations: [...citations],
                }));
              }
            },
            onToken: (token) => {
              assembledText += token;
              updateAssistantMessage(assistantMsgId, (prev) => ({
                ...prev,
                content: assembledText,
                isStreaming: true,
              }));
            },
            onDone: (done) => {
              if (done.conversation_id && onConversationIdChange) {
                onConversationIdChange(done.conversation_id);
              }
              const finalAnswer =
                done.answer && done.answer.trim()
                  ? done.answer
                  : assembledText || "No information was returned for your query.";

              updateAssistantMessage(assistantMsgId, (prev) => ({
                ...prev,
                content: finalAnswer,
                citations: citations.length > 0 ? citations : undefined,
                confidence: done.confidence_score ?? null,
                isStreaming: false,
              }));
            },
            onError: (errorMessage) => {
              updateAssistantMessage(assistantMsgId, (prev) => ({
                ...prev,
                content:
                  prev.content ||
                  `Error: ${errorMessage || "Failed to retrieve response."}`,
                isError: true,
                isStreaming: false,
              }));
            },
          },
          controller
        );
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          updateAssistantMessage(assistantMsgId, (prev) => ({
            ...prev,
            content: prev.content ? `${prev.content} [Response stopped]` : "Response stopped by user.",
            isStreaming: false,
          }));
          return;
        }
        const message =
          err instanceof ApiError
            ? `Server error: ${err.message}`
            : "Could not connect to the backend server. Please make sure the service is running.";

        updateAssistantMessage(assistantMsgId, (prev) => ({
          ...prev,
          content: prev.content || message,
          isError: true,
          isStreaming: false,
        }));
      } finally {
        abortRef.current = null;
        setIsGenerating(false);
        // Refresh suggested questions in background
        fetchSuggestedQuestions(5)
          .then((qs) => setSuggestedQuestions(qs))
          .catch(() => {});
      }
    },
    [isGenerating, persona, conversationId, onConversationIdChange, updateAssistantMessage]
  );

  // Check URL query parameters for initial query (e.g. /chat?q=...)
  useEffect(() => {
    if (initialQueryHandled.current) return;
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const q = params.get("q");
      if (q && q.trim()) {
        initialQueryHandled.current = true;
        handleSend(q);
        window.history.replaceState({}, "", window.location.pathname);
      }
    }
  }, [handleSend]);

  const handleStop = () => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  };

  const handleNewChat = () => {
    handleStop();
    if (onConversationIdChange) {
      onConversationIdChange(null);
    }
    setMessages([WELCOME_MESSAGE]);
  };

  return (
    <div className="flex flex-col h-full bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      {/* Top Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-bold text-sm shadow-md">
            <Sparkles size={20} />
          </div>
          <div>
            <h1 className="text-base font-semibold text-slate-900 dark:text-white leading-tight">
              AJU Intelligent Assistant
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5 mt-0.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse"></span>
              Active Mode: <span className="font-medium text-slate-700 dark:text-slate-300 capitalize">{persona}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {conversationId && (
            <span className="hidden sm:inline-block text-xs px-2.5 py-1 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-500 font-mono">
              ID: {conversationId.slice(0, 8)}...
            </span>
          )}
          <button
            onClick={handleNewChat}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors"
            title="Start new conversation"
          >
            <RefreshCw size={14} />
            <span>New Chat</span>
          </button>
        </div>
      </header>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4 max-w-4xl w-full mx-auto">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Bottom Input Area */}
      <div className="border-t border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md p-4">
        <div className="max-w-4xl mx-auto space-y-3">
          {/* Suggested Pills when conversation is fresh */}
          {!isGenerating && messages.length <= 2 && (
            <SuggestedPills
              questions={suggestedQuestions}
              onSelectQuestion={handleSend}
            />
          )}

          {/* Form input */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend(input);
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Ask AJU Intelligent (${persona} mode)...`}
              disabled={isGenerating}
              className="flex-1 px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 transition-all placeholder:text-slate-400"
            />

            {isGenerating ? (
              <button
                type="button"
                onClick={handleStop}
                className="px-4 py-3 rounded-xl bg-red-600 hover:bg-red-700 text-white font-medium text-sm flex items-center gap-1.5 transition-colors shadow-md"
                title="Stop response generation"
              >
                <Square size={16} className="fill-current" />
                <span className="hidden sm:inline">Stop</span>
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim()}
                className="px-5 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium text-sm flex items-center gap-1.5 transition-all shadow-md"
              >
                <Send size={16} />
                <span className="hidden sm:inline">Send</span>
              </button>
            )}
          </form>

          <p className="text-[11px] text-center text-slate-400 dark:text-slate-500">
            AJU Intelligent RAG Portal • Responses derived from institutional documents
          </p>
        </div>
      </div>
    </div>
  );
}
