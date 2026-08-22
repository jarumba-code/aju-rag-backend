import React from "react";
import { AdminAuthProvider } from "@/components/AdminAuthProvider";
import AdminShell from "@/components/AdminShell";

// Layout for all authenticated admin pages (everything under (protected)/).
// /admin/login lives in the sibling (auth) route group and is intentionally
// NOT wrapped by AdminAuthProvider/AdminShell, so it renders even when the
// auth state is "unauthenticated".
export default function ProtectedAdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminAuthProvider>
      <AdminShell>{children}</AdminShell>
    </AdminAuthProvider>
  );
}
