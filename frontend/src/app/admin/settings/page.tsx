"use client";
import React, { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAdminAuth } from "@/components/AdminAuthProvider";
import { changeAdminPassword, AdminApiError } from "@/lib/adminApi";

type Tab = "security" | "session";

export default function AdminSettingsPage() {
  const router = useRouter();
  const { state, role, signOut } = useAdminAuth();

  const [tab, setTab] = useState<Tab>("security");

  // Password change form
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [pwError, setPwError] = useState<string | null>(null);
  const [pwSuccess, setPwSuccess] = useState<string | null>(null);
  const [pwLoading, setPwLoading] = useState(false);

  // Redirect if not authenticated
  useEffect(() => {
    if (state === "unauthenticated") {
      router.replace("/admin/login");
    }
  }, [state, router]);

  if (state === "loading") {
    return (
      <div style={fullPageStyle}>
        <div style={{ color: "rgba(255,255,255,0.5)", fontSize: "16px" }}>Verifying session…</div>
      </div>
    );
  }

  const handlePasswordChange = async (e: FormEvent) => {
    e.preventDefault();
    setPwError(null);
    setPwSuccess(null);

    if (newPw.length < 8) {
      setPwError("New password must be at least 8 characters.");
      return;
    }
    if (newPw !== confirmPw) {
      setPwError("New passwords do not match.");
      return;
    }
    if (currentPw === newPw) {
      setPwError("New password must differ from your current password.");
      return;
    }

    setPwLoading(true);
    try {
      const res = await changeAdminPassword(currentPw, newPw);
      setPwSuccess(res.message || "Password changed. Please sign in again.");
      setCurrentPw("");
      setNewPw("");
      setConfirmPw("");
      // Force re-authentication — all previous tokens are now invalid
      setTimeout(() => signOut(), 2000);
    } catch (err) {
      if (err instanceof AdminApiError) {
        setPwError(err.message);
      } else {
        setPwError("An unexpected error occurred.");
      }
    } finally {
      setPwLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(135deg, #0a1628 0%, #0d2347 50%, #1a3a5c 100%)",
      fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
    }}>
      {/* Topbar */}
      <header style={{
        background: "rgba(255,255,255,0.03)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid rgba(212,175,55,0.15)",
        padding: "0 32px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        height: "64px",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{ fontSize: "24px" }}>🎓</span>
          <span style={{ color: "#d4af37", fontWeight: 700, fontSize: "16px", letterSpacing: "-0.2px" }}>
            AJU Admin Portal
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <span style={{ color: "rgba(255,255,255,0.45)", fontSize: "13px" }}>
            Signed in as <strong style={{ color: "rgba(255,255,255,0.7)" }}>{role ?? "admin"}</strong>
          </span>
          <button
            id="admin-signout-btn"
            onClick={signOut}
            style={{
              background: "rgba(239,68,68,0.12)", color: "#fca5a5",
              border: "1px solid rgba(239,68,68,0.3)", borderRadius: "8px",
              padding: "8px 16px", fontSize: "13px", fontWeight: 500, cursor: "pointer",
              transition: "all 0.2s",
            }}
          >
            Sign Out
          </button>
        </div>
      </header>

      <div style={{ maxWidth: "720px", margin: "48px auto", padding: "0 24px" }}>
        <h1 style={{ color: "#fff", fontSize: "28px", fontWeight: 700, margin: "0 0 8px", letterSpacing: "-0.4px" }}>
          Settings
        </h1>
        <p style={{ color: "rgba(255,255,255,0.45)", fontSize: "15px", margin: "0 0 36px" }}>
          Manage your admin session and security settings.
        </p>

        {/* Tabs */}
        <div style={{ display: "flex", gap: "4px", marginBottom: "32px", background: "rgba(255,255,255,0.04)", borderRadius: "10px", padding: "4px" }}>
          {(["security", "session"] as Tab[]).map((t) => (
            <button
              key={t}
              id={`tab-${t}`}
              onClick={() => setTab(t)}
              style={{
                flex: 1, padding: "10px 20px",
                background: tab === t ? "rgba(212,175,55,0.15)" : "transparent",
                color: tab === t ? "#d4af37" : "rgba(255,255,255,0.5)",
                border: tab === t ? "1px solid rgba(212,175,55,0.3)" : "1px solid transparent",
                borderRadius: "8px", cursor: "pointer", fontWeight: 600, fontSize: "14px",
                transition: "all 0.2s", textTransform: "capitalize",
              }}
            >
              {t === "security" ? "🔐 Security" : "🕐 Session"}
            </button>
          ))}
        </div>

        {/* Security Tab */}
        {tab === "security" && (
          <div style={cardStyle}>
            <h2 style={{ color: "#d4af37", fontSize: "18px", fontWeight: 700, margin: "0 0 8px" }}>
              Change Password
            </h2>
            <p style={{ color: "rgba(255,255,255,0.45)", fontSize: "14px", margin: "0 0 28px" }}>
              After changing your password, all active sessions will be invalidated and you will need to sign in again.
            </p>

            <form onSubmit={handlePasswordChange}>
              {[
                { id: "current-pw", label: "Current Password", value: currentPw, onChange: setCurrentPw, complete: "current-password" },
                { id: "new-pw", label: "New Password (min. 8 chars)", value: newPw, onChange: setNewPw, complete: "new-password" },
                { id: "confirm-pw", label: "Confirm New Password", value: confirmPw, onChange: setConfirmPw, complete: "new-password" },
              ].map(({ id, label, value, onChange, complete }) => (
                <div key={id} style={{ marginBottom: "20px" }}>
                  <label style={labelStyle}>{label}</label>
                  <input
                    id={id}
                    type="password"
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    autoComplete={complete}
                    required
                    style={inputStyle}
                  />
                </div>
              ))}

              {pwError && (
                <div style={errorBoxStyle}>{pwError}</div>
              )}
              {pwSuccess && (
                <div style={successBoxStyle}>{pwSuccess} Signing you out…</div>
              )}

              <button
                id="change-password-submit"
                type="submit"
                disabled={pwLoading || !currentPw || !newPw || !confirmPw}
                style={{
                  ...btnPrimaryStyle,
                  opacity: pwLoading || !currentPw || !newPw || !confirmPw ? 0.4 : 1,
                  cursor: pwLoading || !currentPw || !newPw || !confirmPw ? "not-allowed" : "pointer",
                }}
              >
                {pwLoading ? "Updating…" : "Update Password"}
              </button>
            </form>
          </div>
        )}

        {/* Session Tab */}
        {tab === "session" && (
          <div style={cardStyle}>
            <h2 style={{ color: "#d4af37", fontSize: "18px", fontWeight: 700, margin: "0 0 24px" }}>
              Session Information
            </h2>
            <div style={{ display: "grid", gap: "16px" }}>
              {[
                { label: "Role", value: role ?? "admin" },
                { label: "Session Type", value: "JWT Bearer Token (HttpOnly Cookie)" },
                { label: "Token Expiry", value: "4 hours from login" },
                { label: "Auth Boundary", value: "FastAPI backend (server-side)" },
              ].map(({ label, value }) => (
                <div key={label} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "14px 16px", background: "rgba(255,255,255,0.04)",
                  borderRadius: "8px", border: "1px solid rgba(255,255,255,0.06)",
                }}>
                  <span style={{ color: "rgba(255,255,255,0.5)", fontSize: "13px" }}>{label}</span>
                  <span style={{ color: "rgba(255,255,255,0.85)", fontSize: "14px", fontWeight: 500 }}>{value}</span>
                </div>
              ))}
            </div>

            <div style={{ marginTop: "32px", paddingTop: "24px", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
              <h3 style={{ color: "rgba(255,255,255,0.7)", fontSize: "15px", fontWeight: 600, margin: "0 0 12px" }}>
                Sign Out
              </h3>
              <p style={{ color: "rgba(255,255,255,0.4)", fontSize: "13px", margin: "0 0 16px" }}>
                This will revoke your session token and redirect you to the login page.
              </p>
              <button
                id="session-signout-btn"
                onClick={signOut}
                style={{
                  background: "rgba(239,68,68,0.1)", color: "#fca5a5",
                  border: "1px solid rgba(239,68,68,0.3)", borderRadius: "8px",
                  padding: "10px 24px", fontSize: "14px", fontWeight: 600, cursor: "pointer",
                }}
              >
                Sign Out Now
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// --- Shared styles ---
const fullPageStyle: React.CSSProperties = {
  minHeight: "100vh",
  background: "linear-gradient(135deg, #0a1628 0%, #0d2347 50%, #1a3a5c 100%)",
  display: "flex", alignItems: "center", justifyContent: "center",
  fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
};

const cardStyle: React.CSSProperties = {
  background: "rgba(255,255,255,0.04)",
  backdropFilter: "blur(12px)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: "16px",
  padding: "36px",
};

const labelStyle: React.CSSProperties = {
  display: "block", color: "rgba(255,255,255,0.6)",
  fontSize: "12px", fontWeight: 500, marginBottom: "8px",
  letterSpacing: "0.3px", textTransform: "uppercase",
};

const inputStyle: React.CSSProperties = {
  width: "100%", boxSizing: "border-box",
  background: "rgba(255,255,255,0.06)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: "8px", padding: "12px 14px",
  color: "#fff", fontSize: "14px", outline: "none",
};

const errorBoxStyle: React.CSSProperties = {
  background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
  borderRadius: "8px", padding: "12px 14px",
  color: "#fca5a5", fontSize: "13px", marginBottom: "20px",
};

const successBoxStyle: React.CSSProperties = {
  background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.3)",
  borderRadius: "8px", padding: "12px 14px",
  color: "#86efac", fontSize: "13px", marginBottom: "20px",
};

const btnPrimaryStyle: React.CSSProperties = {
  background: "linear-gradient(135deg, #d4af37, #b8962e)",
  color: "#0a1628", fontWeight: 700, fontSize: "14px",
  border: "none", borderRadius: "8px", padding: "12px 24px",
  transition: "all 0.2s",
};
