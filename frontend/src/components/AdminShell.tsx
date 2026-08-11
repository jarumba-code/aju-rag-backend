"use client"

import React, { useState } from "react"
import { usePathname } from "next/navigation"
import Link from "next/link"
import {
  LayoutDashboard,
  FileText,
  Upload,
  AlertTriangle,
  Lightbulb,
  BarChart3,
  Users,
  ScrollText,
  Settings,
  Menu,
  X,
  LogOut,
  Shield,
} from "lucide-react"
import { useAdminAuth } from "@/components/AdminAuthProvider"

const navItems = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/documents", label: "Content Management", icon: FileText },
  { href: "/admin/upload", label: "Upload Document", icon: Upload },
  { href: "/admin/gaps", label: "Gaps & Improvements", icon: AlertTriangle },
  { href: "/admin/suggested-questions", label: "Suggested Questions", icon: Lightbulb },
  { href: "/admin/analytics", label: "Analytics & Reports", icon: BarChart3 },
  { href: "/admin/users", label: "Admin Users", icon: Users },
  { href: "/admin/audit-log", label: "Audit Log", icon: ScrollText },
  { href: "/admin/settings", label: "Settings", icon: Settings },
]

export default function AdminShell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const pathname = usePathname()
  const { state, role, signOut } = useAdminAuth()

  if (state === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-navy">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-gold-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gold-100 aju-serif text-lg">Loading Admin Portal...</p>
        </div>
      </div>
    )
  }

  if (state === "unauthenticated") {
    return null
  }

  const isActive = (href: string) => {
    if (href === "/admin") return pathname === "/admin"
    return pathname.startsWith(href)
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <aside
        className="fixed top-0 left-0 z-50 h-screen w-64 bg-navy text-gold-100 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:z-auto"
        style={sidebarOpen ? { transform: "translateX(0)" } : { transform: "translateX(-100%)" }}
      >
        <div className="flex flex-col h-full">
          <div className="flex items-center justify-between p-6 border-b border-gold-900/30">
            <div>
              <h1 className="text-xl font-bold aju-serif text-gold-100">AJU Admin</h1>
              <p className="text-xs text-gold-300 mt-0.5">Knowledge Portal</p>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-gold-300 hover:text-gold-100"
            >
              <X size={20} />
            </button>
          </div>

          <nav className="flex-1 overflow-y-auto py-4 px-3">
            <ul className="space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon
                const active = isActive(item.href)
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group ${
                        active ? "bg-gold-600 text-white shadow-lg" : "text-gold-200 hover:bg-gold-900/30 hover:text-gold-100"
                      }`}
                      onClick={() => setSidebarOpen(false)}
                    >
                      <Icon size={18} className={active ? "text-white" : "text-gold-400 group-hover:text-gold-200"} />
                      <span className="text-sm font-medium">{item.label}</span>
                    </Link>
                  </li>
                )
              })}
            </ul>
          </nav>

          <div className="p-4 border-t border-gold-900/30">
            <div className="flex items-center gap-3 mb-3 px-2">
              <div className="w-8 h-8 rounded-full bg-gold-600 flex items-center justify-center">
                <Shield size={16} className="text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gold-100 truncate">
                  {role === "super_admin" ? "Super Admin" : "Administrator"}
                </p>
                <p className="text-xs text-gold-400 truncate">Administrator</p>
              </div>
            </div>
            <button
              onClick={signOut}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-red-900/20 text-red-300 hover:bg-red-900/40 transition-colors duration-200"
            >
              <LogOut size={16} />
              <span className="text-sm">Sign Out</span>
            </button>
          </div>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
          <div className="flex items-center justify-between px-6 py-4">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden text-slate-600 hover:text-slate-900"
              >
                <Menu size={24} />
              </button>
              <div>
                <h2 className="text-lg font-semibold text-navy aju-serif">
                  {navItems.find((item) => isActive(item.href))?.label || "Admin Portal"}
                </h2>
                <p className="text-xs text-slate-500">
                  Arthur Jarvis University - {new Date().toLocaleDateString("en-NG", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-1.5"></span>
                System Online
              </span>
            </div>
          </div>
        </header>

        <main className="flex-1 p-6">
          <div className="animate-fade-in">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
