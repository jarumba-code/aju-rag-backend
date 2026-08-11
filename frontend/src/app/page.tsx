"use client";

import React, { useState } from "react";
import ChatWidget from "../components/ChatWidget";
import { ApiError, ingestDocument } from "../lib/api";

export default function Home() {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [isConfidential, setIsConfidential] = useState(false);
  const [adminKey, setAdminKey] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: "success" | "error"; text: string } | null>(
    null
  );

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedTitle = title.trim();
    const trimmedContent = content.trim();
    const key = adminKey.trim();

    if (!trimmedTitle || !trimmedContent) {
      setStatusMsg({ type: "error", text: "Both a title and content are required." });
      return;
    }
    if (!key) {
      setStatusMsg({ type: "error", text: "An admin API key is required to ingest content." });
      return;
    }

    setIsUploading(true);
    setStatusMsg(null);

    try {
      await ingestDocument(
        {
          title: trimmedTitle,
          content: trimmedContent,
          is_confidential: isConfidential,
          department_id: null,
          category_id: null,
        },
        key
      );
      setStatusMsg({
        type: "success",
        text: `Document "${trimmedTitle}" ingested successfully! It is now searchable by the AI assistant.`,
      });
      setTitle("");
      setContent("");
      setAdminKey("");
      setIsConfidential(false);
    } catch (err) {
      console.error(err);
      setStatusMsg({
        type: "error",
        text:
          err instanceof ApiError
            ? err.message
            : "Network error occurred. Ensure the backend is running.",
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <main className="min-h-screen relative overflow-hidden bg-slate-50 dark:bg-slate-950 flex flex-col justify-between py-12 px-6">
      {/* Decorative gradient blur background */}
      <div className="absolute top-[-10%] left-[-20%] w-[600px] h-[600px] rounded-full bg-blue-400/20 dark:bg-blue-900/10 blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] rounded-full bg-indigo-500/20 dark:bg-indigo-900/10 blur-[100px] pointer-events-none"></div>

      <div className="max-w-4xl mx-auto w-full z-10 flex-1 flex flex-col justify-center">
        {/* Portal Branding */}
        <div className="text-center mb-12 animate-in fade-in slide-in-from-top-4 duration-500">
          <div className="inline-flex items-center gap-3 px-4 py-2 rounded-full bg-white/60 dark:bg-slate-900/60 border border-slate-200/50 dark:border-slate-800/80 backdrop-blur-md shadow-sm mb-4">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-600 dark:bg-indigo-400 animate-pulse"></span>
            <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 tracking-wide uppercase">
              Arthur Jarvis University Smart Portal
            </span>
          </div>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-700 dark:from-blue-400 dark:via-indigo-300 dark:to-violet-400 leading-tight">
            AJU Intelligent RAG Center
          </h1>
          <p className="mt-4 text-slate-600 dark:text-slate-400 max-w-xl mx-auto text-base">
            Upload course materials, guidelines, and manuals to configure custom AI assistant knowledge for instant portal responses.
          </p>
        </div>

        {/* Dashboard Cards Grid */}
        <div className="grid md:grid-cols-2 gap-8 items-stretch animate-in fade-in-50 duration-700">
          {/* Document Ingestion Card */}
          <div className="bg-white/70 dark:bg-slate-900/80 backdrop-blur-xl rounded-3xl p-8 border border-slate-200/50 dark:border-slate-800/80 shadow-lg flex flex-col justify-between">
            <div>
              <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100 mb-2 flex items-center gap-2">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                  className="w-5 h-5 text-blue-600"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z"
                  />
                </svg>
                Ingest Portal Information
              </h2>
              <p className="text-slate-500 dark:text-slate-400 text-xs mb-6 leading-relaxed">
                Add institutional content (policies, guides, FAQs) to the AI knowledge base.
              </p>

              <form onSubmit={handleIngest} className="space-y-4">
                <label className="block">
                  <span className="text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1 block">
                    Document title
                  </span>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. AJU Student Handbook 2026"
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 text-sm text-slate-800 dark:text-slate-200 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20"
                  />
                </label>

                <label className="block">
                  <span className="text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1 block">
                    Content
                  </span>
                  <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    rows={4}
                    placeholder="Paste the institutional text to index (academic policies, course guides, FAQs)..."
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 text-sm text-slate-800 dark:text-slate-200 outline-none resize-y focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20"
                  />
                </label>

                <label className="block">
                  <span className="text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1 block">
                    Admin API key
                  </span>
                  <input
                    type="password"
                    value={adminKey}
                    onChange={(e) => setAdminKey(e.target.value)}
                    placeholder="Required — matches backend ADMIN_API_KEY (never stored)"
                    autoComplete="off"
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 text-sm text-slate-800 dark:text-slate-200 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20"
                  />
                </label>

                <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={isConfidential}
                    onChange={(e) => setIsConfidential(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  Student-only content (hidden from public visitors)
                </label>

                <button
                  type="submit"
                  disabled={isUploading || !title.trim() || !content.trim() || !adminKey.trim()}
                  className="w-full py-3 px-4 rounded-xl text-sm font-bold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-slate-200 disabled:to-slate-200 dark:disabled:from-slate-800 dark:disabled:to-slate-800 text-white shadow-md transition-all hover:scale-[1.01] active:scale-[0.99] disabled:scale-100 disabled:cursor-not-allowed cursor-pointer outline-none"
                >
                  {isUploading ? "Processing Knowledge..." : "Ingest Document"}
                </button>
                <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1 leading-relaxed">
                  Admin-only ingestion via POST /api/v1/ingest. The key is sent as the
                  X-API-Key header and is never stored in the browser.
                </p>
              </form>
            </div>

            {statusMsg && (
              <div
                className={`mt-4 p-3 rounded-xl text-xs flex gap-2 border leading-relaxed animate-in fade-in duration-200 ${
                  statusMsg.type === "success"
                    ? "bg-emerald-50/50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-900/50 text-emerald-800 dark:text-emerald-300"
                    : "bg-rose-50/50 dark:bg-rose-950/20 border-rose-200 dark:border-rose-900/50 text-rose-800 dark:text-rose-300"
                }`}
              >
                <span>{statusMsg.type === "success" ? "✓" : "⚠"}</span>
                <span>{statusMsg.text}</span>
              </div>
            )}
          </div>

          {/* Quick Guide Card */}
          <div className="bg-white/70 dark:bg-slate-900/80 backdrop-blur-xl rounded-3xl p-8 border border-slate-200/50 dark:border-slate-800/80 shadow-lg flex flex-col justify-between">
            <div>
              <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100 mb-2 flex items-center gap-2">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                  className="w-5 h-5 text-indigo-600"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
                  />
                </svg>
                Portal Usage Guide
              </h2>
              <p className="text-slate-500 dark:text-slate-400 text-xs mb-6 leading-relaxed">
                Step-by-step instructions to configure and execute RAG search.
              </p>

              <ol className="space-y-4 text-xs text-slate-600 dark:text-slate-400 leading-relaxed list-decimal list-inside">
                <li>
                  <strong className="text-slate-700 dark:text-slate-300">Ingest documents:</strong> Provide a title, paste the content, and enter the admin key in the ingestion control panel.
                </li>
                <li>
                  <strong className="text-slate-700 dark:text-slate-300">Processing:</strong> The server automatically segments texts, embeds them, and populates the pgvector table.
                                </li>
                <li>
                  <strong className="text-slate-700 dark:text-slate-300">Intelligent Q&A:</strong> Click the floating bubble in the bottom right corner to invoke the chat assistant.
                </li>
                <li>
                  <strong className="text-slate-700 dark:text-slate-300">Dynamic Pills:</strong> Click any of the popular suggested pills to test search instantly.
                </li>
              </ol>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800 text-[10px] text-slate-400 dark:text-slate-500 text-center">
              Powered by pgvector and OpenAI Streaming GPT Core
            </div>
          </div>
        </div>
      </div>

      {/* Footer copyright */}
      <footer className="w-full text-center text-[11px] text-slate-400 dark:text-slate-600 z-10 pt-8">
        © {new Date().getFullYear()} Arthur Jarvis University. All Rights Reserved.
      </footer>

      {/* RAG Floating Chat Widget */}
      <ChatWidget />
    </main>
  );
}
