"use client";

import React from "react";
import Link from "next/link";
import AJULogo from "./AJULogo";

export default function AJUFooter() {
  return (
    <footer className="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="md:col-span-2">
            <AJULogo size="sm" />
            <p className="mt-3 text-sm text-slate-500 dark:text-slate-400 max-w-md">
              AJU Intelligent is your dedicated academic companion at Arthur Jarvis University.
              Get instant answers about admissions, programmes, policies, and student services.
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-3">Quick Links</h3>
            <ul className="space-y-2">
              {[
                { href: "/", label: "Home" },
                { href: "/chat", label: "Ask AJU" },
                { href: "/resources", label: "Resources" },
                { href: "/help", label: "FAQ" },
                { href: "/student", label: "Student Portal" },
                { href: "/staff", label: "Staff Portal" },
              ].map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-3">Legal</h3>
            <ul className="space-y-2">
              {[
                { href: "#", label: "Privacy Policy" },
                { href: "#", label: "Terms of Service" },
                { href: "#", label: "Contact Us" },
              ].map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-slate-500 dark:text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-slate-200 dark:border-slate-800">
          <p className="text-xs text-slate-400 dark:text-slate-500 text-center">
            © {new Date().getFullYear()} Arthur Jarvis University. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
