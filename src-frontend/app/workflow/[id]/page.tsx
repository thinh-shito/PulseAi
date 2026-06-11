"use client";

import { useEffect, useState, useRef, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Loader2, CheckCircle, AlertTriangle, ShieldCheck, FileText, Check, X, XCircle, Pencil, Download } from "lucide-react";
import Link from "next/link";
import Navbar from "@/components/Navbar";

interface WorkflowDetails {
  id: string;
  patient_id: string;
  status: string;
  quality_score?: number;
  payer_type?: string;
  result_data?: {
    template: string;
    carrier: string;
    fields: Record<string, string>;
  };
}

export default function WorkflowDetailPage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();
  
  const [workflow, setWorkflow] = useState<WorkflowDetails | null>(null);
  const [pipelineLogs, setPipelineLogs] = useState<string[]>([]);
  const [sseActive, setSseActive] = useState(false);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  
  const [editedFields, setEditedFields] = useState<Record<string, string>>({});
  const [editingFieldKey, setEditingFieldKey] = useState<string | null>(null);

  const fetchDetails = async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/v1/workflow/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error("Workflow not found");
      const data = await res.json();
      setWorkflow(data);

      // If status is still active (pending, processing, etc.), start SSE
      if (["pending", "processing"].includes(data.status)) {
        startSseStream();
      }
    } catch (err: any) {
      setError(err.message || "Failed to load case details");
    }
  };

  const startSseStream = () => {
    if (eventSourceRef.current) return;
    setSseActive(true);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const token = localStorage.getItem("token");
    const es = new EventSource(`${API_URL}/api/v1/workflow/${id}/stream${token ? `?token=${token}` : ""}`);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.status === "done") {
          es.close();
          eventSourceRef.current = null;
          setSseActive(false);
          fetchDetails();
          return;
        }

        // Add log entry based on status update
        const logMsg = `[${new Date().toLocaleTimeString()}] Status updated to: ${data.status.replace("_", " ")}`;
        setPipelineLogs((prev) => [...prev, logMsg]);

        // Update local workflow state
        setWorkflow((prev) => {
          if (!prev) return null;
          return {
            ...prev,
            status: data.status,
            payer_type: data.payer_type || prev.payer_type,
            quality_score: data.quality_score !== undefined ? data.quality_score : prev.quality_score,
            result_data: data.prior_auth_form || prev.result_data,
          };
        });
      } catch (err) {
        console.error("Failed to parse SSE event", err);
      }
    };

    es.onerror = () => {
      es.close();
      eventSourceRef.current = null;
      setSseActive(false);
    };
  };

  useEffect(() => {
    const fields = workflow?.result_data?.fields;
    if (fields) {
      setEditedFields(fields);
    }
  }, [workflow?.id, workflow?.result_data?.fields]);

  const hasPendingChanges = useMemo(() => {
    const fields = workflow?.result_data?.fields;
    if (!fields) return false;
    return Object.keys(fields).some(
      (key) => editedFields[key] !== fields[key]
    );
  }, [workflow?.result_data?.fields, editedFields]);

  const handleSaveChanges = async () => {
    setActionLoading(true);
    setError("");
    const token = localStorage.getItem("token");

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/v1/workflow/${id}/fields`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ fields: editedFields }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to save field changes");
      }

      await fetchDetails();
    } catch (err: any) {
      setError(err.message || "Failed to save field changes");
    } finally {
      setActionLoading(false);
    }
  };

  const handleExportPDF = async () => {
    setActionLoading(true);
    setError("");
    const token = localStorage.getItem("token");

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/v1/workflow/${id}/export-pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        throw new Error("Failed to export PDF");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `prior_auth_${id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message || "Failed to export PDF");
    } finally {
      setActionLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [id]);

  const handleAction = async (action: "approve" | "reject") => {
    setActionLoading(true);
    setError("");
    const token = localStorage.getItem("token");

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/v1/workflow/${id}/${action}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Failed to ${action} claim`);
      }

      fetchDetails();
    } catch (err: any) {
      setError(err.message || `Failed to ${action} claim`);
    } finally {
      setActionLoading(false);
    }
  };

  if (error && !workflow) {
    return (
      <div className="min-h-screen bg-[#080b11]">
        <Navbar />
        <div className="max-w-3xl mx-auto px-8 py-20 text-center">
          <AlertTriangle className="h-12 w-12 text-rose-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold">{error}</h2>
          <Link href="/dashboard" className="text-sky-400 hover:underline mt-4 inline-block">
            Go back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  if (!workflow) {
    return (
      <div className="min-h-screen bg-[#080b11] flex items-center justify-center">
        <Loader2 className="h-8 w-8 text-sky-400 animate-spin" />
      </div>
    );
  }

  const role = typeof window !== "undefined" ? localStorage.getItem("role") : "";

  return (
    <div className="min-h-screen bg-[#080b11]">
      <Navbar />

      <main className="max-w-7xl mx-auto px-8 py-10">
        <Link
          href="/dashboard"
          className="inline-flex items-center space-x-2 text-sm text-gray-400 hover:text-white mb-6 transition-all"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Dashboard</span>
        </Link>

        {/* Case Title */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-3xl font-extrabold tracking-wide">Case Detail</h1>
              {sseActive && (
                <span className="flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20 glow-active">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  <span>Agent Running</span>
                </span>
              )}
            </div>
            <p className="text-xs font-mono text-gray-500 mt-1">ID: {workflow.id}</p>
          </div>
          
          <div className="text-right">
            <p className="text-sm text-gray-400">Patient Identifier</p>
            <p className="text-lg font-bold font-mono text-sky-400">{workflow.patient_id}</p>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 text-sm bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-lg">
            {error}
          </div>
        )}

        {/* Pipeline Progress Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
          {/* Progress Steps Card */}
          <div className="glass-card p-6 rounded-2xl lg:col-span-2">
            <h2 className="text-xl font-bold mb-6 flex items-center space-x-2">
              <ShieldCheck className="h-5 w-5 text-sky-400" />
              <span>Prior Auth Pipeline Execution</span>
            </h2>

            <div className="space-y-6">
              {/* Step 1 */}
              <div className="flex items-start space-x-4">
                <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${
                  ["pending", "processing"].includes(workflow.status)
                    ? "bg-sky-500 text-white animate-pulse"
                    : "bg-emerald-500/20 text-emerald-400"
                }`}>
                  1
                </div>
                <div>
                  <h3 className="font-semibold text-sm">Clinical De-identification & Extraction</h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Scrubbing PII using deterministic rules and extracting codes via Clinical LLM Node.
                  </p>
                </div>
              </div>

              {/* Step 2 */}
              <div className="flex items-start space-x-4">
                <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${
                  workflow.payer_type ? "bg-emerald-500/20 text-emerald-400" : "bg-gray-800 text-gray-500"
                }`}>
                  2
                </div>
                <div>
                  <h3 className="font-semibold text-sm">Insurance Payer Routing</h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Analyzing extraction results to route the claim to correct insurer carrier node.
                    {workflow.payer_type && (
                      <span className="block text-sky-400 font-bold mt-1">Routed Payer: {workflow.payer_type}</span>
                    )}
                  </p>
                </div>
              </div>

              {/* Step 3 */}
              <div className="flex items-start space-x-4">
                <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${
                  workflow.result_data ? "bg-emerald-500/20 text-emerald-400" : "bg-gray-800 text-gray-500"
                }`}>
                  3
                </div>
                <div>
                  <h3 className="font-semibold text-sm">Prior Authorization Form Filling</h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Auto-filling required insurer template parameters based on extracted details.
                  </p>
                </div>
              </div>

              {/* Step 4 */}
              <div className="flex items-start space-x-4">
                <div className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${
                  (workflow.quality_score !== undefined && workflow.quality_score !== null) ? "bg-emerald-500/20 text-emerald-400" : "bg-gray-800 text-gray-500"
                }`}>
                  4
                </div>
                <div>
                  <h3 className="font-semibold text-sm">Quality Gate Scoring</h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Validating form parameters and checking confidence thresholds (Gate limit: 95%).
                    {workflow.quality_score !== undefined && workflow.quality_score !== null && (
                      <span className={`block font-bold mt-1 ${workflow.quality_score >= 95 ? "text-emerald-400" : "text-amber-400"}`}>
                        Quality Score: {workflow.quality_score.toFixed(1)}% (Threshold: 95.0%)
                      </span>
                    )}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Logs / Stream Box */}
          <div className="glass-card p-6 rounded-2xl flex flex-col h-[320px] lg:h-auto">
            <h2 className="text-lg font-bold mb-4">Pipeline Live Logs</h2>
            <div className="flex-1 bg-black/40 border border-gray-800 rounded-xl p-4 font-mono text-xs overflow-y-auto space-y-2 text-gray-400">
              {pipelineLogs.length === 0 ? (
                <p className="text-gray-600">Waiting for logs...</p>
              ) : (
                pipelineLogs.map((log, index) => (
                  <p key={index} className="text-sky-400/80">{log}</p>
                ))
              )}
              {sseActive && <p className="text-gray-500 animate-pulse">Running next graph edge...</p>}
            </div>
          </div>
        </div>

        {/* Form Details & Review Action Box */}
        {workflow.result_data && (
          <div className="glass-card p-8 rounded-3xl space-y-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-6 border-b border-gray-850">
              <div className="flex items-center space-x-3">
                <FileText className="h-6 w-6 text-sky-400" />
                <div>
                  <h2 className="text-xl font-bold">Extracted Claim Form Details</h2>
                  <p className="text-xs text-gray-400">Insurer Template: {workflow.result_data.template}</p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                {workflow.result_data && (
                  <button
                    disabled={actionLoading}
                    onClick={handleExportPDF}
                    className="flex items-center space-x-2 px-5 py-2.5 bg-teal-500/10 hover:bg-teal-500/20 border border-teal-500/30 text-teal-400 font-semibold rounded-xl transition-all text-sm"
                  >
                    <Download className="h-4 w-4" />
                    <span>Export PDF</span>
                  </button>
                )}

                {hasPendingChanges && (
                  <button
                    disabled={actionLoading}
                    onClick={handleSaveChanges}
                    className="flex items-center space-x-2 px-5 py-2.5 bg-sky-500 hover:bg-sky-600 text-white font-semibold rounded-xl transition-all text-sm shadow-lg shadow-sky-500/10 hover:shadow-sky-500/20"
                  >
                    {actionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                    <span>Save Changes</span>
                  </button>
                )}

                {workflow.status === "awaiting_approval" && (role === "doctor" || role === "admin") && (
                  <>
                    <button
                      disabled={actionLoading}
                      onClick={() => handleAction("reject")}
                      className="flex items-center space-x-2 px-5 py-2.5 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-400 font-semibold rounded-xl transition-all text-sm"
                    >
                      <X className="h-4 w-4" />
                      <span>Reject Request</span>
                    </button>
                    <button
                      disabled={actionLoading}
                      onClick={() => handleAction("approve")}
                      className="flex items-center space-x-2 px-5 py-2.5 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 font-semibold rounded-xl transition-all text-sm glow-active"
                    >
                      <Check className="h-4 w-4" />
                      <span>Approve Claim</span>
                    </button>
                  </>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Form parameters */}
              <div>
                <h3 className="font-semibold text-gray-400 text-xs tracking-wider uppercase mb-4">Extracted Fields</h3>
                <div className="space-y-4">
                  {Object.entries(editedFields).map(([key, val]) => (
                    <div key={key} className="p-4 bg-[#0d131f] border border-gray-850 rounded-xl group relative">
                      <p className="text-xs text-gray-500 capitalize">{key.replace("_", " ")}</p>
                      {editingFieldKey === key ? (
                        <div className="flex items-center space-x-2 mt-1">
                          <input
                            type="text"
                            value={val || ""}
                            onChange={(e) => setEditedFields(prev => ({ ...prev, [key]: e.target.value }))}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                setEditingFieldKey(null);
                              } else if (e.key === "Escape") {
                                setEditedFields(prev => ({ ...prev, [key]: workflow.result_data!.fields[key] }));
                                setEditingFieldKey(null);
                              }
                            }}
                            className="flex-1 bg-[#060d1f] border border-gray-700 rounded px-2 py-1 text-sm text-gray-200 focus:outline-none focus:border-sky-500 font-sans"
                            autoFocus
                          />
                          <button
                            type="button"
                            onClick={() => setEditingFieldKey(null)}
                            className="text-emerald-400 hover:text-emerald-300 p-1"
                          >
                            <Check className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setEditedFields(prev => ({ ...prev, [key]: workflow.result_data!.fields[key] }));
                              setEditingFieldKey(null);
                            }}
                            className="text-rose-400 hover:text-rose-300 p-1"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex justify-between items-start mt-1">
                          <p className="text-sm font-semibold text-gray-200">{val || "N/A"}</p>
                          <button
                            type="button"
                            onClick={() => setEditingFieldKey(key)}
                            className="opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 focus:opacity-100 transition-opacity text-gray-500 hover:text-sky-400 p-1"
                            title="Edit field"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Status report */}
              <div className="p-6 bg-[#0d131f] border border-gray-850 rounded-2xl flex flex-col justify-center items-center text-center space-y-4">
                {workflow.status === "approved" ? (
                  <>
                    <CheckCircle className="h-16 w-16 text-emerald-400" />
                    <h3 className="text-xl font-bold text-emerald-400">Claim Approved</h3>
                    <p className="text-sm text-gray-400 max-w-sm">
                      Prior authorization has been successfully approved and transmitted to the insurer database.
                    </p>
                  </>
                ) : workflow.status === "rejected" ? (
                  <>
                    <XCircle className="h-16 w-16 text-rose-400" />
                    <h3 className="text-xl font-bold text-rose-400">Claim Rejected</h3>
                    <p className="text-sm text-gray-400 max-w-sm">
                      This claim was rejected by medical billing auditor due to validation errors.
                    </p>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="h-16 w-16 text-amber-400 animate-bounce" />
                    <h3 className="text-xl font-bold text-amber-400">Awaiting Auditor Review</h3>
                    <p className="text-sm text-gray-400 max-w-sm">
                      The extraction score fell below 95%. Clinician signature is required to authorize this claim.
                    </p>
                  </>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
