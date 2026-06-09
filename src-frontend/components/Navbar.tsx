"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Activity, LogOut, Users } from "lucide-react";

export default function Navbar() {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("");
  const [onlineCount, setOnlineCount] = useState<number | null>(null);
  const router = useRouter();

  useEffect(() => {
    const storedEmail = localStorage.getItem("email") || "";
    setEmail(storedEmail);
    setRole(localStorage.getItem("role") || "");

    const token = localStorage.getItem("token");
    if (!token) return;

    // Connect to Real-time Presence SSE stream
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const eventSource = new EventSource(`${API_URL}/api/v1/presence/stream?token=${token}&interval=10`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (typeof data.online_users === "number") {
          setOnlineCount(data.online_users);
        }
      } catch (err) {
        console.error("Error parsing presence stream data:", err);
      }
    };

    eventSource.onerror = (err) => {
      console.error("Presence EventSource failed:", err);
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const handleLogout = async () => {
    const token = localStorage.getItem("token");
    if (token) {
      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        await fetch(`${API_URL}/api/v1/presence/offline`, {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
      } catch (err) {
        console.error("Failed to mark offline on logout:", err);
      }
    }
    localStorage.clear();
    router.push("/login");
  };

  return (
    <nav className="flex justify-between items-center px-8 py-4 border-b border-[var(--border)] bg-[#0d1321]/80 backdrop-blur-md sticky top-0 z-50">
      <div className="flex items-center space-x-6">
        <Link href="/dashboard" className="flex items-center space-x-2">
          <Activity className="h-6 w-6 text-sky-400" />
          <span className="font-bold text-lg tracking-wide bg-gradient-to-r from-sky-400 to-teal-400 bg-clip-text text-transparent">
            PulseAI Portal
          </span>
        </Link>
        
        {/* Real-time Presence Counter */}
        <div className="flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-sm shadow-emerald-500/5">
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
          </span>
          <span>{onlineCount !== null ? `${onlineCount} Online` : "Connecting..."}</span>
        </div>

        <div className="hidden md:flex space-x-4 text-sm font-medium text-gray-300">
          <Link href="/dashboard" className="hover:text-white transition-all">Dashboard</Link>
          <Link href="/workflow/new" className="hover:text-white transition-all">New Case</Link>
          {role === "admin" && (
            <>
              <Link href="/admin/users" className="hover:text-white transition-all">Users</Link>
              <Link href="/admin/audit" className="hover:text-white transition-all">Audit Logs</Link>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="text-right hidden sm:block">
          <p className="text-xs text-gray-500 capitalize">{role}</p>
          <div className="flex items-center space-x-2 justify-end">
            {/* Live user dot */}
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-500"></span>
            </span>
            <p className="text-sm font-medium text-gray-300">{email}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="flex h-10 w-10 items-center justify-center rounded-xl bg-gray-900 hover:bg-gray-800 border border-gray-800 text-gray-400 hover:text-white transition-all"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </nav>
  );
}
