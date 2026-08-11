const fs = require('fs');
const path = 'c:/Users/power/Desktop/SCHOOL RAG/frontend/src/app/chat/page.tsx';
const content = `"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import ChatSidebar from "@/components/public/ChatSidebar";
import ChatMessage, { MessageData } from "@/components/public/ChatMessage";
import SuggestedPills from "@/components/SuggestedPills";
import { ApiError, fetchSuggestedQuestions, streamChat } from "@/lib/api";
import { usePersona } from "@/context/PersonaContext";

const WELCOME_CONTENT = `Hello! I am AJU Intelligent, your dedicated academic companion at Arthur Jarvis University.

I can help you with:
• Admissions requirements and processes
• Academic programmes and courses
• University policies and regulations
• Student services and support
• Faculty and departmental information

How can I assist you today?`;

export default function ChatPage() {
  const { persona, switchToPublic, switchToStudent, switchToStaff } = usePersona();
  const [messages, setMessages] = useState<MessageData[]>([
    { id: 0, role: "assistant", content: WELCOME_CONTENT },
  ]);
  const [input, setInput] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [conversations, setConversations] = useState<Array<{ id: string; title: string }>>([]);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const nextIdRef = useRef(1);

  useEffect(() => {
    let cancelled = false;
    fetchSuggestedQuestions(5)
      .then((q) => { if (!cancelled) setSuggestedQuestions(q); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const startNewConversation = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsGenerating(false);
    setConversationId(null);
    setMessages([{ id: nextIdRef.current++, role: "assistant", content: WELCOME_CONTENT }]);
  }, []);

  const handleSend = useCallback(
    async (text: string) => {
      const query = (text ?? "").trim();
      if (!query || isGenerating) return;

      const userMessage: MessageData = { id: nextIdRef.current++, role: "user", content: query };
      const assistantMessage: MessageData = { id: nextIdRef.current++, role: "assistant", content: "" };
      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setInput("");
      setIsGenerating(true);

      const controller = new AbortController();
      abortRef.current = controller;
      const citations: Array<{ source_title: string; similarity_score?: number; chunk_id?: number }> = [];

      try {
        await streamChat(
          { query, persona, conversation_id: conversationId },
          {
            onCitation: (citation) => {
              citations.push({ source_title: citation.source_title, similarity_score: citation.similarity_score, chunk_id: citation.chunk_id });
              setMessages((prev) => prev.map((m) => m.id === assistantMessage.id ? { ...m, citations: [...citations] } : m));
            },
            onToken: (text) => {
              setMessages((prev) => prev.map((m) => m.id === assistantMessage.id ? { ...m, content: m.content + text } : m));
            },
            onDone: (done) => {
              setConversationId(done.conversation_id);
              setMessages((prev) => prev.map((m) => m.id === assistantMessage.id ? { ...m, content: done.answer, confidence: done.confidence_score ?? null, isStreaming: false } : m));
              setIsGenerating(false);
              abortRef.current = null;
              const title = query.slice(0, 40) + (query.length > 40 ? "..." : "");
              setConversations((prev) => {
                const exists = prev.find((c) => c.id === done.conversation_id);
                if (exists) return prev;
                return [{ id: done.conversation_id, title }, ...prev].slice(0, 20);
              });
            },
            onError: (message) => {
              setMessages((prev) => prev.map((m) => m.id === assistantMessage.id ? { ...m, content: message, isError: true, isStreaming: false } : m));
              setIsGenerating(false);
              abortRef.current = null;
            },
          },
          controller.signal
        );
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") return;
        const msg = err instanceof ApiError ? err.message : "The response was interrupted. Please try again.";
        setMessages((prev) => prev.map((m) => m.id === assistantMessage.id ? { ...m, content: msg, isError: true, isStreaming: false } : m));
        setIsGenerating(false);
        abortRef.current = null;
      }
    },
    [isGenerating, conversationId, persona]
  );

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-slate-950">
      <ChatSidebar
        conversations={conversations}
        activeConversationId={conversationId}
        onNewChat={startNewConversation}
        persona={persona}
        onPersonaChange={(p) => {
          if (p === "student") switchToStudent();
          else if (p === "staff") switchToStaff();
          else switchToPublic();
          startNewConversation();
        }}
      />

      <main className="flex-1 flex flex-col min-w-0">
        <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-slate-900 dark:text-white">AJU Intelligent</h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {persona === "public" ? "Public Assistant" : persona === "student" ? "Student Portal" : "Staff Portal"}
                {conversationId && ` • ${conversationId.slice(0, 8)}...`}
              </p>
            </div>
            <button
              onClick={startNewConversation}
              className="text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992h4.992m12.97 0h4.992v4.992M2.985 9.348h4.992m12.97 0v4.992h-4.992" />
              </svg>
              Clear Conversation
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-center justify-center mb-6">
              <span className="px-3 py-1 rounded-full bg-slate-200 dark:bg-slate-800 text-xs font-medium text-slate-500 dark:text-slate-400">Today</span>
            </div>
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 px-4 sm:px-6 py-4">
          <div className="max-w-3xl mx-auto">
            {!isGenerating && messages.length > 1 && suggestedQuestions.length > 0 && messages[messages.length - 1]?.role === "assistant" && (
              <SuggestedPills questions={suggestedQuestions} onSelectQuestion={(q) => handleSend(q)} />
            )}
            <form onSubmit={(e) => { e.preventDefault(); handleSend(input); }} className="flex items-center gap-2 mt-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a follow-up question..."
                disabled={isGenerating}
                className="flex-1 px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
              />
              <button
                type="submit"
                disabled={!input.trim() || isGenerating}
                aria-label="Send message"
                className="h-11 w-11 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white flex items-center justify-center hover:from-blue-700 hover:to-indigo-700 disabled:from-slate-300 disabled:to-slate-300 transition-all cursor-pointer shadow-md disabled:cursor-not-allowed"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 transform rotate-90">
                  <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.977a.75.75 0 0 0 .53.504l9.167 2.12a.75.75 0 0 0 0-1.458l-9.167-2.12a.75.75 0 0 0-.53-.504l-2.43-7.975Z" />
                  <path d="M2.204 11.23a.75.75 0 0 0-.083.75c.083.277.292.5.568.568l9.167 2.12a.75.75 0 0 0 0-1.458L2.68 11.09a.75.75 0 0 0-.476.14Z" />
                </svg>
              </button>
            </form>
            <p className="text-[11px] text-slate-400 dark:text-slate-500 text-center mt-3">AI can make mistakes. Verify important information.</p>
          </div>
        </div>
      </main>
    </div>
  );
}
`;
fs.writeFileSync(path, content, 'utf8');
console.log('Chat page written');
