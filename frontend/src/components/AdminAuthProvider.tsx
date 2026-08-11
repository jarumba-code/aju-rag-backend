"use client";
import React, { createContext, useContext, useEffect, useState } from "react";
import { adminMe, adminLogout } from "@/lib/adminApi";

type AuthState = "loading" | "authenticated" | "unauthenticated";

interface AdminAuthContextValue {
  state: AuthState;
  role: string | null;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AdminAuthContext = createContext<AdminAuthContextValue>({
  state: "loading",
  role: null,
  signOut: async () => {},
  refresh: async () => {},
});

export function AdminAuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>("loading");
  const [role, setRole] = useState<string | null>(null);

  const refresh = async () => {
    setState("loading");
    try {
      const data = await adminMe();
      if (data.authenticated) {
        setState("authenticated");
        setRole(data.role ?? "admin");
      } else {
        setState("unauthenticated");
        setRole(null);
      }
    } catch {
      setState("unauthenticated");
      setRole(null);
    }
  };

  const signOut = async () => {
    await adminLogout();
    setState("unauthenticated");
    setRole(null);
    window.location.href = "/admin/login";
  };

  useEffect(() => {
    refresh();
  }, []);

  return (
    <AdminAuthContext.Provider value={{ state, role, signOut, refresh }}>
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  return useContext(AdminAuthContext);
}
