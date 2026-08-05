"use client";

import React, { useState, useEffect, useRef } from "react";
import SuggestedPills from "./SuggestedPills";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export const ChatWidget: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Welcome! I am your AJU assistant. Feel free to ask me anything about university regulations, courses, or student health services.",
    },
  ]);
  const [input, setInput] = useState("");
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  // Fetch suggested questions on mount
  useEffect(() => {
    const fetchSuggestions = async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/suggested`
        );
        const data = await response.json();
        if (data && data.questions) {
          setSuggestedQuestions(data.questions);
        }
      } catch (err) {
        console.error("Failed to load suggested questions:", err);
      }
    };
    fetchSuggestions();
  }, []);

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (text: string) => {
    if (!text.trim() || isGenerating) return;

    // Add user message
    const userMessage: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsGenerating(true);

    // Placeholder assistant message for streaming
    const assistantMessage: Message = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, assistantMessage]);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/chat`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text }),
        }
      );

      if (!response.body) {
        throw new Error("No response stream found");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let finished = false;
      let accumulatedResponse = "";

      while (!finished) {
        const { value, done } = await reader.read();
        finished = done;
        if (value) {
          const chunk = decoder.decode(value, { stream: !done });
          accumulatedResponse += chunk;

          // Update the last assistant message
          setMessages((prev) => {
            const updated = [...prev];
            if (updated.length > 0) {
              updated[updated.length - 1] = {
                role: "assistant",
                content: accumulatedResponse,
              };
            }
            return updated;
          });
        }
      }
    } catch (error) {
      console.error("Streaming error:", error);
      setMessages((prev) => {
        const updated = [...prev];
        if (updated.length > 0) {
          updated[updated.length - 1] = {
            role: "assistant",
            content: "Sorry, I encountered an issue connecting to the RAG server.",
          };
        }
        return updated;
      });
    } finally {
      setIsGenerating(false);
      // Refresh suggested questions to reflect new popularity
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/suggested`
        );
        const data = await res.json();
        if (data && data.questions) {
          setSuggestedQuestions(data.questions);
        }
      } catch (e) {
        // Silently catch refresh errors
      }
    }
  };

  const selectQuestion = (question: string) => {
    handleSend(question);
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end font-sans">
      {/* Expanded Chat Window */}
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
            <button
              onClick={() => setIsOpen(false)}
              className="w-8 h-8 rounded-full bg-black/10 hover:bg-black/25 flex items-center justify-center transition-colors cursor-pointer text-white font-semibold outline-none"
            >
              ✕
            </button>
          </div>

          {/* Conversation Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-slate-200 dark:scrollbar-thumb-slate-800">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`flex w-full ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                } animate-in fade-in-50 duration-200`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl p-3 text-sm shadow-sm ${
                    msg.role === "user"
                      ? "bg-gradient-to-tr from-blue-600 to-indigo-600 text-white rounded-br-none"
                      : "bg-white dark:bg-slate-850 dark:text-slate-200 border border-slate-100 dark:border-slate-850/80 text-slate-800 rounded-bl-none"
                  }`}
                >
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
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

          {/* User Input & Actions */}
          <div className="p-4 border-t border-slate-200/50 dark:border-slate-800/80 bg-white/50 dark:bg-slate-900/50 flex flex-col gap-2">
            {/* Suggested Question Pills (only when message list contains only initial welcome or is not generating) */}
            {!isGenerating && messages.length <= 2 && (
              <SuggestedPills
                questions={suggestedQuestions}
                onSelectQuestion={selectQuestion}
              />
            )}

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
                className="flex-1 px-4 py-2.5 rounded-full border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200 text-sm outline-none focus:border-blue-500 dark:focus:border-indigo-500 focus:ring-1 focus:ring-blue-500/20 transition-all shadow-inner"
              />
              <button
                type="submit"
                disabled={!input.trim() || isGenerating}
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
