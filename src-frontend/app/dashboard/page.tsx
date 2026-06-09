"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus, RefreshCw, Eye, CheckCircle2, XCircle, Clock, AlertTriangle, Search } from "lucide-react";
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

export default function DashboardPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const router = useRouter();

  const fetchWorkflows = async () => {
    setError("");
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/v1/workflow/`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 401) {
        localStorage.clear();
        router.push("/login");
        return;
      }

      if (!res.ok) {
        throw new Error("Failed to load workflows");
      }

      const data = await res.json();
      setWorkflows(data);
    } catch (err: any) {
      setError(err.message || "Failed to load workflows");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkflows();
    const interval = setInterval(fetchWorkflows, 10000); // refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "approved":
      case "completed":
        return (
          <span className="inline-flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="h-3 w-3" />
            <span className="capitalize">{status}</span>
          </span>
        );
      case "rejected":
        return (
          <span className="inline-flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <XCircle className="h-3 w-3" />
            <span className="capitalize">{status}</span>
          </span>
        );
      case "awaiting_approval":
        return (
          <span className="inline-flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 glow-active">
            <AlertTriangle className="h-3 w-3" />
            <span>Awaiting Approval</span>
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-semibold bg-gray-500/10 text-gray-400 border border-gray-500/20">
            <AlertTriangle className="h-3 w-3" />
            <span>Failed</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-3 py-1 rounded-full text-xs font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20">
            <Clock className="h-3 w-3 animate-pulse" />
            <span className="capitalize">{status}</span>
          </span>
        );
    }
  };

  const filteredWorkflows = workflows.filter((w) =>
    w.patient_id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-[#080b11]">
      <Navbar />

      <main className="max-w-7xl mx-auto px-8 py-10">
        {/* Header Actions */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-extrabold tracking-wide">Cases Dashboard</h1>
            <p className="text-sm text-gray-400 mt-1">Track and manage prior authorization workflows</p>
          </div>
          
          <div className="flex items-center space-x-3 w-full sm:w-auto">
            <button
              onClick={fetchWorkflows}
              className="flex h-11 w-11 items-center justify-center rounded-xl bg-gray-900 border border-gray-800 text-gray-400 hover:text-white transition-all"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </button>
            <Link
              href="/workflow/new"
              className="flex items-center space-x-2 px-5 h-11 bg-gradient-to-r from-sky-500 to-teal-500 hover:from-sky-600 hover:to-teal-600 text-white font-semibold rounded-xl transition-all shadow-lg shadow-sky-500/5 hover:shadow-sky-500/10"
            >
              <Plus className="h-5 w-5" />
              <span>Submit Case</span>
            </Link>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 text-sm bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-lg">
            {error}
          </div>
        )}

        {/* Filter input */}
        <div className="relative mb-6">
          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-500">
            <Search className="h-5 w-5" />
          </span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by Patient ID (UUID)..."
            className="block w-full max-w-md pl-10 pr-4 py-2.5 bg-[#0d131f] border border-gray-800 rounded-xl focus:border-sky-500 focus:ring-1 focus:ring-sky-500 text-white placeholder-gray-600 outline-none transition-all text-sm"
          />
        </div>

        {/* Workflows table */}
        <div className="glass-card rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-gray-800/80 bg-gray-900/30 text-xs font-semibold tracking-wider text-gray-400 uppercase">
                  <th className="px-6 py-4">Patient ID</th>
                  <th className="px-6 py-4">Payer</th>
                  <th className="px-6 py-4">Quality Score</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Date Created</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/50 text-sm">
                {filteredWorkflows.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-10 text-center text-gray-500">
                      {loading ? "Loading cases..." : "No cases found"}
                    </td>
                  </tr>
                ) : (
                  filteredWorkflows.map((w) => (
                    <tr key={w.id} className="hover:bg-gray-800/10 transition-colors">
                      <td className="px-6 py-4 font-medium font-mono text-sky-400/80">{w.patient_id}</td>
                      <td className="px-6 py-4 text-gray-300 font-semibold">{w.payer_type || "N/A"}</td>
                      <td className="px-6 py-4">
                        {w.quality_score !== undefined && w.quality_score !== null ? (
                          <span className={`font-semibold ${w.quality_score >= 95 ? "text-emerald-400" : "text-amber-400"}`}>
                            {w.quality_score.toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-gray-600">N/A</span>
                        )}
                      </td>
                      <td className="px-6 py-4">{getStatusBadge(w.status)}</td>
                      <td className="px-6 py-4 text-gray-400">
                        {new Date(w.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link
                          href={`/workflow/${w.id}`}
                          className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 text-sky-400 font-semibold text-xs transition-all"
                        >
                          <Eye className="h-3.5 w-3.5" />
                          <span>View Detail</span>
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
