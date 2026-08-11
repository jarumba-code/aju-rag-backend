"use client";

import React from "react";
import Link from "next/link";

interface PortalCardProps {
  title: string;
  description: string;
  href: string;
  icon: React.ReactNode;
  cta: string;
}

export default function PortalCard({ title, description, href, icon, cta }: PortalCardProps) {
  return (
    <Link
      href={href}
      className="group block bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6 hover:shadow-lg hover:border-blue-300 dark:hover:border-blue-700 transition-all duration-200"
    >
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-blue-50 dark:bg-blue-950/30 flex items-center justify-center text-blue-600 dark:text-blue-400 group-hover:scale-110 transition-transform">
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">{title}</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-3">{description}</p>
          <span className="inline-flex items-center text-sm font-medium text-blue-600 dark:text-blue-400 group-hover:underline">
            {cta}
            <svg className="ml-1 w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
            </svg>
          </span>
        </div>
      </div>
    </Link>
  );
}
