import React from "react";

// Route group layout for /admin/login. Intentionally renders children directly
// with NO AdminAuthProvider/AdminShell, so the login page is never subject to
// the auth gate (which would blank it on a 401 from /api/admin/me).
export default function AuthGroupLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
