"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FileUp, Loader2, RefreshCw, Trash2, Check, X, FileText, ToggleLeft, ToggleRight, Pencil } from "lucide-react";
import Navbar from "@/components/Navbar";

interface Template {
  id: string;
  name: string;
  fields: string[];
  is_active: boolean;
}

export default function AdminTemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [toggleLoadingId, setToggleLoadingId] = useState<string | null>(null);
  const [editingTemplateId, setEditingTemplateId] = useState<string | null>(null);
  const [editingTemplateName, setEditingTemplateName] = useState<string>("");
  const [editLoadingId, setEditLoadingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const router = useRouter();

  // Upload Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [schemaText, setSchemaText] = useState(
    JSON.stringify(
      {
        name: "New Insurance Form",
        fields: ["diagnosis_code", "procedure_code", "prior_treatments", "clinical_notes"],
      },
      null,
      2
    )
  );
  const [schemaError, setSchemaError] = useState("");

  const fetchTemplates = async () => {
    setError("");
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");

    if (!token) {
      router.push("/login");
      return;
    }

    if (role !== "admin") {
      router.push("/dashboard");
      return;
    }

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      // Fetch all templates including inactive ones for admin view
      const res = await fetch(`${API_URL}/api/v1/templates?all=true`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 403) {
        throw new Error("Access denied. Admin role required.");
      }

      if (!res.ok) throw new Error("Failed to load templates");
      const data = await res.json();
      setTemplates(data);
    } catch (err: any) {
      setError(err.message || "Failed to load templates");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  const handleToggleActive = async (templateId: string, currentStatus: boolean) => {
    setError("");
    setSuccess("");
    setToggleLoadingId(templateId);

    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/v1/admin/templates/${templateId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ is_active: !currentStatus }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to update template status");
      }

      setSuccess(`Template status updated successfully.`);
      fetchTemplates();
    } catch (err: any) {
      setError(err.message || "Failed to update template status");
    } finally {
      setToggleLoadingId(null);
    }
  };

  const handleSaveName = async (templateId: string) => {
    if (!editingTemplateName.trim()) return;
    setError("");
    setSuccess("");
    setEditLoadingId(templateId);

    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/v1/admin/templates/${templateId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name: editingTemplateName.trim() }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to update template name");
      }

      setSuccess("Template name updated successfully.");
      setEditingTemplateId(null);
      fetchTemplates();
    } catch (err: any) {
      setError(err.message || "Failed to update template name");
    } finally {
      setEditLoadingId(null);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === "application/pdf" || droppedFile.name.toLowerCase().endsWith(".pdf")) {
        setFile(droppedFile);
      } else {
        setSchemaError("Only PDF files are supported");
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUploadTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setSchemaError("");

    if (!file) {
      setSchemaError("Please select or drop a PDF template file");
      return;
    }

    // Validate JSON schema
    let parsedSchema;
    try {
      parsedSchema = JSON.parse(schemaText);
      if (!parsedSchema.name || !parsedSchema.fields || !Array.isArray(parsedSchema.fields)) {
        throw new Error("JSON schema must contain a 'name' (string) and 'fields' (array of strings)");
      }
    } catch (err: any) {
      setSchemaError(err.message || "Invalid JSON format. Check fields list.");
      return;
    }

    setUploadLoading(true);
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const formData = new FormData();
      formData.append("file", file);
      formData.append("schema_data", JSON.stringify(parsedSchema));

      const res = await fetch(`${API_URL}/api/v1/admin/templates`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to upload template");
      }

      setSuccess(`Template "${parsedSchema.name}" uploaded successfully!`);
      setIsModalOpen(false);
      setFile(null);
      fetchTemplates();
    } catch (err: any) {
      setError(err.message || "Failed to upload template");
    } finally {
      setUploadLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#080b11]">
      <Navbar />

      <main className="max-w-7xl mx-auto px-8 py-10">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-extrabold tracking-wide">Manage PA Templates</h1>
            <p className="text-sm text-gray-400 mt-1">Upload PDF forms and configure data field mapping schemas</p>
          </div>
          <div className="flex gap-4">
            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-2 h-11 px-5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold shadow-lg hover:shadow-blue-500/10 transition-all text-sm"
            >
              <FileUp className="h-4 w-4" />
              Upload Template
            </button>
            <button
              onClick={fetchTemplates}
              className="flex h-11 w-11 items-center justify-center rounded-xl bg-gray-900 border border-gray-800 text-gray-400 hover:text-white transition-all"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 text-sm bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-lg">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 text-sm bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg">
            {success}
          </div>
        )}

        {/* Template List Table */}
        <div className="glass-card rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-gray-800/80 bg-gray-900/30 text-xs font-semibold tracking-wider text-gray-400 uppercase">
                  <th className="px-6 py-4">Template Name</th>
                  <th className="px-6 py-4">Configured Fields</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/50 text-sm">
                {templates.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-10 text-center text-gray-500">
                      {loading ? "Loading templates..." : "No templates uploaded yet."}
                    </td>
                  </tr>
                ) : (
                  templates.map((tpl) => (
                    <tr key={tpl.id} className="hover:bg-gray-800/10 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg flex-shrink-0">
                            <FileText className="h-4 w-4" />
                          </div>
                          <div className="flex-1 min-w-0">
                            {editingTemplateId === tpl.id ? (
                              <div className="flex items-center gap-2">
                                <input
                                  type="text"
                                  value={editingTemplateName}
                                  onChange={(e) => setEditingTemplateName(e.target.value)}
                                  className="bg-gray-950 border border-gray-800 rounded px-2 py-1 text-sm text-gray-200 focus:outline-none focus:border-blue-500 w-full"
                                  autoFocus
                                  onKeyDown={(e) => {
                                    if (e.key === "Enter") handleSaveName(tpl.id);
                                    if (e.key === "Escape") setEditingTemplateId(null);
                                  }}
                                />
                                <button
                                  type="button"
                                  onClick={() => handleSaveName(tpl.id)}
                                  disabled={editLoadingId === tpl.id}
                                  className="p-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded hover:bg-emerald-500/20 disabled:opacity-50"
                                >
                                  {editLoadingId === tpl.id ? (
                                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                  ) : (
                                    <Check className="h-3.5 w-3.5" />
                                  )}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setEditingTemplateId(null)}
                                  className="p-1 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded hover:bg-rose-500/20"
                                >
                                  <X className="h-3.5 w-3.5" />
                                </button>
                              </div>
                            ) : (
                              <div className="flex items-center gap-2 group">
                                <span className="font-semibold text-gray-200 truncate max-w-[200px]">{tpl.name}</span>
                                <button
                                  type="button"
                                  onClick={() => {
                                    setEditingTemplateId(tpl.id);
                                    setEditingTemplateName(tpl.name);
                                  }}
                                  className="p-1 text-gray-500 hover:text-sky-400 hover:bg-sky-500/10 rounded transition-all opacity-0 group-hover:opacity-100 focus:opacity-100"
                                  title="Edit Template Name"
                                >
                                  <Pencil className="h-3 w-3" />
                                </button>
                              </div>
                            )}
                            <span className="text-xs text-gray-500 font-mono block mt-0.5">{tpl.id}</span>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 max-w-md">
                        <div className="flex flex-wrap gap-1.5">
                          {tpl.fields.map((f, i) => (
                            <span
                              key={i}
                              className="px-2 py-0.5 rounded text-xs bg-gray-900 border border-gray-800 text-gray-400 font-mono"
                            >
                              {f}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase ${
                            tpl.is_active
                              ? "bg-emerald-500/10 text-emerald-400"
                              : "bg-gray-900 text-gray-500 border border-gray-800"
                          }`}
                        >
                          {tpl.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => handleToggleActive(tpl.id, tpl.is_active)}
                          disabled={toggleLoadingId === tpl.id}
                          className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border text-xs font-semibold transition-all ${
                            tpl.is_active
                              ? "bg-rose-500/5 border-rose-500/20 text-rose-400 hover:bg-rose-500/10 hover:border-rose-500/30"
                              : "bg-emerald-500/5 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10 hover:border-emerald-500/30"
                          } disabled:opacity-50`}
                        >
                          {toggleLoadingId === tpl.id ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : tpl.is_active ? (
                            <>
                              <X className="h-3.5 w-3.5" /> Deactivate
                            </>
                          ) : (
                            <>
                              <Check className="h-3.5 w-3.5" /> Activate
                            </>
                          )}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {/* Upload & Config Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-2xl bg-[#0c121f] border border-gray-800 rounded-2xl overflow-hidden shadow-2xl animate-in fade-in zoom-in duration-150">
            <div className="flex justify-between items-center px-6 py-4 border-b border-gray-800">
              <h2 className="text-xl font-bold text-gray-100">Upload & Configure Template</h2>
              <button
                onClick={() => {
                  setIsModalOpen(false);
                  setFile(null);
                  setSchemaError("");
                }}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleUploadTemplate}>
              <div className="p-6 space-y-6">
                {/* Drag-and-drop Zone */}
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-gray-300 block">PDF Template Document</label>
                  <div
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => document.getElementById("file-select")?.click()}
                    className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
                      dragOver
                        ? "border-blue-500 bg-blue-500/5"
                        : file
                        ? "border-emerald-500 bg-emerald-500/5"
                        : "border-gray-800 bg-gray-900/20 hover:border-gray-700"
                    }`}
                  >
                    <input
                      type="file"
                      id="file-select"
                      className="hidden"
                      accept=".pdf,application/pdf"
                      onChange={handleFileChange}
                    />
                    <FileUp
                      className={`mx-auto h-8 w-8 mb-2 ${
                        file ? "text-emerald-400" : "text-gray-500"
                      }`}
                    />
                    {file ? (
                      <div>
                        <p className="text-sm font-semibold text-emerald-400">{file.name}</p>
                        <p className="text-xs text-gray-500 font-mono mt-0.5">{(file.size / 1024).toFixed(1)} KB</p>
                      </div>
                    ) : (
                      <div>
                        <p className="text-sm text-gray-300 font-medium">Drag & drop your blank template PDF here</p>
                        <p className="text-xs text-gray-500 mt-1">or click to browse your local files</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Schema JSON Editor */}
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <label className="text-sm font-semibold text-gray-300">JSON Schema Definition</label>
                    <span className="text-xs text-gray-500">Must map to backend extraction fields</span>
                  </div>
                  <textarea
                    value={schemaText}
                    onChange={(e) => setSchemaText(e.target.value)}
                    rows={7}
                    className="w-full bg-[#080d1a] border border-gray-800 rounded-xl px-4 py-3 text-sm text-gray-300 font-mono focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
                    placeholder={`{\n  "name": "Template Name",\n  "fields": ["field_name"]\n}`}
                  />
                </div>

                {schemaError && (
                  <div className="p-3.5 text-xs bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-lg">
                    {schemaError}
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-3 px-6 py-4 bg-gray-900/40 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => {
                    setIsModalOpen(false);
                    setFile(null);
                    setSchemaError("");
                  }}
                  className="px-4 py-2 border border-gray-800 rounded-xl text-sm font-semibold text-gray-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploadLoading}
                  className="flex items-center gap-2 px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold rounded-xl text-sm transition-all"
                >
                  {uploadLoading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" /> Uploading...
                    </>
                  ) : (
                    "Confirm & Import"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
