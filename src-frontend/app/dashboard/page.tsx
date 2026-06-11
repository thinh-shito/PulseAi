"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Plus,
  RefreshCw,
  Eye,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  Search,
  FileText,
} from "lucide-react";
import Navbar from "@/components/Navbar";

interface Workflow {
  id: string;
  patient_id: string;
  created_by: string;
  status: string;
  quality_score?: number;
  payer_type?: string;
  created_at: string;
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string; icon: React.ReactNode }> = {
    approved:  { label: "Approved",  cls: "badge badge-success", icon: <CheckCircle2 size={10} /> },
    completed: { label: "Completed", cls: "badge badge-success", icon: <CheckCircle2 size={10} /> },
    rejected:  { label: "Rejected",  cls: "badge badge-danger",  icon: <XCircle size={10} /> },
    failed:    { label: "Failed",    cls: "badge badge-danger",  icon: <AlertTriangle size={10} /> },
    awaiting_approval: {
      label: "Needs Review",
      cls: "badge badge-warning",
      icon: <AlertTriangle size={10} />,
    },
  };

  const cfg = map[status] ?? {
    label: status,
    cls: "badge badge-neutral",
    icon: <Clock size={10} />,
  };

  return (
    <span className={cfg.cls}>
      {cfg.icon}
      {cfg.label}
    </span>
  );
}

function QualityScore({ score }: { score?: number | null }) {
  if (score == null) return <span style={{ color: "var(--text-muted)", fontSize: 13 }}>—</span>;
  const cls = score >= 95 ? "score-high" : score >= 75 ? "score-mid" : "score-low";
  return (
    <span className={cls} style={{ fontWeight: 700, fontSize: 14, fontVariantNumeric: "tabular-nums" }}>
      {score.toFixed(1)}
      <span style={{ fontSize: 11, fontWeight: 500, marginLeft: 1 }}>%</span>
    </span>
  );
}

