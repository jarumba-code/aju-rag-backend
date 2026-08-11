"use client";

import React, { createContext, useContext, useState, useCallback, ReactNode } from "react";
import type { Persona } from "@/lib/api";

interface PersonaContextValue {
  persona: Persona;
  setPersona: (p: Persona) => void;
  switchToStudent: () => void;
  switchToStaff: () => void;
  switchToPublic: () => void;
  isStudent: boolean;
  isStaff: boolean;
  isPublic: boolean;
}

const PersonaContext = createContext<PersonaContextValue | null>(null);

export function PersonaProvider({ children }: { children: ReactNode }) {
  const [persona, setPersona] = useState<Persona>("public");

  const switchToStudent = useCallback(() => setPersona("student"), []);
  const switchToStaff = useCallback(() => setPersona("staff"), []);
  const switchToPublic = useCallback(() => setPersona("public"), []);

  return (
    <PersonaContext.Provider
      value={{
        persona,
        setPersona,
        switchToStudent,
        switchToStaff,
        switchToPublic,
        isStudent: persona === "student",
        isStaff: persona === "staff",
        isPublic: persona === "public",
      }}
    >
      {children}
    </PersonaContext.Provider>
  );
}

export function usePersona(): PersonaContextValue {
  const ctx = useContext(PersonaContext);
  if (!ctx) {
    // Fallback for usage outside provider (should not happen in app)
    return {
      persona: "public",
      setPersona: () => {},
      switchToStudent: () => {},
      switchToStaff: () => {},
      switchToPublic: () => {},
      isStudent: false,
      isStaff: false,
      isPublic: true,
    };
  }
  return ctx;
}
