"use client";

import React from "react";
import AJUHeader from "@/components/public/AJUHeader";
import AJUFooter from "@/components/public/AJUFooter";

export default function SettingsPage() {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col">
      <AJUHeader />
      <main className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-4">Settings</h1>
          <p className="text-slate-600 dark:text-slate-400">
            This section is currently under development. Coming soon!
          </p>
        </div>
      </main>
      <AJUFooter />
    </div>
  );
}
