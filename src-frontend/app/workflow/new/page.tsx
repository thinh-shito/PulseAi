"use client";

import { useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Play, Loader2, Sparkles, Paperclip, FileText, Image, X, Upload, FileType } from "lucide-react";
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
  if (["png", "jpg", "jpeg", "gif", "bmp"].includes(ext || "")) return <Image className="h-4 w-4 text-indigo-400" />;
  if (ext === "pdf") return <FileType className="h-4 w-4 text-rose-400" />;
  if (["docx", "doc"].includes(ext || "")) return <FileText className="h-4 w-4 text-sky-400" />;
  return <FileText className="h-4 w-4 text-gray-400" />;
}

export default function NewCasePage() {
  const [patientId, setPatientId] = useState("");
  const [rawText, setRawText] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [error, setError] = useState("");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

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
    } catch (err: any) {
      setError(err.message || "Failed to process file");
      setUploadedFile(null);
    } finally {
      setUploadLoading(false);
    }
  }, [router]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
    // Reset input so same file can be re-selected
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
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
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

  return (
    <div className="min-h-screen bg-[#080b11]">
      <Navbar />

      <main className="max-w-3xl mx-auto px-8 py-10">
        <Link
          href="/dashboard"
          className="inline-flex items-center space-x-2 text-sm text-gray-400 hover:text-white mb-6 transition-all"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Dashboard</span>
        </Link>

        <div className="mb-8">
          <h1 className="text-3xl font-extrabold tracking-wide">Submit New Patient Case</h1>
          <p className="text-sm text-gray-400 mt-1">
            Initiate the Prior Authorization AI agent pipeline. Sensitive patient identifiers will be automatically de-identified before processing.
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 text-sm bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-lg">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="glass-card p-6 rounded-2xl space-y-5">
            {/* Patient ID */}
            <div>
              <label className="block text-sm font-semibold text-gray-300 mb-1.5 flex justify-between items-center">
                <span>Patient Identification (UUID or Name)</span>
                <button
                  type="button"
                  onClick={handleGenerateId}
                  className="text-xs text-sky-400 hover:text-sky-300 flex items-center space-x-1"
                >
                  <Sparkles className="h-3 w-3" />
                  <span>Generate Anonymous ID</span>
                </button>
              </label>
              <input
                type="text"
                required
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
                placeholder="Enter patient ID or full name (will be anonymized)"
                className="block w-full px-4 py-3 bg-[#0d131f] border border-gray-800 rounded-xl focus:border-sky-500 focus:ring-1 focus:ring-sky-500 text-white placeholder-gray-600 outline-none transition-all text-sm font-mono"
              />
            </div>

            {/* Clinical Notes + File Upload */}
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="block text-sm font-semibold text-gray-300">
                  Clinical Notes / Doctor Notes / Diagnosis Details
                </label>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadLoading}
                  className="flex items-center space-x-1.5 text-xs text-emerald-400 hover:text-emerald-300 transition-all disabled:opacity-50"
                >
                  {uploadLoading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Paperclip className="h-3.5 w-3.5" />
                  )}
                  <span>{uploadLoading ? "Extracting..." : "Upload File"}</span>
                </button>
              </div>

              {/* Hidden file input */}
              <input
                ref={fileInputRef}
                type="file"
                accept={ACCEPTED_EXTENSIONS.join(",")}
                onChange={handleFileChange}
                className="hidden"
                id="file-upload-input"
              />

              {/* Uploaded file badge */}
              {uploadedFile && (
                <div className="flex items-center space-x-2 mb-2 px-3 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                  {getFileIcon(uploadedFile.name)}
                  <span className="text-xs text-emerald-300 flex-1 truncate">{uploadedFile.name}</span>
                  <span className="text-xs text-gray-500">{(uploadedFile.size / 1024).toFixed(1)} KB</span>
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    className="text-gray-500 hover:text-rose-400 transition-all ml-1"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              )}

              {/* Drag-and-drop zone + textarea */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`relative transition-all rounded-xl ${
                  dragOver
                    ? "ring-2 ring-sky-500 ring-offset-2 ring-offset-[#080b11]"
                    : ""
                }`}
              >
                <textarea
                  required
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  rows={10}
                  placeholder={
                    dragOver
                      ? "Drop your file here to extract text..."
                      : "Paste the patient's medical details, symptoms, diagnoses, insurer name, and planned procedures.\nE.g. Patient John Doe has lumbar pain, plans procedure 97110 under Aetna...\n\nOr drag & drop a PDF, DOCX, TXT, or image file above."
                  }
                  className="block w-full px-4 py-3 bg-[#0d131f] border border-gray-800 rounded-xl focus:border-sky-500 focus:ring-1 focus:ring-sky-500 text-white placeholder-gray-600 outline-none transition-all text-sm font-sans resize-none"
                />

                {/* Drag overlay */}
                {dragOver && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-sky-500/10 border-2 border-dashed border-sky-500 rounded-xl pointer-events-none">
                    <Upload className="h-8 w-8 text-sky-400 mb-2" />
                    <p className="text-sky-400 font-semibold text-sm">Drop file to extract text</p>
                    <p className="text-gray-500 text-xs mt-1">PDF, DOCX, TXT, PNG, JPG</p>
                  </div>
                )}
              </div>

              <p className="mt-2 text-xs text-gray-600">
                Supports: PDF, DOCX, TXT, PNG, JPG — text will be extracted and de-identified automatically.
              </p>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={loading || uploadLoading}
              className="flex items-center space-x-2 px-8 py-3.5 bg-gradient-to-r from-sky-500 to-teal-500 hover:from-sky-600 hover:to-teal-600 text-white font-semibold rounded-xl transition-all shadow-lg shadow-sky-500/10 hover:shadow-sky-500/20 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  <span>Run AI Pipeline</span>
                </>
              )}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
