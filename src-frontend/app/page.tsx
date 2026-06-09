"use client";

import Link from "next/link";
import { ArrowRight, ShieldCheck, Activity, Users } from "lucide-react";

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen justify-between">
      {/* Header */}
      <header className="flex justify-between items-center p-6 border-b border-[var(--border)] bg-[rgba(11,15,25,0.5)] backdrop-blur-md">
        <div className="flex items-center space-x-2">
          <Activity className="h-6 w-6 text-sky-400" />
          <span className="font-bold text-xl tracking-wide bg-gradient-to-r from-sky-400 to-emerald-400 bg-clip-text text-transparent">
            PulseAI
          </span>
        </div>
        <Link
          href="/login"
          className="px-5 py-2 rounded-full bg-sky-500 hover:bg-sky-600 text-white font-medium transition-all"
        >
          Sign In
        </Link>
      </header>

      {/* Main Hero */}
      <main className="flex-1 flex flex-col justify-center items-center px-6 text-center max-w-4xl mx-auto my-12">
        <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight mb-6 leading-tight">
          Prior Authorization,{" "}
          <span className="bg-gradient-to-r from-sky-400 via-teal-400 to-emerald-400 bg-clip-text text-transparent">
            Automated in Seconds
          </span>
        </h1>
        <p className="text-lg md:text-xl text-gray-400 mb-8 max-w-2xl">
          HIPAA & TT46 compliant AI pipeline using LangGraph. Streamlines medical insurance requests, extracts ICD-10 codes, and fills claims instantly.
        </p>

        <div className="flex space-x-4">
          <Link
            href="/login"
            className="flex items-center space-x-2 px-8 py-4 bg-gradient-to-r from-sky-500 to-teal-500 hover:from-sky-600 hover:to-teal-600 text-white font-semibold rounded-xl transition-all shadow-lg shadow-sky-500/10 hover:shadow-sky-500/20"
          >
            <span>Access Portal</span>
            <ArrowRight className="h-5 w-5" />
          </Link>
        </div>

        {/* Feature grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 text-left">
          <div className="glass-card p-6 rounded-2xl">
            <ShieldCheck className="h-8 w-8 text-emerald-400 mb-4" />
            <h3 className="font-semibold text-lg mb-2">De-identification</h3>
            <p className="text-sm text-gray-400">
              Deterministic regex-based PHI scrubbing ensures HIPAA privacy prior to any external LLM request.
            </p>
          </div>
          <div className="glass-card p-6 rounded-2xl">
            <Activity className="h-8 w-8 text-sky-400 mb-4" />
            <h3 className="font-semibold text-lg mb-2">LangGraph Pipeline</h3>
            <p className="text-sm text-gray-400">
              State-driven routing between nodes to extract clinical codes, resolve payers, and perform quality checks.
            </p>
          </div>
          <div className="glass-card p-6 rounded-2xl">
            <Users className="h-8 w-8 text-indigo-400 mb-4" />
            <h3 className="font-semibold text-lg mb-2">Doctor Approval</h3>
            <p className="text-sm text-gray-400">
              Quality gate (&lt;95 score) prompts manual clinician review to guarantee absolute billing accuracy.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="p-6 border-t border-[var(--border)] text-center text-sm text-gray-500 bg-[rgba(11,15,25,0.2)]">
        &copy; {new Date().getFullYear()} PulseAI Inc. All rights reserved.
      </footer>
    </div>
  );
}
