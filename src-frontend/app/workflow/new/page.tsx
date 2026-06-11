"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { 
  ArrowLeft, 
  Play, 
  Loader2, 
  Sparkles, 
  Paperclip, 
  FileText, 
  Image, 
  X, 
  Upload, 
  FileType, 
  RefreshCw,
  Trash2,
  CheckCircle,
  AlertCircle
} from "lucide-react";
import Link from "next/link";
import Navbar from "@/components/Navbar";

const ACCEPTED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/msword",
  "text/plain",
  "image/png",
  "image/jpeg",
  "image/jpg",
  "image/gif",
  "image/bmp",
];

const ACCEPTED_EXTENSIONS = [".pdf", ".docx", ".doc", ".txt", ".png", ".jpg", ".jpeg", ".gif", ".bmp"];

function getFileIcon(name: string) {
  const ext = name.split(".").pop()?.toLowerCase();
  // Using text-teal-400 instead of text-indigo-400 to comply with Purple Ban
  if (["png", "jpg", "jpeg", "gif", "bmp"].includes(ext || "")) return <Image className="h-4 w-4 text-teal-400" />;
  if (ext === "pdf") return <FileType className="h-4 w-4 text-rose-400" />;
  if (["docx", "doc"].includes(ext || "")) return <FileText className="h-4 w-4 text-sky-400" />;
  return <FileText className="h-4 w-4 text-gray-400" />;
}

