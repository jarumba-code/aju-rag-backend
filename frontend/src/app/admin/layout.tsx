import React from "react";
import { AdminAuthProvider } from "@/components/AdminAuthProvider";
import AdminShell from "@/components/AdminShell";

export const metadata = {
  title: "Admin Portal — Arthur Jarvis University",
  description: "AJU Knowledge Management Admin Portal",
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminAuthProvider>
      <AdminShell>{children}</AdminShell>
    </AdminAuthProvider>
  );
}
