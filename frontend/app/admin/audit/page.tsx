"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";
import Navbar from "@/components/Navbar";

interface AuditLog {
  id: string;
  user_id: string;
  action: string;
  patient_id?: string;
  workflow_id?: string;
  resource_type?: string;
  resource_id?: string;
  ip_address?: string;
  created_at: string;
}

export default function AdminAuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const router = useRouter();

  const fetchLogs = async () => {
    setError("");
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/v1/admin/audit-logs`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 403) {
        throw new Error("Access denied. Admin role required.");
      }

      if (!res.ok) throw new Error("Failed to load audit logs");
      const data = await res.json();
      setLogs(data);
    } catch (err: any) {
      setError(err.message || "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <div className="min-h-screen bg-[#080b11]">
      <Navbar />

      <main className="max-w-7xl mx-auto px-8 py-10">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-extrabold tracking-wide">HIPAA Audit Logs</h1>
            <p className="text-sm text-gray-400 mt-1">Immutable audit trail of all clinical data operations</p>
          </div>
          <button
            onClick={fetchLogs}
            className="flex h-11 w-11 items-center justify-center rounded-xl bg-gray-900 border border-gray-800 text-gray-400 hover:text-white transition-all"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 text-sm bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-lg">
            {error}
          </div>
        )}

        {/* Audit list table */}
        <div className="glass-card rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-gray-800/80 bg-gray-900/30 text-xs font-semibold tracking-wider text-gray-400 uppercase">
                  <th className="px-6 py-4">Timestamp</th>
                  <th className="px-6 py-4">User ID</th>
                  <th className="px-6 py-4">Action</th>
                  <th className="px-6 py-4">Patient ID</th>
                  <th className="px-6 py-4">Resource</th>
                  <th className="px-6 py-4">IP Address</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/50 text-xs font-mono">
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-10 text-center text-gray-500 font-sans text-sm">
                      {loading ? "Loading audit logs..." : "No logs recorded"}
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-800/10 transition-colors">
                      <td className="px-6 py-4 text-gray-400">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-sky-400/80">{log.user_id}</td>
                      <td className="px-6 py-4">
                        <span className="px-2 py-0.5 rounded bg-gray-800 border border-gray-700 text-gray-200 capitalize font-sans text-[11px] font-semibold">
                          {log.action}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sky-400/80">{log.patient_id || "N/A"}</td>
                      <td className="px-6 py-4 text-gray-300 font-sans">
                        {log.resource_type ? `${log.resource_type} (${log.resource_id})` : "N/A"}
                      </td>
                      <td className="px-6 py-4 text-gray-500">{log.ip_address || "N/A"}</td>
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
