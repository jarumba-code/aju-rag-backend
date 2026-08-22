import React from "react";

// Shared root layout for both admin route groups. Renders children directly —
// no AdminAuthProvider/AdminShell here (those live in (protected)/layout.tsx so
// that /admin/login is not subject to the auth gate).
export const metadata = {
  title: "Admin Portal — Arthur Jarvis University",
  description: "AJU Knowledge Management Admin Portal",
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

