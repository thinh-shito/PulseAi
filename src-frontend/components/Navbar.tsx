"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { Activity, LogOut, BarChart3, Plus, ShieldCheck } from "lucide-react";

export default function Navbar() {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("");
  const [onlineCount, setOnlineCount] = useState<number | null>(null);
  const router = useRouter();

  useEffect(() => {
    setEmail(localStorage.getItem("email") || "");
    setRole(localStorage.getItem("role") || "");

    const token = localStorage.getItem("token");
    if (!token) return;

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const eventSource = new EventSource(
      `${API_URL}/api/v1/presence/stream?token=${token}&interval=10`
    );

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (typeof data.online_users === "number") {
          setOnlineCount(data.online_users);
        }
      } catch (err) {
        console.error("Presence stream error:", err);
      }
    };

    eventSource.onerror = () => eventSource.close();
    return () => eventSource.close();
  }, []);

  const handleLogout = async () => {
    const token = localStorage.getItem("token");
    if (token) {
      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        await fetch(`${API_URL}/api/v1/presence/offline`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {}
    }
    localStorage.clear();
    router.push("/login");
  };

  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        background: "rgba(6, 13, 31, 0.9)",
        backdropFilter: "blur(20px)",
        borderBottom: "1px solid var(--border-subtle)",
        height: 60,
        display: "flex",
        alignItems: "center",
        padding: "0 24px",
      }}
    >
      <div
        style={{
          maxWidth: 1280,
          margin: "0 auto",
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 16,
        }}
      >
        {/* ── Left: Logo + Nav ── */}
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          {/* Logo */}
          <Link
            href="/dashboard"
            id="nav-logo"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              textDecoration: "none",
            }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 7,
                background: "var(--accent-dark)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <BarChart3 size={14} color="#fff" />
            </div>
            <span
              style={{
                fontWeight: 800,
                fontSize: 15,
                letterSpacing: "-0.02em",
                color: "var(--text-primary)",
              }}
            >
              Pulse<span style={{ color: "var(--text-accent)" }}>AI</span>
            </span>
          </Link>

          {/* Divider */}
          <div
            style={{
              width: 1,
              height: 18,
              background: "var(--border-default)",
            }}
          />

          {/* Nav links */}
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <NavLink href="/dashboard" id="nav-dashboard">Dashboard</NavLink>
            <NavLink href="/workflow/new" id="nav-new-case">New Case</NavLink>
            {role === "admin" && (
              <>
                <NavLink href="/admin/users" id="nav-users">Users</NavLink>
                <NavLink href="/admin/templates" id="nav-templates">Templates</NavLink>
                <NavLink href="/admin/audit" id="nav-audit">Audit Log</NavLink>
              </>
            )}
          </div>
        </div>

        {/* ── Right: Presence + User ── */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {/* Online count */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "4px 10px",
              borderRadius: 999,
              background: "var(--success-dim)",
              border: "1px solid rgba(16,185,129,0.2)",
              fontSize: 12,
              fontWeight: 600,
              color: "var(--success)",
            }}
          >
            <span className="live-dot" style={{ width: 6, height: 6 }} />
            {onlineCount !== null ? `${onlineCount} online` : "—"}
          </div>

          {/* Role chip */}
          {role && (
            <span
              style={{
                padding: "3px 8px",
                borderRadius: 999,
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-default)",
                fontSize: 11,
                fontWeight: 700,
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              {role}
            </span>
          )}

          {/* Email */}
          <span
            style={{
              fontSize: 13,
              color: "var(--text-secondary)",
              maxWidth: 160,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {email}
          </span>

          {/* Logout */}
          <button
            id="nav-logout-btn"
            onClick={handleLogout}
            className="btn-icon"
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </nav>
  );
}

function NavLink({
  href,
  children,
  id,
}: {
  href: string;
  children: React.ReactNode;
  id?: string;
}) {
  const pathname = usePathname();
  const isActive = pathname === href;

  return (
    <Link
      href={href}
      id={id}
      style={{
        padding: "6px 12px",
        borderRadius: "var(--radius-sm)",
        fontSize: 13,
        fontWeight: 600,
        textDecoration: "none",
        transition: "color 150ms, background 150ms, border-color 150ms",
        border: isActive ? "1px solid rgba(20, 184, 166, 0.2)" : "1px solid transparent",
        color: isActive ? "var(--text-accent)" : "var(--text-secondary)",
        background: isActive ? "var(--accent-dim)" : "transparent",
      }}
      onMouseEnter={(e) => {
        if (!isActive) {
          (e.currentTarget as HTMLAnchorElement).style.color = "var(--text-primary)";
          (e.currentTarget as HTMLAnchorElement).style.background = "var(--bg-elevated)";
        }
      }}
      onMouseLeave={(e) => {
        if (!isActive) {
          (e.currentTarget as HTMLAnchorElement).style.color = "var(--text-secondary)";
          (e.currentTarget as HTMLAnchorElement).style.background = "transparent";
        }
      }}
    >
      {children}
    </Link>
  );
}