export default function NewCasePage() {
  const [patientId, setPatientId] = useState("");
  const [rawText, setRawText] = useState("");
  const [originalText, setOriginalText] = useState(""); // Stores original extracted text before edits
  const [loading, setLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [error, setError] = useState("");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [piiConfirmed, setPiiConfirmed] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    const pendingText = localStorage.getItem("pending_clinical_text");
    if (pendingText) {
      setRawText(pendingText);
      localStorage.removeItem("pending_clinical_text");
    }
  }, []);

  const handleGenerateId = () => {
    setPatientId(crypto.randomUUID());
  };

  const processFile = useCallback(async (file: File) => {
    if (!ACCEPTED_TYPES.includes(file.type) && !ACCEPTED_EXTENSIONS.some(ext => file.name.endsWith(ext))) {
      setError(`Unsupported file type. Please upload: PDF, DOCX, TXT, or an image.`);
      return;
    }

    setUploadedFile(file);
    setUploadLoading(true);
    setError("");

    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API_URL}/api/v1/workflow/upload-document`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to extract text from document");
      }

      const data = await res.json();
      setRawText(data.text);
      setOriginalText(data.text); // Save initial extraction content
    } catch (err: any) {
      setError(err.message || "Failed to process file");
      setUploadedFile(null);
      setRawText("");
      setOriginalText("");
    } finally {
      setUploadLoading(false);
    }
  }, [router]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
    e.target.value = "";
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => setDragOver(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  };

  const handleRemoveFile = () => {
    setUploadedFile(null);
    setRawText("");
    setOriginalText("");
    setPiiConfirmed(false);
  };

  const handleResetText = () => {
    setRawText(originalText);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // Validation
    if (uploadedFile && !piiConfirmed) {
      setError("Please confirm de-identification compliance before running the pipeline.");
      return;
    }

    setLoading(true);

    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${API_URL}/api/v1/workflow/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          patient_id: patientId,
          raw_text: rawText,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to start prior auth workflow");
      }

      const data = await res.json();
      router.push(`/workflow/${data.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to submit prior authorization request");
    } finally {
      setLoading(false);
    }
  };

  // Helper values for editor feedback
  const wordCount = useMemo(() => {
    if (!rawText.trim()) return 0;
    return rawText.trim().split(/\s+/).length;
  }, [rawText]);

  const charCount = useMemo(() => rawText.length, [rawText]);
  
  const isEdited = useMemo(() => {
    return originalText !== "" && rawText !== originalText;
  }, [rawText, originalText]);

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-base)" }}>
      <Navbar />

      <main className="max-w-7xl mx-auto px-8 py-10">
        <Link
          href="/dashboard"
          className="inline-flex items-center space-x-2 text-sm text-gray-400 hover:text-white mb-6 transition-all"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Dashboard</span>
        </Link>

        {/* Header Section */}
        <div className="mb-8 animate-fade-in">
          <p className="section-label" style={{ marginBottom: 6 }}>Case Creation</p>
          <h1 className="text-3xl font-extrabold tracking-wide">Submit New Patient Case</h1>
          <p className="text-sm text-gray-400 mt-1">
            Initiate the Prior Authorization AI agent pipeline. Clinical documents will be parsed and de-identified before processing.
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 text-sm bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-lg flex items-start space-x-2.5 animate-scale-in">
            <AlertCircle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Main Layout Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            
            {/* Left Column: Case Metadata & Upload Controller (occupies 4/12 width on desktop) */}
            <div className="lg:col-span-4 space-y-6">
              
              {/* Patient Info Card */}
              <div className="panel p-6 space-y-4 animate-fade-in delay-100">
                <h3 className="text-sm font-bold text-gray-300 uppercase tracking-wider">Patient Details</h3>
                
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1.5 flex justify-between items-center">
                    <span>Patient ID (UUID / Name)</span>
                    <button
                      type="button"
                      onClick={handleGenerateId}
                      className="text-xs text-teal-400 hover:text-teal-300 flex items-center space-x-1 transition-all"
                    >
                      <Sparkles className="h-3 w-3" />
                      <span>Anonymize</span>
                    </button>
                  </label>
                  <input
                    type="text"
                    required
                    value={patientId}
                    onChange={(e) => setPatientId(e.target.value)}
                    placeholder="Enter ID or full name"
                    className="field p-3 font-mono text-sm"
                  />
                </div>

                <div className="pt-2">
                  <span className="trust-chip">
                    <CheckCircle className="h-3.5 w-3.5" />
                    <span>HIPAA Compliant Scrubbing</span>
                  </span>
                </div>
              </div>

              {/* Document Source Card */}
              <div className="panel p-6 space-y-4 animate-fade-in delay-150">
                <h3 className="text-sm font-bold text-gray-300 uppercase tracking-wider">Source Document</h3>
                
                {!uploadedFile && !uploadLoading ? (
                  <div
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
                      dragOver 
                        ? "border-teal-500 bg-teal-500/5" 
                        : "border-gray-800 hover:border-gray-750 bg-[#0d131f]/40"
                    }`}
                  >
                    <Upload className="h-7 w-7 text-gray-500 mx-auto mb-2.5 transition-transform group-hover:-translate-y-1" />
                    <p className="text-xs font-semibold text-gray-300">Click or drag document here</p>
                    <p className="text-[10px] text-gray-500 mt-1">PDF, DOCX, TXT, PNG, JPG</p>
                  </div>
                ) : uploadLoading ? (
                  <div className="border border-gray-800 rounded-xl p-8 text-center bg-[#0d131f]/20">
                    <Loader2 className="h-7 w-7 text-teal-400 animate-spin mx-auto mb-2" />
                    <p className="text-xs font-semibold text-teal-400">Extracting clinical text...</p>
                    <p className="text-[10px] text-gray-500 mt-1">Running NLP extraction parser</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Active Upload File Card */}
                    <div className="flex items-center space-x-3 p-3 bg-teal-500/5 border border-teal-500/20 rounded-xl">
                      {getFileIcon(uploadedFile!.name)}
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-teal-300 truncate">{uploadedFile!.name}</p>
                        <p className="text-[10px] text-gray-500">{(uploadedFile!.size / 1024).toFixed(1)} KB</p>
                      </div>
                      <button
                        type="button"
                        onClick={handleRemoveFile}
                        className="text-gray-500 hover:text-rose-400 transition-all p-1"
                        title="Remove Document"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>

                    {/* De-identification compliance checklist */}
                    <div className="bg-[#0d131f]/40 border border-gray-800 rounded-xl p-4 space-y-3">
                      <p className="text-[11px] text-gray-400 leading-normal">
                        Verify that the extracted note is ready. Sensitive patient identifiers will be automatically de-identified before processing.
                      </p>
                      <label className="flex items-start space-x-2.5 cursor-pointer group select-none">
                        <input
                          type="checkbox"
                          checked={piiConfirmed}
                          onChange={(e) => setPiiConfirmed(e.target.checked)}
                          className="mt-0.5 rounded border-gray-800 bg-[#060d1f] text-teal-500 focus:ring-0"
                        />
                        <span className="text-[11px] text-gray-300 group-hover:text-white transition-all font-medium">
                          I confirm clinical data is clean and ready.
                        </span>
                      </label>
                    </div>
                  </div>
                )}

                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPTED_EXTENSIONS.join(",")}
                  onChange={handleFileChange}
                  className="hidden"
                  id="file-upload-input"
                />
              </div>

              {/* Submit Action Button */}
              <div className="animate-fade-in delay-200">
                <button
                  type="submit"
                  disabled={loading || uploadLoading || !rawText.trim() || (uploadedFile !== null && !piiConfirmed)}
                  className="btn btn-primary w-full py-3.5 h-auto text-base font-bold flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <>
                      <Play className="h-4 w-4 fill-white" />
                      <span>Run AI Pipeline</span>
                    </>
                  )}
                </button>
              </div>

            </div>

            {/* Right Column: Dynamic Workbench Workspace (occupies 8/12 width on desktop) */}
            <div className="lg:col-span-8">
              
              {/* Workspace Container Panel */}
              <div className="panel p-6 min-h-[460px] flex flex-col justify-between animate-fade-in delay-150">
                
                <div className="space-y-4 flex-1 flex flex-col">
                  {/* Workspace Header */}
                  <div className="flex justify-between items-center pb-3 border-b border-[var(--border-subtle)]">
                    <div className="flex items-center space-x-2.5">
                      <FileText className="h-5 w-5 text-teal-400" />
                      <div>
                        <h2 className="text-base font-bold text-gray-200">
                          {uploadedFile ? "Extracted Clinical Document Preview" : "Clinical Note Workspace"}
                        </h2>
                        <p className="text-[10px] text-gray-500 mt-0.5">
                          {uploadedFile 
                            ? "Review and edit parsed document contents below before submitting" 
                            : "Enter clinical notes, codes, and details manually"
                          }
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      {isEdited && (
                        <span className="badge badge-warning text-[10px] py-0.5 px-2">
                          Modified
                        </span>
                      )}
                      {uploadedFile && (
                        <span className="badge badge-success text-[10px] py-0.5 px-2">
                          Document Extracted
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Textarea Editor Area */}
                  <div className="flex-1 flex flex-col min-h-[280px] mt-2 relative">
                    <textarea
                      required
                      value={rawText}
                      onChange={(e) => setRawText(e.target.value)}
                      placeholder={
                        uploadedFile 
                          ? "Extracted text will appear here..."
                          : "Type or paste clinical doctor notes here. Include details such as symptoms, diagnoses, ICD/CPT codes, insurance carrier name, and requested procedures (e.g., John Doe has lumbar spine pain, plans physical therapy code 97110 under Aetna)."
                      }
                      className="field flex-1 p-4 font-mono text-sm leading-relaxed resize-none h-full min-h-[300px]"
                    />
                  </div>
                </div>

                {/* Workspace Footer Bar */}
                <div className="mt-4 pt-3 border-t border-[var(--border-subtle)] flex flex-wrap justify-between items-center gap-3">
                  <div className="flex items-center space-x-4 text-xs text-gray-500 font-mono">
                    <span>Words: <strong className="text-gray-400">{wordCount}</strong></span>
                    <span>Characters: <strong className="text-gray-400">{charCount}</strong></span>
                  </div>

                  <div className="flex items-center space-x-2">
                    {isEdited && (
                      <button
                        type="button"
                        onClick={handleResetText}
                        className="btn btn-secondary text-xs h-8 px-3 py-1 flex items-center space-x-1"
                        title="Revert all changes back to original extracted text"
                      >
                        <RefreshCw className="h-3 w-3" />
                        <span>Revert to Original</span>
                      </button>
                    )}
                    {uploadedFile && (
                      <button
                        type="button"
                        onClick={handleRemoveFile}
                        className="btn btn-ghost text-xs text-rose-400 hover:bg-rose-500/10 h-8 px-3 py-1 flex items-center space-x-1"
                      >
                        <Trash2 className="h-3 w-3" />
                        <span>Clear Document</span>
                      </button>
                    )}
                  </div>
                </div>

              </div>
              
              {/* Helpful Tips Alert Banner */}
              <div className="mt-4 p-4 bg-[#0d131f]/30 border border-gray-850 rounded-xl flex items-start space-x-2.5 text-xs text-gray-400 animate-fade-in delay-250">
                <Sparkles className="h-4 w-4 text-teal-400 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="font-semibold text-gray-300">Tips for Higher Extraction Quality:</p>
                  <ul className="list-disc list-inside space-y-1 text-gray-400 pl-1">
                    <li>Ensure prior authorization requested code is clear (e.g. CPT 97110, ICD-10 M54.5).</li>
                    <li>Specify the exact insurer name (e.g. Aetna, UnitedHealthcare, Cigna) to trigger correct routing.</li>
                    <li>Review auto-extracted text for any character noise (e.g. OCR artifact chars) and correct them manually above.</li>
                  </ul>
                </div>
              </div>

            </div>

          </div>
        </form>
      </main>
    </div>
  );
}
