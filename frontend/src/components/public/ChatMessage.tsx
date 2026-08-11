"use client";

import React from "react";
import { User, Bot } from "lucide-react";
import CitationCard from "./CitationCard";

export interface MessageData {
  id: number;
  role: "user" | "assistant";
  content: string;
  citations?: Array<{ source_title: string; similarity_score?: number; chunk_id?: number }>;
  confidence?: number | null;
  isError?: boolean;
  isStreaming?: boolean;
}

interface ChatMessageProps {
  message: MessageData;
  showAvatar?: boolean;
}

export default function ChatMessage({ message, showAvatar = true }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"} mb-6`}>
      {/* Avatar */}
      {showAvatar && (
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${isUser ? "bg-blue-600 text-white" : "bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700"}`}>
          {isUser ? (
            <User size={16} />
          ) : (
            <svg viewBox="0 0 40 40" className="w-5 h-5" fill="none">
              <rect x="2" y="2" width="36" height="36" rx="8" fill="#0a1628" />
              <path d="M12 14L20 18L12 22V14Z" fill="#d4af37" />
              <path d="M20 18L28 14V22L20 18Z" fill="#d4af37" opacity="0.7" />
            </svg>
          )}
        </div>
      )}

      {/* Message bubble */}
      <div className={`flex-1 max-w-[85%] ${isUser ? "flex justify-end" : ""}`}>
        <div
          className={`
            px-4 py-3 rounded-2xl text-sm leading-relaxed
            ${isUser
              ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-tr-sm"
              : "bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 rounded-tl-sm"
            }
            ${message.isError ? "bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900 text-red-800 dark:text-red-300" : ""}
          `}
        >
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
          {message.isStreaming && (
            <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse align-middle" />
          )}
        </div>

        {/* Citations */}
        {message.citations && message.citations.length > 0 && !isUser && (
          <div className="mt-3 space-y-2">
            <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Sources</h4>
            {message.citations.map((citation, idx) => (
              <CitationCard key={idx} {...citation} />
            ))}
          </div>
        )}

        {/* Confidence */}
        {message.confidence !== undefined && message.confidence !== null && !isUser && (
          <div className="mt-2 flex items-center gap-2">
            <span className="text-xs text-slate-400 dark:text-slate-500">Confidence:</span>
            <div className="flex-1 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full max-w-[100px]">
              <div
                className="h-full bg-blue-500 rounded-full"
                style={{ width: `${Math.min(message.confidence * 100, 100)}%` }}
              />
            </div>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {(message.confidence * 100).toFixed(0)}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
