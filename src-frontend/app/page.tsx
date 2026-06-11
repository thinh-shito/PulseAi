"use client";

import Link from "next/link";
import { ShieldCheck, Zap, Users, ChevronRight, Lock, BarChart3 } from "lucide-react";

const FEATURES = [
  {
    icon: ShieldCheck,
    title: "HIPAA & TT46 Compliant",
    description:
      "Deterministic PHI de-identification with Presidio before any external LLM call. Audit trail on every action.",
    accent: "var(--success)",
  },
  {
    icon: Zap,
    title: "LangGraph AI Pipeline",
    description:
      "Multi-node orchestration: clinical extraction → payer routing → form fill → quality gate — in seconds.",
    accent: "var(--accent)",
  },
  {
    icon: Users,
    title: "Clinician Review Gate",
    description:
      "Cases scoring below 95 are flagged for physician sign-off. No claim leaves without human verification.",
    accent: "var(--info)",
  },
];

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen">

      {/* ── Header ── */}
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 50,
          background: "rgba(6, 13, 31, 0.85)",
          backdropFilter: "blur(20px)",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div
          style={{
            maxWidth: 1100,
            margin: "0 auto",
            padding: "0 24px",
            height: 60,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
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
            <span
              style={{
                fontWeight: 800,
                fontSize: 16,
                letterSpacing: "-0.02em",
                color: "var(--text-primary)",
              }}
            >
              Pulse<span style={{ color: "var(--text-accent)" }}>AI</span>
            </span>
          </div>

          {/* Trust chips + CTA */}
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span className="trust-chip" style={{ display: "none" }} id="hipaa-chip">
              <Lock size={10} />
              HIPAA
            </span>
            <Link href="/login" className="btn btn-primary" style={{ height: 36, fontSize: 13 }}>
              Sign In
              <ChevronRight size={14} />
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ── */}
      <main style={{ flex: 1 }}>
        <section
          style={{
            maxWidth: 900,
            margin: "0 auto",
            padding: "96px 24px 80px",
            textAlign: "center",
          }}
        >
          {/* Compliance banner */}
          <div
            className="animate-fade-in"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 16,
              marginBottom: 36,
              padding: "6px 16px",
              borderRadius: 999,
              background: "rgba(20,184,166,0.06)",
              border: "1px solid rgba(20,184,166,0.15)",
            }}
          >
            <span className="trust-chip" style={{ padding: 0, background: "none", border: "none" }}>
              <Lock size={10} />
              HIPAA
            </span>
            <span
              style={{
                width: 1,
                height: 12,
                background: "var(--border-default)",
              }}
            />
            <span style={{ fontSize: 12, color: "var(--text-secondary)", fontWeight: 500 }}>
              TT 46/2018 · Vietnam & USA
            </span>
          </div>

          <h1
            className="animate-fade-in delay-100"
            style={{
              fontSize: "clamp(38px, 6vw, 64px)",
              fontWeight: 800,
              lineHeight: 1.1,
              letterSpacing: "-0.03em",
              color: "var(--text-primary)",
              marginBottom: 24,
            }}
          >
            Prior Authorization,{" "}
            <span style={{ color: "var(--text-accent)" }}>
              Automated.
            </span>
          </h1>

          <p
            className="animate-fade-in delay-150"
            style={{
              fontSize: 18,
              color: "var(--text-secondary)",
              lineHeight: 1.7,
              maxWidth: 560,
              margin: "0 auto 40px",
            }}
          >
            AI pipeline that extracts ICD-10 codes, resolves payers, and submits
            prior auth claims — with full HIPAA compliance and physician oversight.
          </p>

          <div
            className="animate-fade-in delay-200"
            style={{ display: "flex", justifyContent: "center", gap: 12 }}
          >
            <Link href="/login" className="btn btn-primary" style={{ height: 48, fontSize: 15, padding: "0 28px" }}>
              Access Hospital Portal
              <ChevronRight size={16} />
            </Link>
          </div>

          {/* Stats row */}
          <div
            className="animate-fade-in delay-300"
            style={{
              display: "flex",
              justifyContent: "center",
              gap: 48,
              marginTop: 64,
              padding: "32px 0",
              borderTop: "1px solid var(--border-subtle)",
            }}
          >
            {[
              { value: "<3s", label: "Avg. PA submission" },
              { value: "99.2%", label: "PHI de-id accuracy" },
              { value: "ISO 27001", label: "Security certified" },
            ].map((stat) => (
              <div key={stat.label} style={{ textAlign: "center" }}>
                <div
                  style={{
                    fontSize: 26,
                    fontWeight: 800,
                    color: "var(--text-accent)",
                    letterSpacing: "-0.02em",
                    lineHeight: 1,
                    marginBottom: 6,
                  }}
                >
                  {stat.value}
                </div>
                <div style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 500 }}>
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── Feature Cards ── */}
        <section
          style={{
            maxWidth: 1100,
            margin: "0 auto",
            padding: "0 24px 96px",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: 16,
            }}
          >
            {FEATURES.map((f, i) => (
              <div
                key={f.title}
                className={`panel panel-hover animate-fade-in delay-${(i + 1) * 100}`}
                style={{ padding: 28 }}
              >
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 10,
                    background: `${f.accent}14`,
                    border: `1px solid ${f.accent}28`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginBottom: 16,
                  }}
                >
                  <f.icon size={18} color={f.accent} />
                </div>
                <h3
                  style={{
                    fontSize: 15,
                    fontWeight: 700,
                    color: "var(--text-primary)",
                    marginBottom: 8,
                  }}
                >
                  {f.title}
                </h3>
                <p style={{ fontSize: 13.5, color: "var(--text-secondary)", lineHeight: 1.65 }}>
                  {f.description}
                </p>
              </div>
            ))}
          </div>
        </section>
      </main>

      {/* ── Footer ── */}
      <footer
        style={{
          borderTop: "1px solid var(--border-subtle)",
          padding: "20px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
          © {new Date().getFullYear()} PulseAI Inc.
        </span>
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <span className="trust-chip">
            <Lock size={10} />
            HIPAA Compliant
          </span>
          <span className="trust-chip">
            <ShieldCheck size={10} />
            TT 46/2018
          </span>
        </div>
      </footer>
    </div>
  );
}
