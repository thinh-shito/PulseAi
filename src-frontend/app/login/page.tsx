"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Lock, Mail, Loader2, BarChart3, ShieldCheck } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);

      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Invalid credentials. Please try again.");
      }

      const data = await res.json();
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("role", data.role);
      localStorage.setItem("email", email);

      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        background: "var(--bg-base)",
      }}
    >
      {/* ── Left branding panel ── */}
      <div
        className="animate-fade-in"
        style={{
          width: "42%",
          background: "var(--bg-surface)",
          borderRight: "1px solid var(--border-subtle)",
          padding: "48px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
        }}
        aria-hidden="true"
        id="login-brand-panel"
      >
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: "var(--accent-dark)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <BarChart3 size={16} color="#fff" />
          </div>
          <span style={{ fontWeight: 800, fontSize: 16, letterSpacing: "-0.02em" }}>
            Pulse<span style={{ color: "var(--text-accent)" }}>AI</span>
          </span>
        </div>

        {/* Center copy */}
        <div>
          <p className="section-label" style={{ marginBottom: 16 }}>
            Clinical AI Platform
          </p>
          <h2
            style={{
              fontSize: 30,
              fontWeight: 800,
              lineHeight: 1.2,
              letterSpacing: "-0.025em",
              color: "var(--text-primary)",
              marginBottom: 16,
            }}
          >
            Automate Prior<br />Authorization<br />with AI Precision
          </h2>
          <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.7 }}>
            Reduce PA turnaround from days to seconds. Built for hospital workflows in Vietnam and the USA.
          </p>
        </div>

        {/* Trust indicators */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {[
            "HIPAA-compliant PHI de-identification",
            "TT 46/2018 Vietnam regulation",
            "LangGraph multi-agent orchestration",
          ].map((item) => (
            <div
              key={item}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                fontSize: 13,
                color: "var(--text-secondary)",
              }}
            >
              <ShieldCheck size={14} color="var(--accent)" style={{ flexShrink: 0 }} />
              {item}
            </div>
          ))}
        </div>
      </div>

      {/* ── Right login form ── */}
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "24px",
        }}
      >
        <div
          className="animate-scale-in"
          style={{ width: "100%", maxWidth: 400 }}
        >
          <div style={{ marginBottom: 32 }}>
            <h1
              style={{
                fontSize: 24,
                fontWeight: 800,
                letterSpacing: "-0.02em",
                marginBottom: 6,
              }}
            >
              Welcome back
            </h1>
            <p style={{ fontSize: 14, color: "var(--text-secondary)" }}>
              Sign in to the hospital portal
            </p>
          </div>

          {/* Error message */}
          {error && (
            <div
              role="alert"
              style={{
                marginBottom: 20,
                padding: "12px 14px",
                borderRadius: "var(--radius-md)",
                background: "var(--danger-dim)",
                border: "1px solid rgba(239,68,68,0.2)",
                color: "var(--danger)",
                fontSize: 13,
                lineHeight: 1.5,
              }}
            >
              {error}
            </div>
          )}

          <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Email */}
            <div>
              <label
                htmlFor="login-email"
                style={{
                  display: "block",
                  fontSize: 13,
                  fontWeight: 600,
                  color: "var(--text-secondary)",
                  marginBottom: 6,
                }}
              >
                Email address
              </label>
              <div style={{ position: "relative" }}>
                <Mail
                  size={15}
                  color="var(--text-muted)"
                  style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", pointerEvents: "none" }}
                />
                <input
                  id="login-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="doctor@hospital.org"
                  className="field"
                  style={{ paddingLeft: 38, paddingRight: 14, height: 44 }}
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label
                htmlFor="login-password"
                style={{
                  display: "block",
                  fontSize: 13,
                  fontWeight: 600,
                  color: "var(--text-secondary)",
                  marginBottom: 6,
                }}
              >
                Password
              </label>
              <div style={{ position: "relative" }}>
                <Lock
                  size={15}
                  color="var(--text-muted)"
                  style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", pointerEvents: "none" }}
                />
                <input
                  id="login-password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="field"
                  style={{ paddingLeft: 38, paddingRight: 14, height: 44 }}
                />
              </div>
            </div>

            {/* Submit */}
            <button
              id="login-submit-btn"
              type="submit"
              disabled={loading}
              className="btn btn-primary"
              style={{ width: "100%", height: 48, fontSize: 15, marginTop: 4 }}
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Signing in...
                </>
              ) : (
                "Sign In"
              )}
            </button>
          </form>

          {/* Footer note */}
          <p
            style={{
              marginTop: 24,
              fontSize: 12,
              color: "var(--text-muted)",
              textAlign: "center",
              lineHeight: 1.6,
            }}
          >
            <ShieldCheck size={11} style={{ display: "inline", marginRight: 4 }} />
            Secured with TLS 1.3 · HIPAA compliant session handling
          </p>
        </div>
      </div>
    </div>
  );
}
