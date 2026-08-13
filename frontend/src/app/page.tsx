"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowRight, BookOpen, Users, GraduationCap, MessageSquare } from "lucide-react";
import AJUHeader from "@/components/public/AJUHeader";
import AJUFooter from "@/components/public/AJUFooter";
import { fetchSuggestedQuestions } from "@/lib/api";

interface SuggestedQuestion {
  id: string;
  question: string;
  category?: string;
}

export default function Home() {
  const [suggested, setSuggested] = useState<SuggestedQuestion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchSuggestedQuestions(5)
      .then((items) => {
        if (!cancelled) {
          setSuggested(items.map((q, idx) => ({ id: String(idx), question: q })));
        }
      })
      .catch(() => {
        if (!cancelled) setSuggested([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col">
      <AJUHeader />

      <main className="flex-1">
        <section className="relative overflow-hidden">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-28">
            <div className="max-w-3xl">
              <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-950/30 border border-blue-100 dark:border-blue-900 text-blue-700 dark:text-blue-300 text-xs font-semibold uppercase tracking-wide mb-6">
                <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
                Arthur Jarvis University Smart Portal
              </span>

              <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-slate-900 dark:text-white leading-tight mb-6">
                Ask <span className="text-blue-600">AJU Intelligent</span>
              </h1>

              <p className="text-lg md:text-xl text-slate-600 dark:text-slate-300 mb-8 max-w-2xl">
                Get instant answers about admissions, programmes, university policies, student services, and institutional information.
              </p>

              <div className="flex flex-col sm:flex-row gap-3">
                <Link
                  href="/chat"
                  className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold hover:from-blue-700 hover:to-indigo-700 transition-all shadow-md hover:shadow-lg"
                >
                  <MessageSquare size={18} />
                  Ask AJU
                  <ArrowRight size={16} />
                </Link>
              </div>
            </div>
          </div>
        </section>

        <section className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-6">Suggested Questions</h2>
            {loading ? (
              <div className="flex flex-wrap gap-2">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-10 w-48 rounded-full bg-slate-100 dark:bg-slate-800 animate-pulse" />
                ))}
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {suggested.map((item) => (
                  <Link
                    key={item.id}
                    href={`/chat?q=${encodeURIComponent(item.question)}`}
                    className="px-4 py-2 rounded-full border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-sm text-slate-700 dark:text-slate-300 hover:border-blue-300 dark:hover:border-blue-700 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
                  >
                    {item.question}
                  </Link>
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="border-t border-slate-200 dark:border-slate-800">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
            <div className="grid md:grid-cols-3 gap-8">
              <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6">
                <GraduationCap className="w-8 h-8 text-blue-600 mb-4" />
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">Admissions</h3>
                <p className="text-sm text-slate-600 dark:text-slate-400">Entry requirements, application steps, deadlines, and entry pathways.</p>
              </div>
              <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6">
                <BookOpen className="w-8 h-8 text-blue-600 mb-4" />
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">Programmes</h3>
                <p className="text-sm text-slate-600 dark:text-slate-400">Explore faculties, degrees, course structures, and academic regulations.</p>
              </div>
              <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6">
                <Users className="w-8 h-8 text-blue-600 mb-4" />
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">Student Services</h3>
                <p className="text-sm text-slate-600 dark:text-slate-400">Support services, accommodation, finance, and campus life guidance.</p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <AJUFooter />
    </div>
  );
}
