"use client";

import React, { useState } from "react";
import ChatWidget from "../components/ChatWidget";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: "success" | "error"; text: str } | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setStatusMsg(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setIsUploading(true);
    setStatusMsg(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/upload`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (response.ok) {
        setStatusMsg({
          type: "success",
          text: `Document "${file.name}" ingested successfully! It is now searchable by the AI assistant.`,
        });
        setFile(null);
      } else {
        setStatusMsg({
          type: "error",
          text: data.detail || "Failed to ingest the document.",
        });
      }
    } catch (err) {
      console.error(err);
      setStatusMsg({
        type: "error",
        text: "Network error occurred. Ensure the backend is running.",
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
                Add PDFs containing student catalogs, courses, calendars, or guides.
              </p>

              <form onSubmit={handleUpload} className="space-y-4">
                <div className="border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-2xl p-6 hover:border-blue-500/50 transition-colors flex flex-col items-center justify-center relative cursor-pointer group bg-slate-50/50 dark:bg-slate-950/20">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleFileChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <div className="text-center">
                    <p className="text-sm font-semibold text-slate-700 dark:text-slate-300 group-hover:text-blue-600 transition-colors">
                      {file ? file.name : "Select school PDF"}
                    </p>
                    <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
                      PDF formats up to 50MB
                    </p>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={!file || isUploading}
                  className="w-full py-3 px-4 rounded-xl text-sm font-bold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-slate-200 disabled:to-slate-200 dark:disabled:from-slate-850 dark:disabled:to-slate-850 text-white shadow-md transition-all hover:scale-[1.01] active:scale-[0.99] disabled:scale-100 disabled:cursor-not-allowed cursor-pointer outline-none"
                >
                  {isUploading ? "Processing Knowledge..." : "Ingest Document"}
                </button>
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
                  <strong className="text-slate-700 dark:text-slate-300">Upload documents:</strong> Drag or click to select documentation PDFs in the ingestion control panel.
                </li>
                <li>
                  <strong className="text-slate-700 dark:text-slate-300">Processing:</strong> The server automatically segments texts, embeds with OpenAI, and populates the pgvector table.
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
