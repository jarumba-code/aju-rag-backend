"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import SuggestedPills from "./SuggestedPills";
import { ApiError, fetchSuggestedQuestions, Persona, streamChat } from "../lib/api";

interface CitationData {
  source_title: string;
  similarity_score?: number;
}

interface UiMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  citations?: CitationData[];
  confidence?: number | null;
  latencyMs?: number | null;
  isError?: boolean;
}

const WELCOME_MESSAGE: UiMessage = {
  id: 0,
  role: "assistant",
  content:
    "Welcome! I am your AJU assistant. Feel free to ask me anything about university regulations, courses, or student health services.",
};

const PERSONAS: { value: Persona; label: string }[] = [
  { value: "public", label: "Public" },
  { value: "student", label: "Student" },
  { value: "staff", label: "Staff" },
];

let nextMessageId = 1;

export const ChatWidget: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<UiMessage[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [persona, setPersona] = useState<Persona>("public");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load suggested questions on mount (served by the backend).
  useEffect(() => {
    let cancelled = false;
    fetchSuggestedQuestions(5)
      .then((questions) => {
        if (!cancelled) setSuggestedQuestions(questions);
      })
      .catch((err) => console.error("Failed to load suggested questions:", err));
    return () => {
      cancelled = true;
    };
  }, []);

  // Auto-scroll to the newest message.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const updateAssistantMessage = useCallback(
    (messageId: number, updater: (prev: UiMessage) => UiMessage) => {
      setMessages((prev) => prev.map((m) => (m.id === messageId ? updater(m) : m)));
    },
    []
  );

  const handlePersonaChange = (next: Persona) => {
    if (next === persona) return;
    setPersona(next);
    // A different persona is a different access boundary — start a fresh thread.
    setConversationId(null);
  };

  const startNewConversation = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsGenerating(false);
    setConversationId(null);
    setMessages([WELCOME_MESSAGE]);
  };
const handleSend = async (text: string) => {
    const query = (text ?? "").trim();
    if (!query || isGenerating) return;

    // 1. Immediately render the user's message + an empty assistant bubble.
    const userMessage: UiMessage = { id: nextMessageId++, role: "user", content: query };
    const assistantMessage: UiMessage = { id: nextMessageId++, role: "assistant", content: "" };
    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setInput("");
    setIsGenerating(true);

    const controller = new AbortController();
    abortRef.current = controller;
    const citations: CitationData[] = [];
    let assembled = "";

    try {
      await streamChat(
        { query, persona, conversation_id: conversationId },
        {
          onCitation: (citation) => {
            if (citation && citation.source_title) {
              citations.push({
                source_title: citation.source_title,
                similarity_score: citation.similarity_score,
              });
            }
          },
          onMetadata: (meta) => {
            const latencyMs =
              typeof meta.retrieval_latency_ms === "number" ? meta.retrieval_latency_ms : 0;
            updateAssistantMessage(assistantMessage.id, (prev) => ({
              ...prev,
              latencyMs: latencyMs || null,
            }));
          },
          onToken: (token) => {
            assembled += token;
            // Progressive render — each token appends to the visible bubble.
            updateAssistantMessage(assistantMessage.id, (prev) => ({
              ...prev,
              content: assembled,
            }));
          },
          onDone: (done) => {
            if (done.conversation_id) {
              setConversationId(done.conversation_id);
            }
            const finalContent =
              done.answer && done.answer.trim()
                ? done.answer
                : assembled || "I could not find an answer to that question.";
            updateAssistantMessage(assistantMessage.id, (prev) => ({
              ...prev,
              content: finalContent,
              citations: citations.length > 0 ? citations : undefined,
              confidence: done.confidence_score ?? null,
            }));
          },
          onError: (message) => {
            updateAssistantMessage(assistantMessage.id, (prev) => ({
              ...prev,
              content:
                prev.content ||
                `I'm sorry, I couldn't complete that request. ${message}`,
              isError: !prev.content,
            }));
          },
        },
        controller
      );
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return;
      }
      const friendly =
        err instanceof ApiError
          ? `I'm sorry, the server reported an error: ${err.message}`
          : "I'm sorry, I couldn't reach the assistant server. Please try again.";
      updateAssistantMessage(assistantMessage.id, (prev) => ({
        ...prev,
        content: prev.content || friendly,
        isError: !prev.content,
      }));
    } finally {
      abortRef.current = null;
      setIsGenerating(false);
      // Refresh suggestions so popularity reflects the new question.
      fetchSuggestedQuestions(5)
        .then(setSuggestedQuestions)
        .catch(() => {
          // best-effort refresh
        });
    }
  };

  const selectQuestion = (question: string) => {
    handleSend(question);
  };