export default function DashboardPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const router = useRouter();

  const fetchWorkflows = async () => {
    setError("");
    const token = localStorage.getItem("token");
    if (!token) { router.push("/login"); return; }

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/v1/workflow/`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 401) { localStorage.clear(); router.push("/login"); return; }
      if (!res.ok) throw new Error("Failed to load workflows");

      setWorkflows(await res.json());
    } catch (err: any) {
      setError(err.message || "Failed to load workflows");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkflows();
    const interval = setInterval(fetchWorkflows, 10000);
    return () => clearInterval(interval);
  }, []);

  const filtered = workflows.filter((w) =>
    w.patient_id.toLowerCase().includes(search.toLowerCase())
  );

  const stats = {
    total:    workflows.length,
    approved: workflows.filter((w) => ["approved", "completed"].includes(w.status)).length,
    pending:  workflows.filter((w) => w.status === "awaiting_approval").length,
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-base)" }}>
      <Navbar />

      <main
        style={{
          maxWidth: 1280,
          margin: "0 auto",
          padding: "32px 24px 48px",
        }}
      >
        {/* ── Page header ── */}
        <div
          className="animate-fade-in"
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 16,
            marginBottom: 28,
          }}
        >
          <div>
            <p className="section-label" style={{ marginBottom: 6 }}>Prior Authorization</p>
            <h1
              style={{
                fontSize: 26,
                fontWeight: 800,
                letterSpacing: "-0.02em",
                color: "var(--text-primary)",
              }}
            >
              Cases Dashboard
            </h1>
          </div>

          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button
              id="dashboard-refresh-btn"
              onClick={fetchWorkflows}
              className="btn-icon"
              title="Refresh"
              aria-label="Refresh cases"
            >
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            </button>
            <Link
              href="/workflow/new"
              id="dashboard-new-case-btn"
              className="btn btn-primary"
            >
              <Plus size={15} />
              Submit Case
            </Link>
          </div>
        </div>

        {/* ── Stat row ── */}
        <div
          className="animate-fade-in delay-100"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 12,
            marginBottom: 24,
          }}
        >
          {[
            { label: "Total Cases",    value: stats.total,    color: "var(--text-accent)" },
            { label: "Approved",        value: stats.approved, color: "var(--success)" },
            { label: "Needs Review",    value: stats.pending,  color: "var(--warning)" },
          ].map((s) => (
            <div
              key={s.label}
              className="panel"
              style={{ padding: "18px 20px", display: "flex", flexDirection: "column", gap: 4 }}
            >
              <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                {s.label}
              </span>
              <span style={{ fontSize: 28, fontWeight: 800, color: s.color, letterSpacing: "-0.02em", lineHeight: 1 }}>
                {s.value}
              </span>
            </div>
          ))}
        </div>

        {/* ── Error ── */}
        {error && (
          <div
            role="alert"
            style={{
              marginBottom: 16,
              padding: "12px 14px",
              borderRadius: "var(--radius-md)",
              background: "var(--danger-dim)",
              border: "1px solid rgba(239,68,68,0.2)",
              color: "var(--danger)",
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}

        {/* ── Search ── */}
        <div
          className="animate-fade-in delay-150"
          style={{ position: "relative", marginBottom: 16, maxWidth: 360 }}
        >
          <Search
            size={14}
            color="var(--text-muted)"
            style={{
              position: "absolute",
              left: 12,
              top: "50%",
              transform: "translateY(-50%)",
              pointerEvents: "none",
            }}
          />
          <input
            id="dashboard-search-input"
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by Patient ID..."
            className="field"
            style={{ paddingLeft: 36, paddingRight: 14, height: 38, fontSize: 13 }}
          />
        </div>

        {/* ── Table ── */}
        <div
          className="panel animate-fade-in delay-200"
          style={{ overflow: "hidden" }}
        >
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Patient ID</th>
                  <th>Payer</th>
                  <th>Quality</th>
                  <th>Status</th>
                  <th>Date</th>
                  <th style={{ textAlign: "right" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td
                      colSpan={6}
                      style={{
                        padding: "48px 24px",
                        textAlign: "center",
                        color: "var(--text-muted)",
                      }}
                    >
                      {loading ? (
                        <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                          <RefreshCw size={14} className="animate-spin" />
                          Loading cases...
                        </span>
                      ) : (
                        <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                          <FileText size={16} />
                          No cases found
                        </span>
                      )}
                    </td>
                  </tr>
                ) : (
                  filtered.map((w) => (
                    <tr key={w.id}>
                      <td>
                        <span
                          style={{
                            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                            fontSize: 12,
                            color: "var(--text-accent)",
                            letterSpacing: "0.02em",
                          }}
                        >
                          {w.patient_id.slice(0, 8)}…
                        </span>
                      </td>
                      <td>
                        <span style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)" }}>
                          {w.payer_type ?? "—"}
                        </span>
                      </td>
                      <td>
                        <QualityScore score={w.quality_score} />
                      </td>
                      <td>
                        <StatusBadge status={w.status} />
                      </td>
                      <td>
                        <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                          {new Date(w.created_at).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                          })}
                        </span>
                      </td>
                      <td style={{ textAlign: "right" }}>
                        <Link
                          href={`/workflow/${w.id}`}
                          id={`workflow-view-${w.id}`}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 5,
                            padding: "5px 10px",
                            borderRadius: "var(--radius-sm)",
                            background: "var(--accent-dim)",
                            border: "1px solid rgba(20,184,166,0.15)",
                            color: "var(--text-accent)",
                            fontSize: 12,
                            fontWeight: 600,
                            textDecoration: "none",
                            transition: "background 150ms",
                          }}
                          onMouseEnter={(e) => {
                            (e.currentTarget as HTMLAnchorElement).style.background = "rgba(20,184,166,0.2)";
                          }}
                          onMouseLeave={(e) => {
                            (e.currentTarget as HTMLAnchorElement).style.background = "var(--accent-dim)";
                          }}
                        >
                          <Eye size={12} />
                          View
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
