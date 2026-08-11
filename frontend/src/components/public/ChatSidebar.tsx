"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { MessageSquare, LayoutDashboard, FolderOpen, Settings, HelpCircle, Shield, Plus, Menu, X } from "lucide-react";
import AJULogo from "./AJULogo";

interface ChatSidebarProps {
  conversations?: Array<{ id: string; title: string }>;
  activeConversationId?: string | null;
  onNewChat?: () => void;
  onSelectConversation?: (id: string) => void;
  persona?: "public" | "student" | "staff";
  onPersonaChange?: (p: "public" | "student" | "staff") => void;
}

export default function ChatSidebar({
  conversations = [],
  activeConversationId,
  onNewChat,
  onSelectConversation,
  persona = "public",
  onPersonaChange,
}: ChatSidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/chat") return pathname === "/chat";
    return pathname.startsWith(href);
  };

  const navItems = [
    { href: "/chat", label: "Conversation", icon: MessageSquare },
    { href: "/", label: "Home", icon: LayoutDashboard },
    { href: "/resources", label: "Resources", icon: FolderOpen },
    { href: "/settings", label: "Settings", icon: Settings },
    { href: "/help", label: "Help", icon: HelpCircle },
  ];

  return (
    <>
      {mobileOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setMobileOpen(false)} />
      )}

      <aside
        className={`fixed top-0 left-0 z-50 h-screen w-72 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:z-auto ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="flex flex-col h-full">
          <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-800">
            <Link href="/" className="flex-shrink-0">
              <AJULogo size="sm" />
            </Link>
            <button onClick={() => setMobileOpen(false)} className="lg:hidden p-2 rounded-lg text-slate-600 hover:bg-slate-100" aria-label="Close sidebar">
              <X size={20} />
            </button>
          </div>

          <div className="p-4">
            <button
              onClick={() => { onNewChat?.(); setMobileOpen(false); }}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold hover:from-blue-700 hover:to-indigo-700 transition-all shadow-md"
            >
              <Plus size={18} />
              <span>New Chat</span>
            </button>
          </div>

          <nav className="flex-1 overflow-y-auto px-3 pb-4" aria-label="Chat navigation">
            <ul className="space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={() => setMobileOpen(false)}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 ${active ? "bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 font-medium" : "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"}`}
                    >
                      <Icon size={18} className={active ? "text-blue-600" : "text-slate-400"} />
                      <span className="text-sm">{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>

            {conversations.length > 0 && (
              <div className="mt-6">
                <h3 className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider px-3 mb-2">Recent</h3>
                <ul className="space-y-1">
                  {conversations.map((conv) => (
                    <li key={conv.id}>
                      <button
                        onClick={() => { onSelectConversation?.(conv.id); setMobileOpen(false); }}
                        className={`w-full text-left px-3 py-2 rounded-xl text-sm truncate transition-colors ${activeConversationId === conv.id ? "bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300" : "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"}`}
                      >
                        {conv.title}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </nav>

          <div className="p-4 border-t border-slate-200 dark:border-slate-800 space-y-3">
            <div className="flex items-center gap-2 px-2">
              <Shield size={16} className="text-slate-400" />
              <span className="text-xs font-medium text-slate-500">Mode:</span>
              <select
                value={persona}
                onChange={(e) => onPersonaChange?.(e.target.value as "public" | "student" | "staff")}
                className="text-xs bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label="Select persona mode"
              >
                <option value="public">Public</option>
                <option value="student">Student (Dev)</option>
                <option value="staff">Staff (Dev)</option>
              </select>
            </div>

            <Link href="/help" className="flex items-center gap-3 px-3 py-2 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
              <HelpCircle size={18} className="text-slate-400" />
              <span className="text-sm">Help & FAQ</span>
            </Link>
          </div>
        </div>
      </aside>

      <button
        onClick={() => setMobileOpen(true)}
        className="fixed bottom-6 left-6 z-30 lg:hidden w-12 h-12 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-lg flex items-center justify-center text-slate-600 hover:text-blue-600 transition-colors"
        aria-label="Open menu"
      >
        <Menu size={20} />
      </button>
    </>
  );
}