return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end font-sans">
      {isOpen && (
        <div className="w-[380px] h-[550px] md:w-[420px] md:h-[600px] bg-slate-50/90 dark:bg-slate-900/95 backdrop-blur-xl rounded-3xl border border-slate-200/50 dark:border-slate-800/80 shadow-2xl flex flex-col overflow-hidden mb-4 transition-all duration-300 animate-in slide-in-from-bottom-5 fade-in">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-indigo-700 p-4 text-white flex items-center justify-between shadow-md">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-white/20 flex items-center justify-center font-bold text-lg shadow-inner">
                AJU
              </div>
              <div>
                <h3 className="font-semibold text-sm leading-tight">AJU Smart Portal</h3>
                <span className="text-[10px] text-blue-200 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block animate-pulse"></span>
                  RAG Assistant Online
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={startNewConversation}
                title="Start a new conversation"
                aria-label="Start a new conversation"
                className="w-8 h-8 rounded-full bg-black/10 hover:bg-black/25 flex items-center justify-center transition-colors cursor-pointer text-white font-bold text-lg outline-none"
              >
                +
              </button>
              <button
                onClick={() => setIsOpen(false)}
                aria-label="Close chat"
                className="w-8 h-8 rounded-full bg-black/10 hover:bg-black/25 flex items-center justify-center transition-colors cursor-pointer text-white font-semibold outline-none"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Conversation Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-slate-200 dark:scrollbar-thumb-slate-800">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex w-full ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl p-3 text-sm shadow-sm ${
                    msg.role === "user"
                      ? "bg-gradient-to-tr from-blue-600 to-indigo-600 text-white rounded-br-none"
                      : `bg-white dark:bg-slate-850 dark:text-slate-200 border border-slate-100 dark:border-slate-850/80 text-slate-800 rounded-bl-none ${
                          msg.isError
                            ? "border-rose-300 dark:border-rose-900 text-rose-700 dark:text-rose-300"
                            : ""
                        }`
                  }`}
                >
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.content || "…"}</p>

                  {msg.role === "assistant" && msg.citations && msg.citations.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-slate-200/60 dark:border-slate-700/60">
                      <div className="text-[10px] uppercase tracking-wide text-slate-400 mb-1">
                        Sources
                      </div>
                      {msg.citations.map((citation, index) => (
                        <div
                          key={index}
                          className="text-xs text-slate-500 dark:text-slate-400 flex justify-between gap-2"
                        >
                          <span className="truncate">📄 {citation.source_title}</span>
                          {typeof citation.similarity_score === "number" && (
                            <span className="shrink-0">
                              {Math.round(citation.similarity_score * 100)}%
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {msg.role === "assistant" &&
                    (typeof msg.confidence === "number" || typeof msg.latencyMs === "number") && (
                      <div className="mt-1 flex items-center gap-3 text-[10px] text-slate-400 dark:text-slate-500">
                        {typeof msg.confidence === "number" && (
                          <span>Confidence {Math.round(msg.confidence * 100)}%</span>
                        )}
                        {typeof msg.latencyMs === "number" && (
                          <span>Retrieval {Math.round(msg.latencyMs)} ms</span>
                        )}
                      </div>
                    )}
                </div>
              </div>
            ))}
            {isGenerating && (
              <div className="flex w-full justify-start animate-pulse">
                <div className="bg-white dark:bg-slate-850 border border-slate-100 dark:border-slate-850/80 rounded-2xl rounded-bl-none p-3 max-w-[80%] flex gap-1 items-center">
                  <span className="w-2 h-2 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce"></span>
                  <span className="w-2 h-2 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce [animation-delay:0.2s]"></span>
                  <span className="w-2 h-2 rounded-full bg-slate-400 dark:bg-slate-500 animate-bounce [animation-delay:0.4s]"></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
{/* Footer: suggested questions, persona selector, input */}
          <div className="p-4 border-t border-slate-200/50 dark:border-slate-800/80 bg-white/50 dark:bg-slate-900/50 flex flex-col gap-2">
            {!isGenerating && messages.length <= 2 && (
              <SuggestedPills questions={suggestedQuestions} onSelectQuestion={selectQuestion} />
            )}

            <div className="flex items-center gap-1">
              <span className="text-[10px] uppercase tracking-wider text-slate-400 dark:text-slate-500 mr-1">
                Access
              </span>
              {PERSONAS.map((p) => (
                <button
                  key={p.value}
                  type="button"
                  onClick={() => handlePersonaChange(p.value)}
                  className={`px-2.5 py-1 rounded-full text-[11px] font-semibold transition-all cursor-pointer outline-none ${
                    persona === p.value
                      ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-sm"
                      : "bg-white/60 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700 hover:border-blue-400"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend(input);
              }}
              className="flex items-center gap-2 mt-1"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask your portal assistant..."
                disabled={isGenerating}
                className="flex-1 px-4 py-2.5 rounded-full border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200 text-sm outline-none focus:border-blue-500 dark:focus:border-indigo-500 focus:ring-1 focus:ring-blue-500/20 transition-all shadow-inner"
              />
              <button
                type="submit"
                disabled={!input.trim() || isGenerating}
                aria-label="Send message"
                className="h-10 w-10 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-slate-300 disabled:to-slate-300 dark:disabled:from-slate-800 dark:disabled:to-slate-800 text-white flex items-center justify-center transition-all cursor-pointer shadow-lg hover:scale-105 active:scale-95 disabled:scale-100 disabled:cursor-not-allowed outline-none"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className="w-4.5 h-4.5 transform rotate-90"
                >
                  <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.977a.75.75 0 0 0 .53.504l9.167 2.12a.75.75 0 0 0 0-1.458l-9.167-2.12a.75.75 0 0 0-.53-.504l-2.43-7.975Z" />
                  <path d="M2.204 11.23a.75.75 0 0 0-.083.75c.083.277.292.5.568.568l9.167 2.12a.75.75 0 0 0 0-1.458L2.68 11.09a.75.75 0 0 0-.476.14Z" />
                  <path d="M21.522 11.23a.75.75 0 0 1 .083.75c-.083.277-.292.5-.568.568l-9.167 2.12a.75.75 0 0 1 0-1.458l9.167-2.12a.75.75 0 0 1 .485.14Z" />
                </svg>
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Floating Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-label={isOpen ? "Close chat" : "Open chat"}
        className="w-14 h-14 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 text-white flex items-center justify-center shadow-xl hover:shadow-2xl hover:scale-110 active:scale-95 transition-all duration-300 cursor-pointer outline-none border border-white/10"
      >
        {isOpen ? (
          <span className="text-xl">✕</span>
        ) : (
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
            className="w-7 h-7"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a.75.75 0 0 1-1.074-.83l1.246-3.835C4.333 15.016 3 13.62 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z"
            />
          </svg>
        )}
      </button>
    </div>
  );
};

export default ChatWidget;