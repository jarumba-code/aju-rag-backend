"use client";
import React, { Suspense, useState, useEffect, FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { adminLogin, AdminApiError } from "@/lib/adminApi";

export default function AdminLoginPage() {
  return (
    <Suspense fallback={null}>
      <AdminLoginForm />
    </Suspense>
  );
}

function AdminLoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await adminLogin(password);
      const next = searchParams.get("next") ?? "/admin/settings";
      router.replace(next);
    } catch (err) {
      if (err instanceof AdminApiError) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(135deg, #0a1628 0%, #0d2347 50%, #1a3a5c 100%)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
    }}>
      {/* Background decoration */}
      <div style={{
        position: "fixed", inset: 0, overflow: "hidden", pointerEvents: "none",
      }}>
        <div style={{
          position: "absolute", top: "-20%", right: "-10%",
          width: "600px", height: "600px", borderRadius: "50%",
          background: "radial-gradient(circle, rgba(212,175,55,0.08) 0%, transparent 70%)",
        }} />
        <div style={{
          position: "absolute", bottom: "-10%", left: "-10%",
          width: "500px", height: "500px", borderRadius: "50%",
          background: "radial-gradient(circle, rgba(26,90,140,0.2) 0%, transparent 70%)",
        }} />
      </div>

      <div style={{
        width: "100%", maxWidth: "440px", margin: "0 24px",
        background: "rgba(255,255,255,0.04)",
        backdropFilter: "blur(20px)",
        border: "1px solid rgba(212,175,55,0.2)",
        borderRadius: "20px",
        padding: "48px 40px",
        boxShadow: "0 25px 60px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.05) inset",
      }}>
        {/* Logo / Crest area */}
        <div style={{ textAlign: "center", marginBottom: "40px" }}>
          <div style={{
            width: "72px", height: "72px", borderRadius: "50%",
            background: "linear-gradient(135deg, #d4af37, #f0d060)",
            margin: "0 auto 16px",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "32px", boxShadow: "0 4px 20px rgba(212,175,55,0.4)",
          }}>
            🎓
          </div>
          <h1 style={{
            color: "#d4af37", fontSize: "22px", fontWeight: 700,
            margin: "0 0 4px", letterSpacing: "-0.3px",
          }}>
            AJU Admin Portal
          </h1>
          <p style={{ color: "rgba(255,255,255,0.45)", fontSize: "14px", margin: 0 }}>
            Arthur Jarvis University — Knowledge Management
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "24px" }}>
            <label style={{
              display: "block", color: "rgba(255,255,255,0.7)",
              fontSize: "13px", fontWeight: 500, marginBottom: "8px",
              letterSpacing: "0.3px", textTransform: "uppercase",
            }}>
              Administrator Password
            </label>
            <input
              id="admin-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
              autoFocus
              autoComplete="current-password"
              style={{
                width: "100%", boxSizing: "border-box",
                background: "rgba(255,255,255,0.06)",
                border: `1px solid ${error ? "rgba(239,68,68,0.6)" : "rgba(255,255,255,0.12)"}`,
                borderRadius: "10px", padding: "14px 16px",
                color: "#fff", fontSize: "15px", outline: "none",
                transition: "border-color 0.2s",
              }}
            />
          </div>

          {error && (
            <div style={{
              background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.3)",
              borderRadius: "8px", padding: "12px 14px",
              color: "#fca5a5", fontSize: "13px", marginBottom: "20px",
            }}>
              {error}
            </div>
          )}

          <button
            id="admin-login-submit"
            type="submit"
            disabled={loading || !password}
            style={{
              width: "100%", padding: "14px",
              background: loading || !password
                ? "rgba(212,175,55,0.3)"
                : "linear-gradient(135deg, #d4af37, #b8962e)",
              color: "#0a1628", fontWeight: 700, fontSize: "15px",
              border: "none", borderRadius: "10px", cursor: loading || !password ? "not-allowed" : "pointer",
              transition: "all 0.2s", letterSpacing: "0.2px",
              boxShadow: loading || !password ? "none" : "0 4px 16px rgba(212,175,55,0.3)",
            }}
          >
            {loading ? "Authenticating…" : "Sign In"}
          </button>
        </form>

        <p style={{
          textAlign: "center", marginTop: "32px",
          color: "rgba(255,255,255,0.25)", fontSize: "12px",
        }}>
          Protected administrative access only.
        </p>
      </div>
    </div>
  );
}
